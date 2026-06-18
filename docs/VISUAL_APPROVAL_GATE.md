# Visual Approval Gate

TTG Creative Studio must not move to release/build packaging because code exists. It moves forward only when the visual proof is acceptable.

## Current proof order

1. Repo renders `outputs/ttg_reference_still.jpg`.
2. Repo scores the still with `outputs/ttg_reference_still_score.json`.
3. If the still fails automated guardrails, motion is blocked.
4. If the still passes, repo renders 48 motion proof frames.
5. Repo builds `outputs/reference_motion_contact_sheet.jpg`.
6. Repo scores motion with `outputs/reference_motion_score.json`.
7. Human approval is required before MP4/video/export/release work.

## Human approval checklist

The still/contact sheet must be judged against the intended THETECHGUY cinematic standard:

- Ghost/logo is visible and correct.
- THETECHGUY wordmark feels premium, not flat 2D text.
- SYSTEMS / TOOLS / ISP / WEB cards look intentional and professional.
- Scene has depth: floor/perspective/light/reflection/glow.
- Composition looks like a serious company intro, not a tutorial slide.
- No duplicate random text added on top of artwork.
- Motion proof feels like elements are coming alive, not only zooming.

## Blocked until approval

The following stay blocked until this visual gate is passed:

- MP4 final intro export.
- YouTube intro production.
- Installer/release packaging.
- Claims that Creative Studio is ready.

## Local commands, only when needed

```powershell
python scripts\verify_reference_still.py
python scripts\verify_reference_motion.py
```

## GitHub Actions artifact

Workflow: `Reference Still And Motion Verification`

Artifact should contain:

- `ttg_reference_still.jpg`
- `ttg_reference_still_score.json`
- `reference_motion_contact_sheet.jpg`
- `reference_motion_score.json`
- `reference_motion_frames/*.jpg`
