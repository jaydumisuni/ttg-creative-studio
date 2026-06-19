# Advanced Mode Presets

Advanced Mode should not feel like a pile of random buttons. It should expose professional presets first, then detailed editable controls.

Preset catalog source:

```text
src/ttg_advanced_presets.py
```

## Text material presets

- Neon Chrome
- Glass White
- Deep Purple 3D

## Effect stack presets

- Premium Wordmark Stack
- Glass Card Stack
- Cyber Floor

## Motion presets

- Dark Start Reveal
- Side Light Wipe
- Final Glow Lock

## Export presets

- YouTube Intro 1080p
- Social Preview GIF

## UI direction

The Advanced panel should eventually show these groups as dropdowns/cards:

```text
Text Material | Effects | Scene | Motion | Export
```

Each preset should apply real editable properties to the selected layer/project. A user should be able to choose a professional preset quickly, then fine tune exact values in Properties.

## Quality target

The reference intro should be buildable from visible presets and editable controls, not only from a hidden script. The hidden renderer is proof of direction; the app must later expose the same capability in Advanced Mode.
