# TTG Creative Studio Pack System

The installer must stay light. Heavy features must be downloaded only when needed.

## Install model

Core installer includes the app shell, 2D editor foundation, project schema, pack manager, small TTG resources, and basic export tools.

Core installer does not include large model files, 3D template packs, sound packs, stock backgrounds, large fonts, or optional render packs.

## Runtime behavior

When a user opens a feature that needs a missing pack, the app should ask before downloading it.

Example message:

```text
This feature needs the Motion Intro Pack. Download now?
```

## Local storage

Use the app data folder for downloaded packs, manifests, and cache. Large files should not live inside the source repo.

## Pack manifest example

```json
{
  "id": "motion-intro",
  "name": "Motion Intro Pack",
  "version": "0.1.0",
  "kind": "motion",
  "required": false,
  "description": "Cinematic logo reveal templates, particles, light streaks and sound hits.",
  "files": [
    {
      "name": "cinematic_intro_templates.zip",
      "url": "https://github.com/jaydumisuni/ttg-creative-studio/releases/download/packs-v0.1/cinematic_intro_templates.zip",
      "path": "templates/cinematic_intro_templates.zip",
      "size_mb": 120,
      "sha256": "replace-later"
    }
  ]
}
```

## Planned packs

### bg-removal

Background removal model pack. Download only when the user needs background removal.

### motion-intro

Logo reveal and YouTube intro assets: 3D text presets, light streaks, particles, sound hits, and intro templates.

### schematic-symbols

Repair, ISP, PCB and diagram symbols: connectors, phones, routers, network nodes, PCB blocks, arrows and measurement lines.

### ttg-brand

Official THETECHGUY brand assets: ghost logo, wordmark, colors, templates, and YouTube assets.

### ai-assist

Optional AI helpers. This must remain optional. The editor must work without it.
