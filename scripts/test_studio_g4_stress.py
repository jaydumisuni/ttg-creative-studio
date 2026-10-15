#!/usr/bin/env python3
"""Repeatable G4 multi-layer rendering, cache and interrupted-recovery test.

CI runner test, not a physical ATHENA memory/DPI/GPU qualification.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ttg_action_engine import ActionEngine
from ttg_canvas_engine import CanvasRenderer, RenderContext, _cached_small_image
from ttg_recovery import RecoveryStore

checks=[]


def check(name: str, condition: bool):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def run():
    with tempfile.TemporaryDirectory(prefix="studio-g4-stress-") as tmp:
        root=Path(tmp)
        action=ActionEngine()
        project=action.new_project("Real multilayer qualification", "image")
        project.canvas.width=1400
        project.canvas.height=900
        _cached_small_image.cache_clear()
        for i in range(12):
            name=f"image_{i:02d}.png"
            color=((i*21)%256, (i*57)%256, (i*97)%256, 210)
            Image.new("RGBA",(440,360),color).save(root/name)
            layer=action.add_image(project,name,(i%4)*270,(i//4)*170)
            if i%3==0:
                layer.effects.append({"type":"contrast","amount":1.2})
        renderer=CanvasRenderer(RenderContext(root))
        start=time.perf_counter()
        image1=renderer.render(project)
        sha1=hashlib.sha256(image1.tobytes()).hexdigest()
        image2=renderer.render(project)
        sha2=hashlib.sha256(image2.tobytes()).hexdigest()
        elapsed=time.perf_counter()-start
        check("12-layer 1400x900 render completes",image2.size==(1400,900))
        check("deterministic multilayer render hashes",sha1==sha2)
        check("bounded decoded small-image LRU",_cached_small_image.cache_info().currsize<=16)
        check("repeat render exercises cache",_cached_small_image.cache_info().hits>0)
        check("bounded CI runner completion",elapsed<90)

        # A tiny compressed PNG can still decode to millions of pixels.
        # It must not occupy 16 cache slots worth of enormous RGBA buffers.
        huge = root/"highly-compressible.png"
        Image.new("RGBA", (1800, 900), (1, 2, 3, 255)).save(huge)
        cached = _cached_small_image(str(huge.resolve()), huge.stat().st_mtime_ns,
                                    huge.stat().st_size)
        check("large decoded image bypasses memory-bounded cache",cached is None)
        source=root/"image_11.png"
        time.sleep(.03)
        Image.new("RGBA",(440,360),(250,30,40,255)).save(source)
        image3=renderer.render(project)
        check("real image change invalidates render cache",
              hashlib.sha256(image3.tobytes()).hexdigest()!=sha1)

        saved=root/"saved.ttgstudio.json"
        project.save(saved)
        saved_hash=hashlib.sha256(saved.read_bytes()).hexdigest()
        store=RecoveryStore(root/"recovery",limit=3)
        project.name="Modified in memory (not yet saved)"
        prior=store.snapshot(project,saved)
        reopened, original=store.load(prior)
        check("recover edited unsaved state without overwriting project",
              reopened.name==project.name and original==saved
              and hashlib.sha256(saved.read_bytes()).hexdigest()==saved_hash)

        project.name="Change interrupted by simulated full disk"
        with patch("ttg_recovery.os.replace",side_effect=OSError("No space left on device")):
            try:
                store.snapshot(project,saved)
            except OSError:
                checks.append("simulated failed disk replace surfaces error")
            else:
                raise AssertionError("Full disk error was hidden")
        kept,_=store.load(prior)
        check("preexisting recovery survives interrupted disk commit",
              kept.name=="Modified in memory (not yet saved)"
              and not list(store.root.glob("*.tmp")))
        prior.write_text("{definitely not valid JSON",encoding="utf-8")
        try:
            store.load(prior)
        except (ValueError,json.JSONDecodeError):
            checks.append("corrupt recovery rejected, not promoted")
        else:
            raise AssertionError("Corrupt recovery returned a project")
        check("corrupt recovery cannot alter last saved project",
              hashlib.sha256(saved.read_bytes()).hexdigest()==saved_hash)
        for i in range(5):
            store.snapshot(project,None,str(i))
            time.sleep(.01)
        check("autosave retention prunes old snapshots",len(store.pending())==3)

    print(json.dumps({"result":"PASS","checks_count":len(checks),
                      "render_seconds":round(elapsed,3),"checks":checks},indent=2))


if __name__=="__main__":
    run()
