# Creative Studio Campaign Designer v1 — 15 October 2026

## Goal and current boundary

Deliver an independent offline editing feature that produces visually coherent campaigns
from a short user brief. This is not text-to-image AI. Compositions are rendered by
Creative Studio's own Pillow-based canvas engine, using original procedural illustration,
native shapes and editable text layers. No Ptah runtime, Hunter, cloud key or account is
required. Production image-generation integrations remain a separate roadmap area.

## Implemented user journey

Open the source application via `python scripts/launch_creative_studio.py` and select
**Design Campaign** in the main toolbar or **Templates → New Campaign Designer**.

Choose a format (1080×1350 portrait, 1080×1080 social square or 1920×1080 widescreen),
then edit brand, headline, supporting copy, product name, website, CTA and color theme.
Optionally choose an actual product PNG/JPEG/WEBP; without one the engine generates an
original generic smartphone illustration and decorative orbit artwork. Press **Preview
Design** to see a real Studio render, then **Create Editable Campaign**.

The application saves under the user's Documents/TTG Creative Studio/Projects folder,
opens the saved native project automatically, selects its editable headline and sets
the canvas/export asset root to the project folder. Layers can be moved, edited,
recolored, duplicated and exported using the existing Properties, Canvas and Export
controls. Keyboard shortcuts: Ctrl+S, Ctrl+O, Ctrl+Z, Ctrl+Shift+Z and Ctrl+E.
The toolbar scrolls horizontally at compact window widths.

## Technical deliverables

- `src/ttg_campaign_composer.py`: scene briefs, bounded input validation, three
  compositions, font fitting and wrapping, optional original product image preservation,
  assets, editable Studio document, PNG, SHA-256 manifest and portable ZIP.
- `src/ttg_campaign_dialog.py`: real Qt campaign brief, live render preview and handoff.
- `src/ttg_creative_workspace.py`: standalone GUI integration and asset-root correction.
- `scripts/creative_cli.py design-campaign`: headless generation for batch workflows.
- `examples/campaigns/`: three real saved, editable sample projects and export bundles.
- `scripts/verify_campaign_showcase.py`: verifies every committed render against the
  exact saved layers and integrity manifest.
- `scripts/test_campaign_designer.py`: three layouts, asset relocation, ZIP checks,
  source image replacement, invalid briefs, PNG replay, Qt preview, GUI editing root,
  narrow-window toolbar and CLI coverage.
- `.github/workflows/ci.yml`: Windows/Linux CI with focused offscreen
  Qt qualification and prior editor smoke tests.

## Run locally

Install at least Pillow and PyQt6 from the project dependencies (the complete
`requirements.txt` includes optional advanced media/AI dependencies). Then:

```bash
python scripts/launch_creative_studio.py
python -B scripts/test_campaign_designer.py
python -B scripts/verify_campaign_showcase.py
python scripts/creative_cli.py design-campaign ./my-campaign --layout flagship \
  --brand THETECHGUY --headline "BEYOND THE ORDINARY." --accent aqua
```

For headless Qt tests on Linux use `QT_QPA_PLATFORM=offscreen`.

## Limits and next acceptance

This is a functioning offline design vertical slice, not completed Photoshop/Canva/
Filmora parity or a general-purpose AI prompt-to-image engine. The generic smartphone
is a raster asset independently movable and replaceable, not a parametric 3D model.
The sample project uses system-available fonts with fallback, so typography may
vary across different operating systems. The committed Linux example previews are
checked pixel-exactly on Linux and against a bounded pixel-difference budget on
Windows; newly generated projects are verified pixel-exactly on their own host.
Tracked example project JSON is checked out as LF on Windows so SHA-256 source
integrity is not defeated by Git's platform newline conversion.

Broader photo retouching, generative-image provider quality, advanced real-time motion,
final accessibility review, Windows installer signing and subjective art-direction
acceptance remain separate work. Do not promote this engineering feature to a full
commercial application release solely because its CI passes.
