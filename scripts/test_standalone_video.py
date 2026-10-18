#!/usr/bin/env python3
"""Stand-alone Creative Studio real-video import, trim, playback, and export proof."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ttg_video_media import probe_video, video_frame, clip_source_time
from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_motion_exporter import MotionExporter
from ttg_project_schema import TTGProject
from ttg_ffmpeg_manager import FFmpegManager
from PyQt6.QtWidgets import QApplication
from ttg_creative_workspace import CreativeWorkspace
from ttg_video_lab_dialog import VideoLabDialog, VideoTrimDialog, VideoExportThread

checks = []


def require(condition, name):
    assert condition, name
    checks.append(name)


def pixel_is(frame, color):
    r, g, b = frame.getpixel((30, 30))[:3]
    return (r > 180 and b < 110) if color == "red" else (b > 180 and r < 110)


def main():
    ffmpeg = FFmpegManager().require()
    ffprobe = shutil.which("ffprobe")
    with tempfile.TemporaryDirectory(prefix="studio-real-video-") as directory:
        path = Path(directory)
        first = path/"a.mp4"
        second = path/"b.mp4"
        joined = path/"clip.mp4"
        for name, color in [(first, "red"), (second, "blue")]:
            command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                       "-f", "lavfi", "-i", f"color=c={color}:s=160x90:r=4:d=1",
                       "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=8000:duration=1",
                       "-c:v", "mpeg4", "-q:v", "3", "-c:a", "aac",
                       "-shortest", str(name)]
            proc = subprocess.run(command, capture_output=True, timeout=35)
            require(proc.returncode==0 and name.stat().st_size > 700,
                    f"Real {color} audio/video encoded")
        manifest=path/"concat.txt"
        manifest.write_text(
            f"file '{first.as_posix()}'\nfile '{second.as_posix()}'\n")
        result = subprocess.run(
            [ffmpeg,"-hide_banner","-loglevel","error","-y",
             "-f","concat","-safe","0","-i",str(manifest),"-c","copy",str(joined)],
            capture_output=True, timeout=32)
        require(result.returncode==0, "Two-color video assembled")
        metadata=probe_video(joined)
        require(metadata["audio_streams"]>=1 and metadata["duration"]>1.5,
                "Actual video and audio streams probed")
        require(pixel_is(video_frame(joined,.25),"red"),
                "Red first video frame genuinely decoded")
        require(pixel_is(video_frame(joined,1.25),"blue"),
                "Blue later video frame genuinely decoded")
        require(clip_source_time({"start":1,"source_in":0.25,"source_out":1.5,"speed":1},0) is None,
                "Clip not visible before timeline start")
        require(clip_source_time({"start":1,"source_in":0.25,"source_out":1.5,"speed":1},1.5)==.75,
                "Timeline maps to source trim offset")

        app=QApplication.instance() or QApplication([])
        dialog=VideoLabDialog(str(joined))
        dialog.inspect()
        until=time.monotonic()+32
        while dialog._worker and dialog._worker.isRunning() and time.monotonic()<until:
            app.processEvents()
            time.sleep(.03)
        app.processEvents()
        require(dialog.metadata is not None and len(dialog.previews)==3,
                "Video Lab asynchronously inspects real media and previews")
        dialog.close()
        trim_editor=VideoTrimDialog({"start":0.2,"source_in":0.25,
                                     "source_out":1.75,"speed":1},metadata["duration"])
        trim_editor.trim_in.setValue(0.5)
        trim_editor.confirm()
        require(trim_editor.result()==trim_editor.DialogCode.Accepted,
                "Standalone GUI supports editable trim settings after import")
        trim_editor.close()

        document=path/"document.ttgstudio.json"
        project=TTGProject(name="Native Real Video",project_type="mixed")
        project.canvas.width=160
        project.canvas.height=90
        project.canvas.background="#000000"
        project.canvas.fps=4
        project.canvas.duration=2
        project.save(document)
        workspace=CreativeWorkspace(path)
        workspace.project=project
        workspace.project_path=document
        workspace._set_asset_root(path)
        workspace.import_video_clip(joined,metadata,timeline_start=0,
                                    trim_in=0,trim_out=metadata["duration"],
                                    include_audio=True,copy_into_project=False)
        layer=workspace.selected_layer()
        require(layer is not None and layer.type=="video", "GUI imports editable video layer")
        linked=Path(layer.properties["path"])
        require((linked if linked.is_absolute() else path/linked).resolve()==joined.resolve(),
                "Linked source avoids copy/storage waste")
        require(len(workspace.project.audio_markers)==1, "Audio stream import wired into timeline")
        exported_project=workspace.project
        renderer=MotionExporter(RenderContext(path))
        image1=renderer.render_frame(exported_project,.25)
        image2=renderer.render_frame(exported_project,1.25)
        require(pixel_is(image1,"red") and pixel_is(image2,"blue"),
                "Native layer actually composites changing source video pixels")
        workspace.preview_still()
        workspace.seek_timeline(.25)
        earlier=workspace.playback.label.pixmap().cacheKey()
        workspace.seek_timeline(1.25)
        later=workspace.playback.label.pixmap().cacheKey()
        require(earlier != later and abs(workspace.playback.time-1.25)<.01,
                "Timeline scrubbing changes playback: " +
                str({"first":earlier,"second":later,"time":workspace.playback.time,
                "approved":workspace.still_preview_approved,
                "label":workspace.playback.label.text()}))
        workspace.save_project()
        reloaded=TTGProject.load(document)
        require(reloaded.layers[0].type=="video" and reloaded.layers[0].properties["source_in"]==0,
                "Save/reopen retains editable video clip and trim")
        exported_by_gui=path/"async-export.mp4"
        async_worker=VideoExportThread(
            reloaded, path, exported_by_gui, path/"async-scratch"
        )
        completed=[]
        export_errors=[]
        async_worker.completed.connect(completed.append)
        async_worker.failed.connect(export_errors.append)
        async_worker.start()
        until=time.monotonic()+75
        while async_worker.isRunning() and time.monotonic()<until:
            app.processEvents()
            time.sleep(.03)
        async_worker.wait(5000)
        app.processEvents()
        require(bool(completed) and exported_by_gui.is_file(),
                "Background Qt export creates a real MP4 without blocking GUI: " +
                str({"completed":completed,"errors":export_errors,
                     "file_exists":exported_by_gui.exists()}))
        workspace.delete_layer()
        require(len(workspace.project.audio_markers)==0,
                "Removing a video layer also removes only its linked source audio")
        workspace.undo()
        require(len(workspace.project.audio_markers)==1,
                "Undo restores video layer and linked audio marker")
        workspace.close()
        app.processEvents()

        output=path/"export.mp4"
        rendered=renderer.export_mp4(reloaded,output,path/"scratch")
        require(rendered.is_file() and rendered.stat().st_size>1100,
                "Actual edited Studio movie and source audio encoded")
        require(not list((path/"scratch").glob("ttg-render-*")),
                "Export removes scratch frames")
        require(probe_video(output)["audio_streams"]>=1,
                "Final MP4 contains source audio")
        if ffprobe:
            info = probe_video(output)
            require(info["width"]==160 and info["height"]==90,
                    "Final video output preserves intended canvas geometry")

        # Opt-in copied assets are deduplicated by content hash.
        workspace=CreativeWorkspace(path)
        workspace.project=TTGProject(name="Portable Clip",project_type="mixed")
        workspace.project_path=path/"portable.ttgstudio.json"
        workspace.project.save(workspace.project_path)
        workspace._set_asset_root(path)
        workspace.import_video_clip(joined,metadata,copy_into_project=True,include_audio=False)
        source_ref=workspace.selected_layer().properties["path"]
        require(not Path(source_ref).is_absolute() and (path/source_ref).exists(),
                "Portable import copies source into project asset folder")
        workspace.import_video_clip(joined,metadata,copy_into_project=True,include_audio=False)
        require(len(list((path/"assets/video").glob("*.mp4")))==1,
                "Repeated portable import deduplicates large source")
        workspace.close()
        app.processEvents()

    print(json.dumps({"result":"PASS","checks":len(checks),"names":checks},indent=2))


if __name__=="__main__":
    main()
