# TTG Native Image Brain

This is the future native image intelligence layer for TTG Creative Studio and Hunter.

It is **not** a reserved-provider system.

The goal is to build our own multimodal image engine that takes the best ideas from image understanding, image generation, image editing, layout reasoning and tool-worker execution, then shapes them for TTG Creative Studio and Hunter.

## Rule

The editor must work without this brain.

The order is:

```text
Core editor first
Deterministic Banana actions second
TTG Native Image Brain third
External APIs only as temporary research/borrowed brains when needed
```

## Native modules

The TTG Native Image Brain is planned as modules:

- Vision Encoder
- Layout Reasoner
- Scene Planner
- Image Generator Core
- Edit Planner
- Tool Worker Router

## Hunter usage

Hunter should use this as a worker:

```text
Hunter request → TTG Native Image Brain → TTG action plan → editable project/layers/assets
```

Hunter should not hide the result as a flat image only. The goal is editable Creative Studio output wherever possible.

## Supported future tasks

- Understand image.
- Suggest edits.
- Generate asset.
- Generate variants.
- Image to template.
- Prompt to scene.
- Scene to layers.
- Render plan.
- Edit plan.
- Banana workflow planning.

## Important architecture decision

We are not building around these as reserved provider slots:

```text
native multimodal transformer provider
DALL-E 3 compatible provider
ChatGPT Images 2.0 style provider
```

Instead, TTG builds its own native image brain and may borrow external systems only when useful for research, comparison or temporary capability. Confirmed lessons should become TTG knowledge/capability later.

## Safety and quality

- The native brain must be optional until mature.
- Bad output must not break the project.
- Generated/edited outputs should be reviewed before video/release stages.
- Deterministic tools remain the fallback.
- Output should be editable where possible, not only a flattened bitmap.
