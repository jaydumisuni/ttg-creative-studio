#!/usr/bin/env python3
"""Cinematic intro project builders for TTG Creative Studio."""

from __future__ import annotations

from ttg_project_schema import Keyframe, Layer, TTGProject, Transform


class IntroBuilder:
    def build_ttg_intro(self) -> TTGProject:
        return self.build_reference_intro()

    def build_reference_intro(self) -> TTGProject:
        project = TTGProject(name="THETECHGUY Reference Cinematic Intro", project_type="motion")
        project.canvas.width = 1920
        project.canvas.height = 1080
        project.canvas.fps = 30
        project.canvas.duration = 8.0
        project.canvas.background = "#03040E"

        bg = Layer(id="bg_world", type="shape", name="Cyber floor background", properties={"shape": "rectangle", "width": 1920, "height": 1080, "fill": "#03040E", "reflection": True})
        particles = Layer(id="particles", type="particle", name="Purple cyan particle field", properties={"density": 360, "colors": ["#BC13FE", "#00E5FF", "#3A5BFF"], "trail": True})
        ghost = Layer(
            id="ghost_hero",
            type="image",
            name="Official TTG Ghost Hero",
            transform=Transform(x=760, y=95, scale_x=0.34, scale_y=0.34),
            properties={"path": "resources/logo.png", "locked_design": True, "glow": True, "glow_blur": 18, "reflection": True},
            keyframes={"position": [Keyframe(0.6, [760, -220, 0], "ease_out_back"), Keyframe(2.2, [760, 95, 0], "ease_out_back")]},
        )
        wordmark = Layer(
            id="wordmark",
            type="text3d",
            name="THETECHGUY wordmark",
            transform=Transform(x=250, y=610),
            properties={
                "text": "THETECHGUY",
                "size": 180,
                "color": "#BC13FE",
                "gradient": True,
                "gradient_start": "#BC13FE",
                "gradient_end": "#00E5FF",
                "stroke_width": 3,
                "stroke_fill": "#18002F",
                "shadow": True,
                "glow": True,
                "glow_blur": 16,
                "extrude_px": 24,
                "extrude_color": "#18002F",
                "reflection": True,
                "material": "neon_chrome",
            },
            keyframes={
                "position": [Keyframe(0.0, [250, 820, 0], "ease_out_back"), Keyframe(2.4, [250, 610, 0], "ease_out_back")],
                "opacity": [Keyframe(0.0, 0, "linear"), Keyframe(1.4, 1, "ease_in_out")],
            },
        )
        subtitle = Layer(id="subtitle", type="text", name="DIGITAL SOLUTIONS", transform=Transform(x=450, y=805), properties={"text": "D I G I T A L   S O L U T I O N S", "size": 58, "color": "#F7FAFF", "glow": True, "glow_blur": 7})
        cards = []
        card_data = [
            ("SYSTEMS", 145, 155, "#BC13FE"),
            ("TOOLS", 520, 190, "#BC13FE"),
            ("ISP", 1250, 190, "#00E5FF"),
            ("WEB", 1580, 155, "#00E5FF"),
        ]
        for label, x, y, color in card_data:
            cards.append(Layer(id=f"card_{label.lower()}", type="shape", name=f"{label} glass card", transform=Transform(x=x, y=y), properties={"shape": "rectangle", "width": 245, "height": 245, "fill": "#07132F55", "outline": color, "radius": 20, "glow": True, "reflection": True}))
            cards.append(Layer(id=f"label_{label.lower()}", type="text3d", name=f"{label} label", transform=Transform(x=x + 38, y=y + 160), properties={"text": label, "size": 38, "color": "#F7FAFF", "glow": True, "stroke_width": 1, "extrude_px": 6}))
        tagline = Layer(id="tagline", type="text", name="Tagline", transform=Transform(x=445, y=910), properties={"text": "Fairytale Business — Make a wish, we sort it.", "size": 36, "color": "#F7FAFF", "glow": True, "glow_blur": 5})
        website = Layer(id="website", type="text", name="Website", transform=Transform(x=675, y=985), properties={"text": "thetechguyds.com", "size": 40, "color": "#EAF3FF", "glow": True, "glow_blur": 9})
        project.layers.extend([bg, particles, ghost, *cards, wordmark, subtitle, tagline, website])
        project.audio_markers = [
            {"time": 0.5, "name": "dark startup"},
            {"time": 1.4, "name": "ghost drop"},
            {"time": 2.4, "name": "wordmark lock"},
            {"time": 3.4, "name": "cards power on"},
            {"time": 6.8, "name": "final glow"},
        ]
        return project
