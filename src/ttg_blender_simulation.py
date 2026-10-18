"""Isolated Blender 3D simulation-bake admission, not part of normal rendering.

Only a physically produced Blender cache and an inspected newly saved
.blend can qualify a simulation. Crashes never get silently retried as
success or executed in Studio's Qt process.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import uuid

from ttg_blender_engine import blender_status


class SimulationBakeError(RuntimeError):
    pass


def bake_simulation(blend: str | Path, destination: str | Path, *,
                    object_id: str, kind: str = "CLOTH",
                    frame_end: int = 6, timeout: int = 180) -> dict:
    if kind not in ("CLOTH","GAS","LIQUID"):
        raise SimulationBakeError("Only cloth, gas and liquid bake kinds are permitted")
    if not isinstance(object_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", object_id):
        raise SimulationBakeError("Invalid simulation object identifier")
    if type(frame_end) is not int or not 2 <= frame_end <= 60:
        raise SimulationBakeError("Bake requires 2–60 frames")
    if type(timeout) is not int or not 30 <= timeout <= 900:
        raise SimulationBakeError("Bake runtime must be bounded")
    path = Path(blend).expanduser()
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".blend":
        raise SimulationBakeError("Bake source must be an existing normal Blender scene")
    if not 100 <= path.stat().st_size <= 256 * 1024**2:
        raise SimulationBakeError("Bake source outside size budget")
    path = path.resolve()
    dest = Path(destination).expanduser()
    if dest.is_symlink() or dest.exists() or not dest.parent.is_dir():
        raise SimulationBakeError("Bake destination must be a new project directory")
    dest = dest.resolve()
    blender = blender_status()
    if not blender["available"]:
        raise SimulationBakeError("Blender executable unavailable: cannot bake physics")
    runner = (Path(__file__).resolve().parent.parent/"integrations"/"blender"/
              "gpl_simulation_baker.py")
    if not runner.is_file():
        raise SimulationBakeError("Licensed isolated Blender baker is missing")
    # Fluid domains store an on-disk cache directory path in the .blend.
    # Keeping the admitted destination fixed avoids invalidating that path
    # through a final directory rename. On any failure this directory is
    # removed, so partial cache files are never admitted.
    staging = (dest if kind in ("GAS","LIQUID")
               else dest.parent / (".ttg-bake-" + uuid.uuid4().hex))
    staging.mkdir(mode=0o700)
    try:
        cmd = [
            blender["executable"], "--background", "--factory-startup",
            "--disable-autoexec", "--python-exit-code", "43", str(path),
            "--threads", "2", "--python", str(runner), "--",
            str(staging), object_id, kind, str(frame_end),
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            raise SimulationBakeError("Blender physics bake timed out (no acceptance)") from None
        if r.returncode:
            raise SimulationBakeError(
                "Isolated Blender simulation failed, no bake accepted: " +
                (r.stderr[-430:] if r.stderr else r.stdout[-430:])
            )
        result_file = staging/"simulation-proof.json"
        output_file = staging/"baked.blend"
        if not result_file.is_file() or not output_file.is_file():
            raise SimulationBakeError("Blender produced no physical bake evidence")
        proof = json.loads(result_file.read_text())
        if proof.get("status") != "baked" or proof.get("kind") != kind:
            raise SimulationBakeError("Blender did not independently confirm a bake")
        if output_file.stat().st_size < 100:
            raise SimulationBakeError("No saved baked Blender scene")
        if staging != dest:
            os.rename(staging, dest)
        return {**proof, "blend": str(dest/"baked.blend"),
                "receipt": str(dest/"simulation-proof.json")}
    except Exception:
        # Stage is new and owned exclusively by this request; never touch
        # the input scene or a preexisting directory.
        import shutil
        shutil.rmtree(staging, ignore_errors=True)
        raise
