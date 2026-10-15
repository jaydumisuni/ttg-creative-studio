# TTG Creative Studio — Standalone Capability and Release Candidate
15 October 2026. Engineering branch: `studio/release-capabilities-20261015`

## Scope
This changes only Creative Studio. It is independent of Ptah infrastructure and
Hunter. It continues on the previous draft Campaign Designer PR #11. All seven
product areas are worked on here, but not all are eligible for production closure.

## Implemented and tested

**Desktop builds.** The former Windows `build_exe.ps1` and
`build_installer.ps1` mistakenly built Background Remover. Both now target
`TTG Creative Studio.spec` and its Inno Setup source. The installer AppId
and output path are corrected. A frozen `--self-check` tests real Qt startup,
Pillow imports and the native renderer without entering an indefinite UI loop.
GitHub Actions builds a Windows installer candidate and a Linux portable
one-folder application; local `install_linux_portable.py` supports a
non-destructive user-prefix install. **Artifacts are UNSIGNED and
pre-release**; no signing keys are included. Current production signing and
ATHENA physical installation must be qualified separately.

**AI image creation.** The Image Lab runs offline brightness/contrast/color
enhancement without a model. When the user provides a real local ComfyUI
endpoint and a checkpoint actually installed there, it submits real
CheckpointLoader/CLIP/KSampler/VAE/SaveImage jobs and retrieves the result
bytes. It supports text-to-image, image-to-image, and white-mask inpainting
(i.e. region replacement). The UI runs these jobs outside the Qt main thread,
imports the image as an editable layer, and errors clearly if the service,
model or inference result is absent. The ComfyUI protocol is tested with a
local synthetic HTTP fixture; **this is NOT proof of high-quality diffusion
inference on ATHENA or KRATOS**. No default checkpoint download or paid cloud
provider is performed.

**Professional image editing.** Layer raster masks, brush-painted selection
masks, brightness/contrast/saturation/sharpen/grayscale effects and offline
enhancement are backed by the native renderer. The original imported file
is retained. Masks/effects are stored as editable project properties, and
Undo/Redo operates through Studio's existing history. No claim of Photoshop
feature parity, advanced vector paths or full retouching.

**Video/audio.** Existing timeline retains keyframe interpolation. Added
slide-up and fade-out presets, bounded frame counts, unique per-export
frame directories and audio-track import. FFmpeg can combine audio tracks,
produce H.264/AAC MP4, and fail without a partial success claim if no
encoder is installed. A real audio-bearing MP4 test passed on KRATOS after
installing an isolated `imageio-ffmpeg` test binary (outside tracked sources).
No claim of full Filmora-class editing or GPU-accelerated encoding.

**Templates.** Added six one-click editable campaign briefs spanning
electronics, luxury, retail, sports, services and creators to the existing
portrait, square and widescreen composers.

**Usability and product acceptance.** The standalone Image Lab, brush
selection, GIF/MP4 paths, typography/campaign GUI and current
Studio application are testable in offscreen Qt. Final human design review,
physical Windows installation acceptance and accessibility audits remain
separate. PR #11 owner approval is not automatically granted or merged.

**Recovery/performance.** Edit state is snapshotted atomically every 45
seconds when changed; recovery can be opened explicitly **without overwriting
the original saved project**. Snapshot retention is bounded at 15. Native
raster asset caching uses up to eight small images, automatically invalidating
a cache entry when its source's size or modification time changes.
This is a bounded CPU optimization, not evidence of GPU acceleration.

**Updates.** The UI can inspect an optional approved HTTPS release manifest,
rejects untrusted hosts and incorrect hashes, and offers an official release
page; it NEVER automatically executes an installer. No update feed is
configured by default, and deployment of a signed update service is pending.

## Qualification and boundaries

- `python -B scripts/test_studio_completion.py`: 29/29 checks on KRATOS
  with real FFmpeg, masks, asset caching, crash recovery, Qt Image Lab and
  local ComfyUI protocol contract. The generated PNG in the mock protocol is
  a fixture, not an inference result.
- `python -B scripts/test_release_packaging.py`: validates both build
  scripts, Linux user-prefix install, frozen self-check and update metadata.
- Existing `test_campaign_designer.py`, `verify_campaign_showcase.py`
  and core editor regressions remain required.
- `.github/workflows/studio-release-candidate.yml`: intended independent
  Windows/Linux artifact build, application smoke and installer checks.
  **Do not claim hosted build success until the exact-head jobs finish.**
- No production signing materials, external infrastructure or Ptah files
  are modified.

## Explicit remaining closure gates

1. Signed Windows installer from an approved code-signing identity; install
   and run on ATHENA or an approved physical customer-equivalent machine.
2. Provision and qualify a real image-generation checkpoint and its inference
   quality/performance (not just the ComfyUI client protocol).
3. Art-direction acceptance for example presets and generated images.
4. Full accessibility/keyboard/assistive-technology review.
5. Larger-project benchmarks, memory-pressure and hardware GPU optimization
   when measured bottlenecks warrant it.
6. Owner-directed merge, versioning and production rollout.
