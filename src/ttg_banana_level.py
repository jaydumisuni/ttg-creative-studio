#!/usr/bin/env python3
"""Banana Level architecture for TTG Creative Studio.

Banana Level is the wow layer: absurdly easy, surprisingly powerful, and fun
without making the product unserious. It sits above Easy/Advanced/Motion modes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BananaWorkflow:
    id: str
    name: str
    promise: str
    input_needed: tuple[str, ...]
    output_created: tuple[str, ...]
    ai_optional: bool = True


BANANA_WORKFLOWS = (
    BananaWorkflow(
        "make_it_pop",
        "Make It Pop",
        "Instantly improves a flat design with premium glow, contrast, spacing and depth.",
        ("current_project",),
        ("polished_still", "editable_layers"),
    ),
    BananaWorkflow(
        "turn_logo_into_intro",
        "Logo To Intro",
        "Turns a logo/wordmark into a cinematic intro proof with motion frames.",
        ("logo_asset", "brand_name"),
        ("intro_still", "motion_preview", "editable_project"),
    ),
    BananaWorkflow(
        "poster_to_motion",
        "Poster To Motion",
        "Takes a static poster and creates a moving social/video version.",
        ("poster_image",),
        ("motion_preview", "timeline_project"),
    ),
    BananaWorkflow(
        "fix_my_design",
        "Fix My Design",
        "Analyzes a weak layout and applies alignment, hierarchy and spacing fixes.",
        ("current_project",),
        ("cleaner_project", "change_report"),
    ),
    BananaWorkflow(
        "brand_everything",
        "Brand Everything",
        "Applies brand colors, logo, typography and export presets across a project.",
        ("brand_kit", "current_project"),
        ("branded_project", "export_set"),
    ),
)


def workflow_ids() -> list[str]:
    return [workflow.id for workflow in BANANA_WORKFLOWS]


def find_workflow(workflow_id: str) -> BananaWorkflow:
    for workflow in BANANA_WORKFLOWS:
        if workflow.id == workflow_id:
            return workflow
    raise KeyError(workflow_id)
