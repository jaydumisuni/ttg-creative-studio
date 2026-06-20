#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_property_schema import editable_keys_for_layer_type, spec_by_key


def main() -> int:
    text_keys = editable_keys_for_layer_type("text")
    text3d_keys = editable_keys_for_layer_type("text3d")
    shape_keys = editable_keys_for_layer_type("shape")
    ok = True
    ok = ok and "text" in text_keys
    ok = ok and "size" in text_keys
    ok = ok and "gradient" in text_keys
    ok = ok and "extrude_px" not in text_keys
    ok = ok and "extrude_px" in text3d_keys
    ok = ok and "fill" in shape_keys
    ok = ok and spec_by_key("opacity").min_value == 0.0
    ok = ok and spec_by_key("opacity").max_value == 1.0
    print("Property schema check:", "ok" if ok else "not ok")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
