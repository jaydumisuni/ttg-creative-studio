# Image Intelligence Worker

This is a future optional worker layer for TTG Creative Studio and Hunter.

It exists so Hunter can later understand images, suggest edits, generate assets and drive Banana Level workflows without redesigning the editor.

## Rule

The editor must work without this worker.

The worker is optional:

```text
Core editor first
Deterministic Banana actions second
Image intelligence worker third
External image providers last
```

## Provider slots

The architecture leaves slots for:

- Native multimodal transformer provider.
- DALL-E 3 compatible generation provider.
- ChatGPT Images 2.0 style generation/editing provider.

These are provider interfaces, not required dependencies.

## Hunter usage

Hunter should use this as a worker:

```text
Hunter request → Image Intelligence Worker → suggested TTG actions → editable project/layers
```

Hunter should not hide the result as a flat image only. The goal is to return useful editable actions where possible.

## Supported future tasks

- Understand image.
- Suggest edits.
- Generate asset.
- Generate variants.
- Image to template.
- Prompt to scene.
- Scene to layers.
- Banana workflow planning.

## Safety and quality

- AI output must be optional.
- Bad AI output must not break the project.
- Generated/edited outputs should be reviewed before video/release stages.
- Deterministic tools remain the fallback.
