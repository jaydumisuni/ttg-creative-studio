#!/usr/bin/env python3
"""Execute Studio's own production selector from any approved workspace."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from ttg_production_director import ProductionDirector, ProductionError


def main() -> int:
    p=argparse.ArgumentParser(description="TTG Creative Studio autonomous production")
    p.add_argument("--instruction",required=True)
    p.add_argument("--catalog",type=Path,required=True,action="append",
                   help="Approved local resource directory (repeatable)")
    p.add_argument("--output-root",required=True,type=Path)
    p.add_argument("--output-name",default="studio_production")
    p.add_argument("--reference",type=Path)
    p.add_argument("--exact",action="store_true",
                   help="Reuse verified editable image elements to recreate the supplied reference exactly")
    p.add_argument("--dry-run",action="store_true")
    args=p.parse_args()
    try:
        director=ProductionDirector(args.catalog,args.output_root)
        receipt=director.produce(
            instruction=args.instruction,reference=args.reference,
            exact=args.exact,output_name=args.output_name,dry_run=args.dry_run
        )
    except (ProductionError,OSError,ValueError) as exc:
        print(json.dumps({"ok":False,"error":str(exc)}))
        return 2
    print(json.dumps({"ok":True,"receipt":receipt},indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
