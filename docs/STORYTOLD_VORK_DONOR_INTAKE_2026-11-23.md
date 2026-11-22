# Creative Studio — Storytold + Vork donor intake (2026-11-23)

**Status:** PLANNED / SOURCE-REVIEWED / NO INTEGRATION PROOF. Internal engineering acceleration; no replacement of the Studio app or of verified behavior. Ecosystem register: private `TTG-ecosystem/docs/DONOR_COHORT_STORYTOLD_VORK_2026-11-23.md`.

## Protect the existing implementation

Studio already has PyQt layered canvas, `.ttgstudio.json` source/project model, image jobs, Campaign Designer, editable scene compilation, deterministic verification, native 3D mesh authoring, optional Blender subprocess, timeline, FFmpeg-gated export and optional image/video provider paths. Preserve existing `creative_execute`, `studio_produce`, ProductionDirector, `run_image_job`, `run_video_job` and output receipts. Do not silently promote generative inference, semantic vision or Hunter dispatch to production. The KRATOS primary checkout has uncommitted local edits; **do not reset, overwrite or rebase that workspace**.

## Donor-to-donor assignment — not seven new editors

| Specialized operation | First donor | Companion / overlap | Intended Studio seam |
| --- | --- | --- | --- |
| Layered PSD + pixel/brush editing | [PhotoCraft](https://github.com/storytold/photocraft) | LightCraft is RAW developer/library, **not** a second layers engine | Import/export or wrapped headless CLI/MCP; compare real PSD roundtrips to Studio project/layers |
| Nonlinear editorial timeline, multicam, color, audio | [FilmCraft](https://github.com/storytold/filmcraft) | EffectCraft is composition/VFX, not final NLE | OTIO/AAF/FCP7 XML or explicit video/clip interchange; Studio retains canonical project |
| Motion graphics, keyframes, Lottie and compositing | [EffectCraft](https://github.com/storytold/effectcraft) | AniCraft owns 2D frame/vector animation | Composition export and rendered alpha/final passes; no duplicate final timeline |
| Programmatic 3D scene, materials, cameras, GPU simulation | [Vork](https://github.com/voyager-so/vork) | Existing Studio Blender adapter remains; EffectCraft handles layered composites | New **optional** Vork render adapter beneath Studio's Director; source-bound scene schema and pixel/MP4 artifact receipts |
| Procedural PBR graph → paint/bake surfaces | [MaterialCraft](https://github.com/storytold/materialcraft) + [TextureCraft](https://github.com/storytold/texturecraft) | Their native `.mcmat` workflow is documented; no Vork export compatibility proven | Asset/texture import with material metadata; explicit glTF/GLB texture and PBR mapping qualification |
| AI-assisted staged assets / provider routing | [ArtCraft](https://github.com/storytold/artcraft) | PhotoCraft edits raster; Vork is deterministic 3D, not diffusion inference | Separately consented optional specialist; actual generated pixels, cost, model provenance, no fabricated local inference |
| Vector, layouts, sound, RAW | VectorCraft / DesignCraft / SoundCraft / LightCraft | Existing Studio/FFmpeg/timeline can already cover parts | Only when fixture proves missing operations and a stable, reversible interchange exists |

## Source anchors (observed 2026-11-23; pin exact reviewed dependency before implementation)

- PhotoCraft `ad51efbcb1a5711ef6975b113c44962817bb353b`; FilmCraft `2a4c3eada1797ed96ed67c90c1ed2969c6b29eae`.
- EffectCraft `7e2d0256209974ffb92a29d8bdb6f2a49078f51f`; Vork `bc228cba5b0b3554ef97b50954bdd8f9a0ad0256`.
- ArtCraft `de571bb2f8351ade6c742d41caea81f11f595801`; MaterialCraft `4ff5af9af7371613ee37b186e03caf49ee6dbd88`; TextureCraft `019fe97395be45ad571a9a82359dabc56658d73e`.
- Storytold applications inspected generally declare `MIT OR Apache-2.0` (verify individual packages/assets); Vork is source-available under a **different preview licence** allowing own-use modification and restricting modified distribution/hosted service. `artcraft-services` has separate licensing and must not be assumed permissive.
- Vork's `192-frame/1080p/97s/NVIDIA L4` million-birds figure is a developer measurement; Blender `13–18 minutes` is *projected*, not a measured equal-quality baseline. Vork needs compatible ray-query Vulkan/Metal; KRATOS GPU is not automatically qualified. Native execution only; no Docker assumption.

## Qualification order

1. **Read-only inventory:** exact current Studio head/dirty worktrees, current feature gates, donor API/CLI schemas, file formats, assets/licenses, system resources; record donor commits.
2. **Photo:** one licensed PSD with text/mask/effect layers → PhotoCraft → Studio or canonical interchange → reopen, compare layer semantics/rendered pixels/hash; preserve originals. Reject silent flattening.
3. **Video + VFX:** identical short audio/video fixture through FilmCraft/EffectCraft and Studio; compare timestamps, decoded frame/audio fidelity, roundtrip, failure signals and measured CPU/memory.
4. **3D:** translate one bounded, deterministic Studio scene to Vork JSON or SDK, compare against existing Blender reference with matching geometry/camera/light/samples *and* inspect both images. Explicitly report quality/performance differences and hardware failures.
5. **Material:** `.mcmat` → material bake/mesh import → Studio surface reference; verify UV/normal/roughness/colorspace metadata and undoable editable Studio asset references.
6. **Review:** independent Sergeant/Patrol/Studio owner acceptance under registered roots; only then add an optional capability entry with tool contract, pinned hashes and rollback. Existing paths stay default until proven.

**Unchanged gates:** paid AI consent, actual semantic visual acceptance, Hunter→Studio real handoff, physical installer/signing and release decision all remain separate. **No integration or performance win is claimed by this document.**

## Existing roadmap stage coverage and retirement (2026-11-23)

See [Studio's phase definitions](ROADMAP.md) and the private ecosystem `docs/STORYTOLD_VORK_ROADMAP_CLOSURE_MATRIX_2026-11-23.md`. Donor admission closes **requirements**, not phases by declaration:

| Studio phase/gate | Donor coverage candidate | What still controls the whole exit |
| --- | --- | --- |
| **P0 source/packs** | Craft packaging ideas only | Clean installer/source/optional asset pack and physical release checks; no direct closure |
| **P1 editor** | PhotoCraft PSD/layer/masks, LightCraft RAW, VectorCraft | Existing project/undo/render correctness retained; new layer/PSD fidelity and honest unsupported behavior; don't redo native source model |
| **P2 motion** | FilmCraft timeline/audio, EffectCraft VFX, AniCraft animation, SoundCraft audio | Real keyframe/track/preview/FFmpeg MP4 source fidelity, A/V sync, exact replay and failure tests |
| **P3 packs** | Candidate optional donor engines/assets | Versioned optional pack install/uninstall/rollback, offline/no-forced-weight behavior, clean-clone receipts; donor source is not a pack manager |
| **P4 diagrams** | VectorCraft lines/symbols, CADCraft drafting exchange | Snap, connector/callout/measurement/PCB-style *presentation* export and editable Studio project; not Hardware Studio engineering authority |
| **P5 cinematic 3D** | Vork renders/compute; MaterialCraft+TextureCraft surfaces; EffectCraft composite; FilmCraft+SoundCraft final | Authored 3D text, bevel, neon, camera, particles, service cards, sound markers, final MP4, editable/replayable scene, actual matched-quality GPU/fallback proof. Keep optional Blender for gaps not proven replaced |
| **P6 Hunter** | CLI/MCP/typed interface patterns and Vork sessions | Actual admitted Hunter→Studio job/lease/file custody/authorization/fence, result/undo/replay and independent review; no direct donor shell authority |
| **G6.3/G6.6 image quality** | ArtCraft provider/asset workflow only | Consented real generated images and ten independent unseen photographic acceptances, separately from basic image editing |
| **G7 visual semantics** | Donors may edit defects, not certify independent understanding | A real semantic observer and bounded correction loop; preserve already proven G7.1 text/pixel source requirements |
| **G0–G5 final release** | No direct donor closure | Existing installer, physical UI, signing and owner release gates remain independent |

**Retirement:** only mark a phase `CLOSED` when all its own mandatory outputs pass exact-head regressions, fixture+negative case, Studio project replay and appropriate independent/owner review; update Studio roadmap + progress. After qualifying a subfeature, mark `PARTIAL` with remaining items, not a percentage. **All new donor integrations are currently CANDIDATE.**
