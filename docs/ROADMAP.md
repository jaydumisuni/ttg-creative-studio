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

## 2026-11-23 — Storytold + Vork specialist donor intake

**Discovery only — no engine/release status change.** Read [STORYTOLD_VORK_DONOR_INTAKE_2026-11-23.md](STORYTOLD_VORK_DONOR_INTAKE_2026-11-23.md) before adding another editor, renderer, model provider or workflow. Compare PhotoCraft/FilmCraft/EffectCraft/Vork/ArtCraft/MaterialCraft/TextureCraft **against each other and the incumbent Studio engines**. Studio keeps the editable project, Director and output receipts. Begin with isolated PSD, timeline, PBR and same-scene Vork-vs-Blender fidelity probes; require permission, license/source pins, deterministic fallback and independent visual proof before adaptation. **No donor capabilities are implemented or admitted by this note.**

## 2026-11-26 — Existing donor roadmap integration

Native interchange subsets were added on the existing Storytold donor-integration branch: PhotoCraft OpenRaster, FilmCraft OpenTimelineIO, EffectCraft basic-shape Lottie, MaterialCraft/TextureCraft exported PBR maps, and VectorCraft basic SVG shapes. Operations are reachable in the existing Studio toolbar, CLI and Hunter tool catalog, with original editable Studio projects preserved.

See the exact supported formats, safety constraints, negative cases and incomplete advanced donor feature coverage in 'STORYTOLD_VORK_DONOR_INTAKE_2026-11-23.md'. This contributes to P1/P2/P4/P5 requirement coverage without declaring entire phases completed. No ArtCraft paid service/model authority added. Vork remains deferred and the current Blender adapter is unchanged.


## 2026-11-26 — Native donor nextwave: clip sequences and reference material previews

Continuing the prior Studio native donor integration, a Tenfold Gen 1 two-lane isolated construction pass added FilmCraft OTIO sequential multi-clip/Gap exchange with original track grouping and actual Studio still/video/audio timing, and a MaterialCraft/TextureCraft reference-lit PBR swatch as an editable native image layer. The swatch is a verified source-map rendering, not a native 3D mesh/UV shader qualification. Existing Studio application, project schema, source editors, output controls and review rules are unchanged. No new coordinator; external Cookpit implementation lanes left running. See `docs/STORYTOLD_VORK_DONOR_INTAKE_2026-11-23.md` for exact scope and remaining donor capabilities. Whole P2/P5 gate acceptance, physical proof, real material production shader and owner release signatures remain separate.


## 2026-11-26 — Native audio fades and Lottie animated shape opacity

Continuing the already-approved Storytold donor approach, the existing TTG Studio native audio/FFmpeg exporter now accepts source-relative validated fade-in/fade-out durations and the existing native Lottie adapter exchanges animated shape opacity, with real canvas alpha at each authored frame. The complete exact-source evidence and limits are in `docs/STORYTOLD_VORK_DONOR_INTAKE_2026-11-23.md`. This is not equivalent to a SoundCraft DAW or full EffectCraft/AniCraft runtime. Existing Studio editor, Blender, system services and release authority unchanged.


## 2026-11-26 — Layer group and SVG multi-point donor nextwave

An additional qualified Tenfold Gen 1 two-lane construction cycle extends the **existing** PhotoCraft-compatible OpenRaster and VectorCraft-compatible SVG adapters: neutral nested OpenRaster group structure is preserved in editable TTG layers, and two-to-128-point SVG polylines roundtrip through native diagram connectors with rendered-pixel proof. Details, explicit unsupported effects, source proof and owner-stage limits are in `docs/STORYTOLD_VORK_DONOR_INTAKE_2026-11-23.md`. This is not full PhotoCraft/PSD or VectorCraft editor capability; P1/P4 whole-stage gates remain unchanged.


### 2026-11-26 — Independent donor bridge: LightCraft/CADCraft

The existing Storytold donor campaign extends Studio's native editable project through LightCraft developed-RAW PNG intake and bounded CADCraft ASCII DXF drawing exchange. Both reuse the existing Studio File/Export UI, manual CLI and typed Hunter job entrypoint. Each is an independently tested, Tenfold-isolated new subfeature; not full RAW development or CAD/DWG/hardware-design equivalence. See the existing STORYTOLD_VORK_DONOR_INTAKE_2026-11-23.md for exact source and proof. Existing P1/P4 owner exit gates, Vork deferral and Blender remain unchanged.


### 2026-11-26 — DNG structural evidence and CAD ARC numeric interchange

Two qualified follow-on native format-subset candidates extend the existing
Studio LightCraft/CADCraft work: DNG IFD0/Version/dimension structural
validation with provenance, and DXF ARC source-preserving presentation
interchange. They reuse existing UI/CLI/job entrypoints. Full LightCraft
raw demosaic and CADCraft mechanical/EDA authority are not provided.
Detailed exact limitations and evidence belong in the existing Storytold
donor intake document.


### 2026-11-26 — LightCraft source integration and Builder ownership correction

The native LightCraft feature now resolves its optional donor RAW development
engine from a source-pinned, Builder-staged component packaged **inside TTG
Creative Studio**. There is no separate installed LightCraft application or
automatic donor download. Its Windows/Linux runtime requires an actual Builder
source build and accepted artifact receipt; absent that, it fails closed.
KRATOS owns source integration and verification; ATHENA is for optional
Windows evidence. See the existing Storytold donor intake document and source
lock. This is an implementation-route correction, not proof of full RAW
demosaicing, production packaging or final owner acceptance.
