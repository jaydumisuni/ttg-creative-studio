# No Release Until

This file is a hard quality checklist. Passing code checks or generating a video proof is not enough for release.

## Visual proof must pass

- `outputs/index.html` exists and opens cleanly.
- `outputs/ttg_reference_still.jpg` looks premium enough for THETECHGUY.
- `outputs/reference_motion_preview.gif` feels alive, not only zooming.
- `outputs/reference_motion_contact_sheet.jpg` shows a sensible sequence.
- No random text is added over the art.
- Ghost/logo is correct and visible.

## App quality must pass

- Advanced Mode panel is usable.
- Asset/template browser is usable.
- Properties panel edits real selected layer values.
- Canvas click/drag/select works reliably.
- Timeline preview is understandable.
- Background remover feels like part of Creative Studio, not a separate old app.
- Missing optional packs show clean messages.

## Build quality must pass

- Clean clone installs dependencies.
- App launches on Windows.
- Visual proof scripts run.
- Optional Video Export Pack boundary works.
- Installer installs small core only.
- No oversized models/packs are forced into the core installer.

## Release remains blocked if any are false

- Visual proof accepted.
- Video proof accepted.
- App alpha test accepted.
- Build test accepted.
- Installer test accepted.

Until all are true, the correct status is not release-ready.
