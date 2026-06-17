#!/usr/bin/env python3
"""Cinematic intro project builder for TTG Creative Studio."""

from __future__ import annotations

from ttg_project_schema import Keyframe, Layer, TTGProject, Transform


class IntroBuilder:
    def build_ttg_intro(self) -> TTGProject:
        project = TTGProject(name="TTG Cinematic Logo Reveal", project_type="motion")
        project.canvas.width = 1920
        project.canvas.height = 1080
        project.canvas.fps = 30
        project.canvas.duration = 8.0

        bg = Layer(id="bg_world", type="shape", name="Dark cinematic background", properties={"shape": "rectangle", "width": 1920, "height": 1080, "fill": "#050614"})
        particles = Layer(id="particles", type="particle", name="Cyan purple particles", properties={"density": 220, "colors": ["#00E5FF", "#BC13FE"], "trail": True})
        wordmark = Layer(
            id="wordmark",
            type="text3d",
            name="THETECHGUY wordmark",
            properties={"text": "THETECHGUY", "material": "neon_metal", "bevel": 0.08, "extrude": 0.32, "size": 120},
            transform=Transform(x=220, y=410),
            keyframes={
                "position": [Keyframe(0.7, [-900, 410, -200], "ease_out_back"), Keyframe(1.8, [220, 410, 0], "ease_out_back")],
                "opacity": [Keyframe(0.6, 0, "linear"), Keyframe(1.2, 1, "ease_in_out")],
            },
        )
        subtitle = Layer(id="subtitle", type="text", name="DIGITAL SOLUTIONS", transform=Transform(x=620, y=560), properties={"text": "DIGITAL SOLUTIONS", "size": 62, "color": "#F7FAFF"})
        ghost = Layer(id="ghost", type="image", name="Official TTG ghost", transform=Transform(x=1320, y=300), properties={"asset": "ttg_ghost_original", "locked_design": True})
        panels = []
        for index, text in enumerate(["SYSTEMS", "TOOLS", "ISP", "WEB"]):
            panels.append(Layer(id=f"panel_{text.lower()}", type="text3d", name=f"{text} panel", transform=Transform(x=180 + index * 390, y=180), properties={"text": text, "material": "glass_neon", "size": 52}))
        tagline = Layer(id="tagline", type="text", name="Tagline", transform=Transform(x=610, y=850), properties={"text": project.brand.slogan, "size": 34, "color": "#F7FAFF"})
        website = Layer(id="website", type="text", name="Website", transform=Transform(x=820, y=915), properties={"text": project.brand.website, "size": 30, "color": "#00E5FF"})
        project.layers.extend([bg, particles, wordmark, subtitle, ghost, *panels, tagline, website])
        project.audio_markers = [
            {"time": 0.7, "name": "startup bass hit"},
            {"time": 1.8, "name": "wordmark lock"},
            {"time": 3.2, "name": "ghost reveal"},
            {"time": 4.5, "name": "panels lock"},
            {"time": 6.6, "name": "final chime"},
        ]
        return project
