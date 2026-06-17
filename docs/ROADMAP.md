# TTG Creative Studio Roadmap

TTG Creative Studio is not meant to be a small background remover. The current background remover becomes the first tool inside a larger local-first creative engine.

The core rule: **the app must be powerful without AI.** Hunter/AI will later operate the same tools a human can use manually.

## Phase 0 — Source cleanup

- Keep source on GitHub.
- Keep build outputs, installers, models, and prereqs out of the repo.
- Use GitHub Releases or another pack host for heavy optional packs.
- Keep installer small.

## Phase 1 — Core editor foundation

Goal: Photoshop/Canva style editable project foundation.

- `.ttgstudio` project files.
- Layer model.
- Asset model.
- Brand kit model.
- Save/load project JSON.
- Basic canvas preview.
- Import image/logo/text.
- Export PNG/JPG.

## Phase 2 — Timeline and motion

Goal: Filmora/CapCut style movement, but editable and brand-controlled.

- Timeline panel.
- Keyframes for position, scale, rotation, opacity.
- Keyframes for blur, glow, shadow.
- Audio markers.
- Preview motion.
- Export MP4 via FFmpeg.

## Phase 3 — Pack system

Goal: small installer, heavy power on demand.

Core app installs small. Optional packs download only when needed.

Packs:

- Background Removal Pack
- Motion Intro Pack
- 3D Logo Pack
- Schematic Symbols Pack
- TTG Brand Pack
- Sound Effects Pack
- AI Assist Pack

## Phase 4 — Diagram and schematic tools

Goal: make repair, ISP, PCB, and system drawings easy.

- Snap grid.
- Connector lines.
- Arrow/callout tools.
- Measurement lines.
- Component blocks.
- ISP/network symbols.
- PCB-style traces.
- Export clean technical sheets.

## Phase 5 — 3D / cinematic intro engine

Goal: the YouTube intro problem becomes easy.

- 3D text layers.
- Bevel/extrude settings.
- Metallic/neon materials.
- Camera fly-through.
- Particles.
- Light streaks.
- Service cards: SYSTEMS / TOOLS / ISP / WEB.
- Synced sound markers.
- Export final MP4.

## Phase 6 — Hunter control

Goal: Hunter uses the real tool, not random image generation.

Hunter should create or edit `.ttgstudio` project JSON and call app actions:

- create project
- add layer
- set keyframes
- apply template
- require pack
- render preview
- export final

AI is the operator. The editor is the engine.
