# Review Gate

The generated visual proof package must be reviewed before any final video work.

Review these generated files:

- outputs/ttg_reference_still.jpg
- outputs/reference_motion_contact_sheet.jpg
- outputs/reference_motion_preview.gif
- outputs/ttg_visual_proof_manifest.json

After review, create this local file if the proof is accepted for the next stage:

outputs/ttg_visual_review.json

Example:

{
  "review": "accepted_for_video_proof",
  "still_checked": true,
  "contact_sheet_checked": true,
  "gif_checked": true,
  "release_ready": false
}

This only allows video proof work. It does not mark the app release-ready.
