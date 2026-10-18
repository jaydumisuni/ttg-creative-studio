#!/usr/bin/env python3
"""Reproducible model-agnostic video contract qualification.

Requires Pillow. For real media probe/decode tests, system ffmpeg and ffprobe
must both be present. No model, FreeVideo download, or remote API required.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from ttg_action_engine import ActionEngine
from ttg_creative_studio.engine.video_jobs import tool_catalog
from ttg_project_schema import TTGProject

CHECKS: list[str] = []


def check(condition, name):
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def job_cli(temp, content, result_name):
    job=temp/(result_name+".job.json")
    result=temp/(result_name+".result.json")
    job.write_text(json.dumps(content),encoding="utf-8")
    r=subprocess.run([sys.executable,"-B",str(ROOT/"src/ttg_creative_studio/cli.py"),
                      "--job",str(job),"--result",str(result)],
                     cwd=ROOT,capture_output=True,text=True,timeout=80)
    return r,json.loads(result.read_text()) if result.exists() else {}


def main():
    with tempfile.TemporaryDirectory(prefix="studio-video-contract-") as area:
        directory=Path(area)
        cmd=[sys.executable,"-B",str(ROOT/"src/ttg_creative_studio/cli.py"),"--catalog"]
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=15,cwd=ROOT)
        check(r.returncode==0 and json.loads(r.stdout)["schema"]=="ttg.creative.video-agent.v1",
              "Any AI can discover versioned shared tool contract")
        catalog=tool_catalog()
        check(catalog["operations"]["video_generate"]["state"]=="online_opt_in" and
              catalog["operations"]["video_local_install"]["state"]=="future_GT502_Spark",
              "Cloud generation requires approval and local weights remain disabled")
        caps, info=job_cli(directory,{"task":"video_capabilities","jobId":"hello"},"caps")
        check(caps.returncode==0 and info["ok"] and "ffmpeg" in info["meta"],
              "Runtime video capabilities are observed")
        brief={
            "task":"video_plan","jobId":"plan1",
            "output":str(directory/"plan.json"),
            "options":{"fps":24,"scenes":[
                {"description":"A phone on a studio table","seconds":2.5},
                {"description":"Close-up detail shot","seconds":1.5},
            ]}
        }
        r,report=job_cli(directory,brief,"plan1")
        saved=json.loads((directory/"plan.json").read_text())
        check(r.returncode==0 and report["ok"] and saved["duration_seconds"]==4,
              "Native storyboard is timestamped and persisted")
        check(saved["status"]=="review_required" and
              all(s["status"]=="planned_not_generated" for s in saved["scenes"]),
              "Storyboard never masquerades as generated video")
        again, _=job_cli(directory,brief,"plan-repeat")
        check(again.returncode!=0,
              "Model-originated workflow cannot overwrite an existing output")
        invalid={
            "task":"video_plan","output":str(directory/"invalid.json"),
            "options":{"scenes":[{"description":"Impossible scene","seconds":float("nan")}]}
        }
        fail, _=job_cli(directory,invalid,"invalid")
        check(fail.returncode!=0 and not (directory/"invalid.json").exists(),
              "Invalid scene duration fails closed")
        bad,reply=job_cli(directory,{"task":"video_generate","output":str(directory/"fake.mp4")},
                          "unsupported")
        check(bad.returncode!=0 and "explicit approval" in reply.get("error","")
          and not (directory/"fake.mp4").exists(),
              "Cloud generation cannot charge or fabricate results without approval")

        from PIL import Image
        pic=directory/"image.png"
        Image.new("RGB",(28,18),(8,30,170)).save(pic)
        prior={
            "task":"image_info","input":str(pic),
            "output":str(directory/"image.json")
        }
        compatible,response=job_cli(directory,prior,"image_info")
        check(compatible.returncode==0 and response["ok"] and
              response["meta"]["width"]==28,
              "Preexisting Hunter image jobs remain compatible")

        ffmpeg=shutil.which("ffmpeg")
        ffprobe=shutil.which("ffprobe")
        if ffmpeg:
            movie=directory/"sample.mp4"
            proc=subprocess.run(
                [ffmpeg,"-hide_banner","-loglevel","error","-y",
                 "-f","lavfi","-i","color=c=blue:s=160x90:r=6:d=1",
                 "-c:v","libx264","-pix_fmt","yuv420p",str(movie)],
                capture_output=True,timeout=35,
            )
            check(proc.returncode==0 and movie.stat().st_size>200,
                  "Real FFmpeg fixture generated")
            report_path=directory/"video-info.json"
            r,report=job_cli(directory,{
                "task":"video_info","input":str(movie),"output":str(report_path)
            },"video_info")
            if ffprobe:
                check(r.returncode==0 and report["meta"]["width"]==160
                      and report["meta"]["source_sha256"],
                      "Real ffprobe metadata and SHA256")
                r,understand=job_cli(directory,{
                    "task":"video_understand", "input":str(movie),
                    "output":str(directory/"understanding.json"),
                },"understand")
                measure=understand.get("meta",{})
                check(r.returncode==0 and len(measure.get("frame_samples",[]))==3,
                      "Real media decoded and three visual timestamps inspected")
                check(measure.get("interpretation")=="pixel_measurements_only"
                      and all("objects" not in x for x in measure["frame_samples"]),
                      "No ungrounded semantic objects invented without VLM")
            else:
                check(r.returncode!=0 and "ffprobe" in report.get("error",""),
                      "Video metadata fails closed without ffprobe: " + str(report))

            project=ActionEngine().new_project("Real timeline test","motion")
            project.canvas.width=160
            project.canvas.height=90
            project.canvas.fps=4
            project.canvas.duration=.5
            ActionEngine().add_shape(project,"rectangle",0,0)
            project_file=directory/"native.ttgstudio.json"
            project.save(project_file)
            dest=directory/"native-render.mp4"
            r,render=job_cli(directory,{
                "task":"video_render","input":str(project_file),
                "output":str(dest)
            },"render")
            check(r.returncode==0 and render["ok"] and dest.is_file()
                  and dest.stat().st_size>200,
                  "AI can invoke same native Studio timeline real MP4 renderer: "
                  + json.dumps({"response":render,"stdout":r.stdout[-1500:],
                                "stderr":r.stderr[-2000:]},default=str))
        else:
            missing,report=job_cli(directory,{
                "task":"video_info","input":str(pic),
                "output":str(directory/"nomedia.json")
            },"no_ffmpeg")
            check(missing.returncode!=0,
                  "Media operation fails without true dependencies")

    print(json.dumps({"result":"PASS","checks":len(CHECKS),"names":CHECKS},indent=2))


if __name__=="__main__":
    main()
