# Creative Studio — installed GUI qualification (15 October 2026)

## Scope

This adds **real application-window acceptance** to the existing Windows and
Linux disposable-runner engineering builds. It is a supplement to the prior
frozen-app imports/self-check and Inno Setup install/uninstall test.

`--qualify-gui <empty-directory>` opens the same Qt main window users see,
creates an editable Studio document, selects a text layer, edits its text,
tests Undo and Redo, saves and reloads the project, exports nonblank original
PNG artwork, and records an actual Qt window screenshot. It closes the
application without starting the normal indefinite user event loop.

The generated evidence is:

- `gui-editable.ttgstudio.json` — native editable two-layer saved document.
- `gui-export.png` — exported 480×320 rendered image.
- `gui-window.png` — actual main window capture, at least 1024×640.
- `gui-proof.json` — nine checks and SHA-256 digests for the above three files.

`scripts/verify_frozen_gui_proof.py` checks saved layers, actual PNG headers
and dimensions, file bytes, hashes, and exact evidence schema. It must fail if
evidence changes or if a previous proof directory is reused.

On CI, the Python source test and both frozen application tests must pass.
The Windows Inno Setup installer is installed into a disposable runner path,
the **installed executable** creates fresh UI proof, and then the app is
uninstalled. Linux smoke runs both the extracted frozen program and the
installed user-prefix launcher, with fresh independent proof. Proof artifacts
are uploaded to GitHub Actions.

These tests confirm native GUI functionality in offscreen hosted-runner
conditions; **they do not prove** physical ATHENA permission, real human
interaction/usability acceptance, signed Windows release, a provisioned
ComfyUI checkpoint or model-backed inference. The app is not automatically
installed onto ATHENA or publicly published by these changes.

No Ptah, Hunter, Oracle workstation policy, credentials or release authority
is modified.
