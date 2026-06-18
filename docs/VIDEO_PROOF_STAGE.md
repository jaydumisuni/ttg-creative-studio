# Video Proof Stage

Video proof is not release. Video proof only starts after the visual proof package is reviewed and accepted.

## Required order

1. Generate visual proof package:

```powershell
python scripts\generate_visual_proof_package.py
```

2. Review generated artifacts:

- `outputs/index.html`
- `outputs/VISUAL_PROOF_REVIEW.md`
- `outputs/ttg_reference_still.jpg`
- `outputs/reference_motion_contact_sheet.jpg`
- `outputs/reference_motion_preview.gif`

3. Create local review gate file only if the proof is accepted for video proof:

```json
{
  "review": "accepted_for_video_proof",
  "still_checked": true,
  "contact_sheet_checked": true,
  "gif_checked": true,
  "release_ready": false
}
```

Save that as:

```text
outputs/ttg_visual_review.json
```

4. Build video proof:

```powershell
python scripts\build_video_proof.py
```

## Important blocks

- `build_video_proof.py` runs `check_video_gate.py` first.
- If the review file is missing or invalid, video proof is blocked.
- If FFmpeg is missing, video proof is blocked with a clean message.
- Release packaging remains blocked even after video proof succeeds.

## Output

```text
outputs/ttg_reference_video_proof.mp4
```

This MP4 is a proof artifact only, not the final release intro and not proof that the full Creative Studio app is release-ready.
