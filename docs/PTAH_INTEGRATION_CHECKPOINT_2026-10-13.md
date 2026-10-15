# TTG Creative Studio × Ptah — candidate integration checkpoint

**Date:** 2026-10-13
**Branch:** `integration/ptah-creative-studio-kratos`
**Creative Studio baseline:** `670215de820775ce7f4543cfa52ab6ee9a520301`
**Ptah consumption:** existing checked-out A04/A05/A06/A07 crates, identical across relevant source trees to public `Ptah-space/main` at `5119d40b0b0cde25117c56640422bfd81f263f6b` at initial audit.

## Verified technical claim

A Creative Studio-owned, **embedded Ptah consumer**, not a resident Ptah daemon, runs two bounded specialist commands using Ptah A06 Workspace, A04 Activity/Operation/Attempt receipts, A05 native subprocess Provider, and A07 Object/Revision/CAS read-back/explicit Artifact promotion.

- `scene_edit`: editable 640×360 project, exact position movement, preview, portable ZIP; three A07 Artifacts.
- `ad_from_assets`: three-scene editable motion project, source-asset copy, relative-path bundle, timeline/audio metadata and contact sheet; three A07 Artifacts.
- The ad contact-sheet renderer now resolves project-relative image paths, including after relocation of the bundle.
- A separate process independently checks request-versus-saved project and output pixels before A07 registration.
- Artifact integrity is independently re-read and verified by Ptah CAS; output registration and Artifact promotion use distinct A04 evidence.
- Reopening a completed request with `--resume` rechecks request identity, source digests and image inventory, stored CAS, and durable Workspace, then refuses to allocate a new Attempt.
- Partial runs without the final accepted manifest fail closed; new work needs reconciliation.

## Latest qualification

On KRATOS:

```bash
python3 -B scripts/test_ptah_adapter.py
cargo check --offline --locked --manifest-path integrations/ptah/Cargo.toml
```

**25/25 direct positive/adversarial regression checks PASS** after the follow-up filesystem and CI hardening. No Hunter was used.

Retained latest proof:

```
/home/kratos/projects/TTG-Creative-Studio/.workspace/scratch/ptah-regression-1f3836a4f6/qualification_report.json
```

- Scene proof manifest SHA-256: `a8920b554a937f836843d0840cbb7c832c0678fd8031014621a970b710134015`.
- Ad proof manifest SHA-256: `706d56d532d17971c0d279c40cfc2daca43773dd41cca3d1b07b8a2befc9227f`.
- Each run retains **175 canonical ledger records** across A04, A06 and A07.
- Python syntax AST checks pass.
- Patrol allows all changed Creative Studio-owned paths.
- The Ptah repository was not modified; its pre-existing `browser-provider/node_modules/` untracked directory remains outside this task.

## Deliberate nonclaims / remaining gates

1. The `studio_tool.json` file is a Creative Studio manifest. Ptah-native service/plugin discoverability and registration are not yet integrated.
2. Current demo is **embedded**, with development Provider identity; it is not a production-authenticated enrolled Ptah Node, an always-on daemon, or a deployed multi-host service.
3. Resume proves intact prior completion, not automatic repair/continuation of a partially executed or externally side-effecting workflow. E06 offline synchronization is not claimed.
4. Neither visual beauty, text OCR, logo correctness beyond declared exact text, AI image generation, live model inference, desktop UI, Windows installer, nor client-delivery approval is established.
5. Independent Sergeant review, clean-target build matrix, and acceptance/promotion remain separate gates. Rustfmt was installed on KRATOS; `cargo fmt --check` now passes. The new scoped `.github/workflows/ci.yml` still requires remote exact-head CI confirmation.

**Next owner-managed implementation frontier:** qualify Ptah's supported resident dispatch/application registry with authenticated Node authority. Then attach this independently working adapter under that actual contract; test process interruption, lease expiry, restart and artifact recovery with physical proof before production enrollment. No Ptah source changes should be made from Creative Studio.

## Follow-up engineering hardening — 2026-10-14

- Separate Linux CI now checks out a **pinned Ptah dependency**, builds the actual adapter, checks formatting and executes the real positive/negative proof suite.
- The embedded A05 worker and verifier can consume an explicit `TTG_CREATIVE_PYTHON` runtime so clean target environments use their installed Pillow rather than an unrelated system interpreter.
- Prior to opening the ledger or executing any workload, the adapter rejects output-directory symlinks and verifies the canonical output remains inside Creative Studio's registered workspace.
- Added two regression checks proving an output symlink cannot redirect writes.
- Initial model-free Sergeant verdict was `REQUEST_CHANGES`, primarily for the missing `ci.yml` proof path; re-review is required on the updated exact head.

## Additional native Ptah D04 qualification — 2026-10-14

The Studio adapter now consumes the released `ptah-recipe-registry` crate to register and resolve a bounded in-memory D04 service observation using exact current Provider Revision, Instance and generation. A stale-generation lookup fails closed, and both jobs verify the D04 resolution path. This does **not** implement D04 persistent recipe execution, an enrolled production service, external network exposure or Ptah daemon discovery.
