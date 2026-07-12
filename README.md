# TTG Creative Studio

Local-first THETECHGUY creative editor built around one product target:

```text
Photoshop power + Canva simplicity + Filmora motion + TTG worker intelligence
```

## Current implemented foundation

- Layer-based editable projects.
- Direct canvas selection, movement, resize and rotate interaction paths.
- Properties engine for layer names, transforms, opacity, text, style properties and effects.
- Timeline engine primitives for clip timing, keyframes and interpolation.
- Advanced text rendering with font loading, alignment, stroke, shadow, glow, gradient and spacing.
- Folder and ZIP asset-package import with safe extraction checks.
- Ad workflow: ZIP/folder assets → editable `.ttgstudio.json` project → visual proof.
- Creative Studio app hooks for importing ad ZIPs and folders.
- Asset/template browser foundation.
- Deterministic Banana Level actions.
- Native TTG image-worker architecture with Hunter bridge and editable-action planning.
- Background cleanup/cutout adapter path.
- Still render, motion-frame, contact-sheet and GIF visual proof generation.
- Frame export and gated MP4 export through optional FFmpeg/Video Export Pack support.
- Benchmark target and benchmark-gap reports.
- Single full review command.

## Run from source

```powershell
python scripts\launch_creative_studio.py
```

## Full review gate

```powershell
python scripts\review_gate_all.py
```

The review gate checks structure, Python compilation, claims against implementation, property/timeline behavior, asset import, ad workflow, canvas interaction, worker paths, presets, offscreen UI wiring, visual proof generation and benchmark-gap reporting.

## Building order

```text
Engine
Workflow
Proof output
UI
Polish
```

The UI is the final shell over working capability, not a substitute for capability.

## Release truth

TTG Creative Studio separates two closure levels:

- **Engine/workflow closure:** implementation, workflow proof, claims gate and visual artifact paths exist.
- **User-release closure:** final UI polish, clean-clone/runtime proof, package installation and target-machine verification are complete.

The repository must not claim more than the code and proof artifacts support.

## Architecture rule

AI is not the foundation. The editor works manually and deterministically first. Hunter and the TTG Native Image Brain coordinate or enhance specialist workflows later without replacing the core editor.
