# Creative Studio Video Lab — Standalone V1

Standalone Creative Studio owns real video clip import, inspection, timeline editing and MP4 export. It does not depend on Hunter, Ptah or an AI provider.

## GUI
Use Add → Video Clip · Inspect / Import or Tools → Video Lab · Inspect / Import.
Select an MP4, MOV, MKV or WebM file. The dialog reads real stream metadata and three genuine frame previews in a Qt worker. Choose source trim, timeline start and speed (0.25–4x), then import as an editable Studio video layer. Keep source audio only when speed is 1x; higher/lower speed otherwise would create sound desynchronization. Choose either a link to existing video (default; no duplicate disk storage) or opt-in project-local copy with content-hash deduplication.

Canvas renders source frames at actual clip time. Playback and timeline scrubbing advance through rendered frames. Existing text, images, effects, keyframes and audio are composited by the native Studio engine. MP4 export runs on a background Qt worker and uses the existing atomic media export path. The project remains editable after save/reopen.

## Understanding
Inspection is actual local FFmpeg/FFprobe metadata and frame pixels—not generated footage or invented semantic objects. If an already-installed local vision model exists, the Video Lab can optionally request three advisory descriptions using the existing direct local vision interface. Without that model, all non-semantic video editing/inspection still works. Semantic claims require human review.

## Limitations
Source size limited to 2 GiB, decode to 16 megapixels, preview cache eight bounded images; Studio video timelines up to 600 seconds. Source footage may be longer but must be trimmed to the timeline budget. Actual FFmpeg video decoding may not be suitable for long 4K/multicam productions or guaranteed smooth real-time playback. The Video Export Pack must provide FFmpeg. FFprobe is preferred; when it is absent, measured FFmpeg stream diagnostics provide bounded fallback or reject unclear media.

Linking external clips consumes no extra storage but source links may break when moved. Choose Copy into project for portability.

FreeVideo and other generative video engines are independent optional providers: no licensed model, large weights or GPU checkpoint is downloaded by Video Lab, and no unqualified AI video generation is asserted. No Hunter integration is configured here.

## Tests
The script scripts/test_standalone_video.py builds real red/blue sample clips with audio, imports them, verifies frame changes, timing/trim, actual Qt inspection, undo-safe editable layers, save/reopen, final MP4 with source audio, cleanup and deduplicated project copying. Cross-platform qualification is in .github/workflows/studio-standalone-video.yml. Source qualification is not signed production release acceptance.
