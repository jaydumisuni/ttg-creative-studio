# Creative Studio G3/G4 engineering qualification — 15 October 2026

Source: independent Creative Studio branch from main 74f014246f14cad02d3a00c219fa2e3ef78ff81a.

## G3: exact artifact custody (engineering PASS, production signing BLOCKED)

The new scripts/studio_release_manifest.py creates per-OS and per-GitHub-run
candidate custody records after Windows install/run/uninstall and Linux
portable GUI qualification. They identify exact source commit, workflow ID,
platform, artifact name, file length, SHA-256, packaging dependency versions,
and Authenticode presence or absence. The same files are reverified before
CI publishes the manifests as separately downloadable artifacts.

These records are NOT signed release attestations. A PE signature is only
classified UNVERIFIED_SIGNATURE until a trusted publisher certificate and
Windows operating system verification are present; unsigned Windows installers
are labeled UNSIGNED. Linux tar files are labeled UNSIGNED_ARCHIVE.
The verifier rejects forged production_release_ready claims, modified files,
wrong source SHA, traversal entries, unsafe symlinks, special files and
signature-presence drift. Normal internal PyInstaller symlinks remain allowed.

The 13 adversarial tests pass on KRATOS. Final code signing is still blocked
on a genuine approved identity and a protected release environment.

## G4: editor stress and autosave recovery (CI PASS, physical QA PENDING)

The native small-raster cache now holds up to 16 reusable sources, only
for images of 1 million decoded pixels or fewer. The decoded cached RGBA
pixel data is therefore bounded to around 64 MiB, even when a highly
compressed file is tiny but would otherwise expand to an enormous bitmap.
Cache identity includes resolved asset path, modification timestamp and size.

The 13 new CI-scale checks pass: deterministic 1400x900 canvas rendering with
12 image layers and repeated-run cache hits; image-change invalidation;
huge compressed PNG bypass; original project integrity; successful unsaved
autosave recovery; simulated disk-full atomic-replace failure without
loss of the previous snapshot; corrupted recovery rejection; and bounded
snapshot retention. The full existing Studio review gate also passes.

These are NOT proof of sustained ATHENA hardware/DPI/GPU/accessibility
qualification, and do not substitute for the owner's actual visual approval.

## Current production boundaries

G0: PASS, verified exact GitHub artifact custody from merged PR #16.
G1: BLOCKED, Oracle still denies D:\projects\TTG-Creative-Studio.
G2: BLOCKED, no genuine ComfyUI checkpoint-backed image proof on ATHENA.
G3: Candidate manifest/tests PASS; legitimate trusted signing identity absent.
G4: CI-scale stress PASS; physical and visual acceptance pending.
G5: NO-GO until G1-G4 real acceptance and final release authorization.

No changes to Ptah, REA, Hunter, production credentials, Oracle allowed roots
or public distribution occurred. Ptah and REA remain optional engineering
helpers, never Creative Studio runtime dependencies.
