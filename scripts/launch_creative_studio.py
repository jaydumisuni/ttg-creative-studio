#!/usr/bin/env python3
"""Launch TTG Creative Studio from a source checkout."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_creative_app import run

def main() -> int:
    # The frozen desktop executable has a bounded, noninteractive smoke path.
    # This checks its bundled Qt/plugins without claiming user GUI acceptance.
    if "--self-check" in sys.argv:
        import json
        from PyQt6.QtWidgets import QApplication
        from ttg_action_engine import ActionEngine
        from ttg_canvas_engine import CanvasRenderer, RenderContext
        app = QApplication.instance() or QApplication([])
        project = ActionEngine().new_project("Frozen Creative Studio Smoke", "image")
        project.canvas.width, project.canvas.height = 48, 48
        actual = CanvasRenderer(RenderContext(ROOT)).render(project)
        print(json.dumps({
            "application": "TTG Creative Studio",
            "packaged_imports": True,
            "renderer_size": list(actual.size),
            "qt": bool(app),
        }))
        return 0
    if "--qualify-gui" in sys.argv:
        import faulthandler
        import json
        import os
        position = sys.argv.index("--qualify-gui")
        proof_dir = Path(sys.argv[position + 1]) if len(sys.argv) > position+1 else None
        if proof_dir is None or not proof_dir.is_dir() or list(proof_dir.iterdir()):
            # Existing proof must never be overwritten, including transient
            # diagnostics for a failed second invocation.
            return 3
        diag = proof_dir / "gui-failure.txt"
        stage = proof_dir / "gui-stage.txt"
        stack = proof_dir / "gui-hang-stack.txt"
        old_stage = os.environ.get("TTG_STUDIO_GUI_STAGE_FILE")
        try:
            stage.write_text("launcher-entered\n", encoding="utf-8")
            os.environ["TTG_STUDIO_GUI_STAGE_FILE"] = str(stage)
            with stack.open("w", encoding="utf-8") as trace:
                faulthandler.dump_traceback_later(45, file=trace, repeat=False)
                try:
                    if len(sys.argv) != position + 2:
                        raise ValueError("--qualify-gui needs exactly one proof directory")
                    # Import must be within this boundary: a missing PyInstaller
                    # module must not show a modal traceback on unattended CI.
                    from ttg_frozen_gui_probe import qualify_gui
                    report = qualify_gui(proof_dir)
                finally:
                    faulthandler.cancel_dump_traceback_later()
            # Remove only these transient QA trace files on success;
            # immutable four-file evidence receipt remains unchanged.
            stage.unlink(missing_ok=True)
            stack.unlink(missing_ok=True)
            print(json.dumps({"result": report["result"], "checks": len(report["checks"])}))
            return 0
        except Exception as exc:
            if not diag.exists():
                diag.write_text(
                    type(exc).__name__ + ": " + str(exc)[:900] + "\n",
                    encoding="utf-8",
                )
            return 3
        finally:
            if old_stage is None:
                os.environ.pop("TTG_STUDIO_GUI_STAGE_FILE", None)
            else:
                os.environ["TTG_STUDIO_GUI_STAGE_FILE"] = old_stage
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
