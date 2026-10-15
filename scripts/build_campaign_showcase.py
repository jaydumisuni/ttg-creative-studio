#!/usr/bin/env python3
"""Build three original, relocatable Creative Studio showcase projects."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from ttg_campaign_composer import CampaignBrief, compose_campaign

EXAMPLES = (
    CampaignBrief(
        layout="flagship", brand="THETECHGUY",
        headline="REWRITE THE\nPOSSIBLE.",
        subhead="Premium technology. Endless possibilities.",
        product_name="FLAGSHIP EXPERIENCE", cta="EXPLORE WHAT'S NEXT",
        accent="aqua",
    ),
    CampaignBrief(
        layout="social", brand="THETECHGUY",
        headline="AN ICON\nIN THE MAKING.",
        subhead="Built around your ambitions.",
        product_name="THE NEXT EXPERIENCE", cta="DISCOVER MORE",
        accent="violet",
    ),
    CampaignBrief(
        layout="wide", brand="THETECHGUY",
        headline="MAKE EVERY\nMOMENT COUNT.",
        subhead="Technology meets possibility.",
        product_name="DIGITAL SOLUTIONS", cta="EXPLORE THE COLLECTION",
        accent="amber",
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path,
        default=ROOT/"examples"/"campaigns",
        help="New directory for editable samples; existing projects are never overwritten",
    )
    args = parser.parse_args()
    base = args.output.resolve()
    base.mkdir(parents=True, exist_ok=True)
    reports = {}
    for brief in EXAMPLES:
        created = compose_campaign(brief, base/brief.layout)
        reports[brief.layout] = {key: str(path) for key, path in created.items()}
    (base/"README.md").write_text(
        "# Editable Creative Studio campaign samples\n\n"
        "These are original procedurally composed illustrations, not AI-generated images "
        "or manufacturer product photographs. All three use Studio's real layer schema, "
        "renderer and export service.\n\n"
        "Open each campaign.ttgstudio.json in Creative Studio using File > Open Project. "
        "Its assets/ folder must stay beside it. The portable-campaign.zip contains the "
        "project, assets, PNG and SHA-256 manifest and can be extracted elsewhere.\n\n"
        "Choose Design Campaign to create new layouts with your own headlines, colors "
        "and optional product image. The images and editable project are generated locally "
        "without Hunter, Ptah or an image-generation API.\n",
        encoding="utf-8",
    )
    print(json.dumps(reports, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
