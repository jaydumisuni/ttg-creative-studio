# Creative Studio — Storytold + Vork donor intake (2026-11-23)

**Status:** PARTIAL TTG-NATIVE MOTION/LAYER INTEGRATION VERIFIED; FULL DONOR INTEROPERABILITY PENDING. Internal engineering acceleration; no replacement of the Studio app or of verified behavior. Ecosystem register: private `TTG-ecosystem/docs/DONOR_COHORT_STORYTOLD_VORK_2026-11-23.md`.

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
4. **3D — DEFERRED:** do not integrate Vork or alter the current working Blender adapter while other donors are being qualified. First finish native TTG-owned PhotoCraft/FilmCraft/EffectCraft/VectorCraft/material/texture capability slices and combined regressions. Then inventory any actual remaining Blender-dependent requirements and decide whether Vork adds enough value to justify an adapter; if yes, run same-scene quality/hardware/fallback evidence before adoption.
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

**Retirement:** record per-feature acceptance as evidence during implementation. **Defer the aggregate roadmap-closure measurement until after the selected donor-feature integrations and combined regressions are complete.** Only mark a phase `CLOSED` when its pre-existing exit contract and independent owner review pass. Keep Blender untouched and Vork deferred until that audit. Initial actual code candidate: [Studio PR #55](https://github.com/jaydumisuni/ttg-creative-studio/pull/55), TTG-native hold and Bézier motion curves; 11/11 targeted KRATOS tests and real frame replay passed, GUI and PR admission not yet proven.

## Native donor-integration qualification update — 2026-11-25

Two existing donor-informed Studio requirements are now integrated and verified together in the TTG-native engine, not by embedding donor executables. This supersedes the earlier blanket no-integration-proof status for only these native slices.

- Motion / P2 subset: hold and cubic-Bezier keyframes with stored-project replay and actual motion pixels, behavior referenced to EffectCraft.
- Layer canvas / P1 subset: Multiply and Screen with backdrop/source alpha, TTG layer properties and saved-project pixel replay, behavior referenced to PhotoCraft.
- Joint source: integration/storytold-motion-blend-20261125 at bca3f5d8d7d7dc82593456a8e93bcc98783c5ef9. The existing independent PR #55 and PR #56 remain intact.
- Exact changed-file Sergeant source review: APPROVE, zero required actions, using repository-relative paths.
- Actual KRATOS headless tests: 23 passes plus 34 subtests. ATHENA PyQt6 tests: 23 passes plus 34 subtests; offscreen GUI smoke and canvas wiring PASS; 29 Studio completion checks PASS; 25 real standalone video/timeline/export checks PASS. Two source-bound GitHub workflows passed.
- Private source-bound evidence: TTG-Creative-Studio/.workspace/evidence/donor-combined-20261125/DONOR_MOTION_BLEND_COMBINED_FREEZE_20261125.json, SHA-256 a47722665853d10c5fb819ac6caa330e1079ad2b0b6b3cb777287e759435c4bc.

Do not mark the full P1 or P2 phase CLOSED from this subset. Actual PhotoCraft layered PSD roundtrips, FilmCraft/EffectCraft donor interchange and paid ArtCraft production model outputs are not qualified. The pinned PhotoCraft CLI source documents info, convert and run, but no donor executable was found on KRATOS; layer blending is NOT PSD interoperability. Vork stays deferred, Blender unchanged, and source/release main retains existing owner authority.

## Native donor interchange wave — 2026-11-26

This extends the existing TTG Creative Studio app and native source project, not a separate set of editors. The motion easing and alpha-aware blend integration was already implemented and source-bound tested; **already documented — no duplicate implementation needed**.

| Donor | New native Studio interchange and exact supported subset | Not yet proven |
| --- | --- | --- |
| PhotoCraft | OpenRaster (.ora) import/export with actual RGBA layers, supported blend modes, order, opacity, visibility, original image preservation and pixel roundtrip | Full PSD/PSB, groups, masks, adjustments or editable vector/text parity |
| FilmCraft | OpenTimelineIO (.otio) independent clip tracks, real local media references, source trim/timing and native TTG metadata roundtrip | Advanced NLE trims, multi-clip track sequences, FCPXML/AAF, color pipeline and DSP equivalence |
| EffectCraft | Lottie 5.x editable basic shape and position/hold/cubic Bézier motion subset, including an attributed actual EffectCraft test fixture | Full Effects, AEP, masks, expressions, complex Lottie or complete AniCraft |
| MaterialCraft + TextureCraft | Imported real exported PNG PBR maps with hashes, channel and color-space identification, normal-Y conventions, and editable TTG asset references | .mcmat graph baking, full shader/UV integration and surface-quality certification |
| VectorCraft (DesignCraft overlap) | SVG solid rectangle, ellipse/circle, two-point connector primitives as editable native TTG layers | Rich SVG paths, typography, diagrams, complex effects, PDF/AI interchange |
| ArtCraft | Existing opt-in provider image/video workflow remains; no new model service invoked | Real ArtCraft model/API admission, cost agreement and unseen image quality acceptance |
| SoundCraft, LightCraft, AniCraft | Existing TTG sound markers, image ingestion and keyframes remain | Standalone DSP, RAW and full frame/vector animation equivalence |

All five new exact interchange subsets are available through existing Studio **File** and **Export** toolbar menus, the manual 'scripts/creative_cli.py' operations, and the existing Hunter-compatible 'src/ttg_creative_studio/cli.py' task catalog. Imports produce a new canonical TTG project, not a donor-managed replacement source. They refuse unsupported or potentially lossy structural mappings instead of silently flattening them. Original sources are preserved, outputs are create-only, and input/archive/file budgets apply. Vendor donor binaries and model weights are not installed or required for these native format implementations.

The included test file 'tests/fixtures/effectcraft_bouncing_ball.json' and its attribution came from EffectCraft at the previously pinned donor source revision, MIT OR Apache-2.0.

**Retirement discipline:** These are qualified implementation candidates for specific P1/P2/P4/P5 source-interchange requirements, not closure of full phases or complete direct donor runtime interoperability. Independent owner review, OS-specific GUI tests, CLI tests and real source-file interchange remain requirements. Vork intentionally deferred; Blender left unchanged.

**2026-11-26 source correction:** FilmCraft OTIO Audio tracks now map into Studio's existing `audio_markers` mix graph, preserving start/trim/duration/volume and rejecting unsupported private FilmCraft grade/DSP metadata. Imported OTIO still-image clips are time-bounded in the existing frame renderer; ordinary untagged Studio image layers are unchanged. Windows file identity validation accounts for valid short/long path aliases. All source changes remain in the same integration branch and shared editor/CLI workflow.


### 2026-11-26 — Nextwave: FilmCraft sequences and MaterialCraft swatches

This is a **source-bound extension to the existing native Studio interchange**, not a new product, new coordinator or a full donor-engine import.

- **FilmCraft P2:** OTIO Tracks containing multiple consecutive Clip/Gap objects now map to native Studio layers/real audio markers with authored start, duration, trim and sequence identity. Re-export regroups clips into the original track with actual gap timing. Still-image frames are displayed only within their authored clip windows and audio clips enter the incumbent MP4 mixer. Native video rendering, transitions, retimes, FilmCraft effects and nested Compositions retain their existing scope limits.
- **MaterialCraft/TextureCraft P5:** The existing verified, separately hashed PNG map channels now also create a bounded, reproducible fixed-light **material swatch** and one editable Studio image layer. The swatch samples normal, roughness, metallic, ambient occlusion, base-color, emissive and opacity channels with explicit OpenGL/DirectX normal-Y handling. This is a reference-rendered 2D preview, **not** a UV-mapped 3D shader, full material-graph bake or independent surface-fidelity certification.
- The same Studio File/Export workflow and manual/typed command routing remain in use; original donor files are untouched and exports are still create-only.
- Independent Tenfold Gen 1 Foreman lanes prepared these two code changes in *isolated* worker scopes from the exact Studio main ancestor. Tenfold worker stdout carried reviewed patch deltas; the integrated candidate is reviewed/tested in a separate Studio worktree. Existing Cookpit/Sergeant/other project services and timers are not changed.
- Stage retirement remains per existing owner roadmap. The added clip-sequence and fixed-light-swatch *subrequirements* may be considered in review; **neither P2 nor P5 as a whole is declared closed**. Blender untouched and Vork deferred.


### 2026-11-26 — SoundCraft audio envelope and EffectCraft/AniCraft opacity (Tenfold isolated wave)

**Native additive implementation:**
- **User-facing control:** Existing Studio Tools → Edit Audio Fades opens one bounded per-track dialog to adjust the real production FFmpeg envelope, preserving undo and existing editable audio markers; source-only JSON edits are no longer required.
- **SoundCraft P2 subset:** The existing Studio audio marker now accepts two optional, finite, source-relative durations, `fade_in` and `fade_out` (seconds). The production FFmpeg chain applies trimmed audio, volume, actual `afade` in/out, then timeline delay, before native mix. Fades are bounded (nonnegative, no overlap past clip duration), clips without fades retain original behavior. Native editable metadata survives the FilmCraft OTIO track exchange. A generated real PCM WAV uses FFT-free amplitude measurements on any workstation with FFmpeg installed; absent FFmpeg is not recorded as a real PCM proof.
- **EffectCraft/AniCraft P2 subset:** Lottie 5.x basic solid rectangle/ellipse tracks now exchange animated layer opacity as well as position using linear, hold and cubic-Bézier keys. Native shape rendering now honors the same transform.opacity as image and video layers, so saved-project frame sequences are replayable and genuine transparent/visible frame pixels can be compared. External effects, expressions, complex masks or complete AniCraft/EffectCraft runtime remain unsupported.
- Implementation used the existing qualified Tenfold Foreman and **two independent isolated construction workers**, without altering Cookpit project workers/timers or the existing Blender adapter. Source patches move through the same Studio edit/review/merge path.
- This advances *selected P2 feature implementations only*. It does **not** close SoundCraft DSP editing, complete animation/VFX parity, full FilmCraft postproduction, protected production signing or the whole P2 stage.


### 2026-11-26 — PhotoCraft neutral groups and VectorCraft multi-point connectors (Tenfold construction)

These are additional *native TTG Creative Studio* capabilities implemented by two independent Tenfold Gen 1 construction workers against one exact Studio ancestor. The existing editors, project schema, file operations, GUI menus and specialist CLI routing remain authoritative; no new worker service or donor binary is created.

- **PhotoCraft / OpenRaster P1 subset:** Bounded OpenRaster nested `<stack>` groups (up to four levels) with neutral compositing are imported as independently editable image layers. Every layer retains an ordered, named group identity in its native TTG project metadata. OpenRaster re-export reconstructs the original nested group tree and ordering, and actual pixel rendering matches the source. Group opacity, offsets, isolation, visibility, group blend, and grouped child Multiply/Screen remain unsupported because independently flattened layer compositing cannot prove their equivalence. Original PhotoCraft source archives remain unchanged. This is not PSD/PSB group, mask or adjustment-layer support.
- **VectorCraft / SVG P4 subset:** Bounded standard `<polyline>` elements with two to 128 local pixel-coordinate vertices, a solid hex-color stroke and bounded integral stroke width import as a real editable TTG `connector_line` layer. Multi-point connector lines re-export as SVG polylines; two-point connectors retain the previous `<line>` representation. Real Studio canvas pixels and SVG roundtrip match. Unsupported paths, transforms, fills, scripts, external resources, CSS, excessive point budgets and out-of-canvas coordinates remain explicit errors.
- New independent tests exercise genuine image/scene source import, saved-project replay, re-export/reimport, and malformed negative cases. The scope is two newly proven donor **subfeatures**, not entire P1/P4 exit, complete OpenRaster or full VectorCraft engine equivalence. Existing Blender, Vork deferral, Cookpit supervisors and other project workers are untouched.


### 2026-11-26 — Independent LightCraft and CADCraft parallel construction

New source-bound Studio adapters, built in two separate worktrees from the same Studio main ancestor and qualified by two parallel Tenfold Gen 1 isolated verification jobs. They extend the existing Studio editing workspace, manual commands and Hunter-compatible typed job entrypoint. No active Cookpit workers, timers, supervisor rotations, Blender code, existing donor branches, or Vork deferral are changed.

- **P1 LightCraft developed RAW intake:** The actual original camera RAW file is size/header screened and SHA-256-bound; the actual RGB/RGBA PNG is loaded, hashed, copied to a new Studio-local asset folder and opened as an editable image layer. The original RAW remains where it was. The optional develop-lightcraft-raw command invokes one explicitly selected, already installed LightCraft CLI using render and preserves byte receipts. Import LightCraft developed RAW is available in Studio File. No RAW demosaic, camera color accuracy, licensed external binary identity, XMP editing or general camera coverage is certified solely by synthetic fixture tests. An existing LightCraft executable is not silently downloaded.
- **P4 CADCraft bounded DXF:** ASCII R12/R2000 DXF import/export supports simple LINE, straight LWPOLYLINE and unfilled CIRCLE, explicit unit agreement, true-color or common ACI colors, layer names and exact y-up CAD to y-down Studio conversion. Saved TTG connectors/circle primitives remain editable, and imported files reopen with pixel replay. Unknown sections/entities, 3D/elevated geometry, CAD hatches, spline/bulge, blocks, DWG and engineering netlists are rejected. Studio File / Export menus and CLI expose the same bounded typed contract. This is 2D presentation exchange only, not CADCraft's complete drafting system or Hardware Studio's electrical/mechanical design authority.

The two modules own no separate app, resource worker, installed model, hardware operation or production release key. Exact source versions, Tenfold run evidence, platform-specific GUI and CLI checks, Sergeant review and GitHub CI must be frozen before deciding any subrequirement retirement. Do not mark P1 or P4 as whole-stage closed.


### 2026-11-26 — Two follow-on source-quality gaps: DNG structure and CAD ARC

Existing exact Studio source is extended in two independent, Tenfold Gen 1
isolated workstreams, without touching active Cookpit timers, application
services, installed binaries or alternate worktrees.

- **LightCraft DNG integrity:** the earlier DNG intake validated only a
  TIFF four-byte signature; it now also validates endian/magic, bounded first
  TIFF IFD, presence/type/value of DNGVersion tag 50706, dimension tags,
  duplicate-tag ambiguity, source bounds and reasonable image dimensions.
  An unsupported/truncated TIFF is rejected before producing a new Studio
  asset. Structural evidence is attached to native project provenance.
  **A synthetic TIFF with correct tags remains synthetic**, and the check is
  expressly not validation of raw pixels, demosaic/colour accuracy, a real
  camera sample or a trusted LightCraft executable.
- **CADCraft 2D ARC:** the previously missing DXF ARC entity now maps to
  an editable Studio connector line with a bounded 5-degree-or-finer display
  tessellation. The original curve centre, radius, start/end angles, layer
  and color are retained; unchanged geometry reexports as a true DXF ARC
  with 17-significant-digit numeric fidelity. Wraparound angles, original
  geometry replay, out-of-bounds geometry, 3D arcs, transforms and edited
  sampled geometry have explicit regression/negative checks.
  Tessellation is a presentation primitive, not exact manufacturing BREP
  or clearance tolerance. Modified arc point geometry requires explicit
  conversion rather than silent loss of the analytic curve.

Existing GUI DXF File/Export and LightCraft RAW intake, manual CLI and
typed specialist-job APIs automatically use the corrected underlying
source-bound modules; no duplicate menus or reimplementation is needed.
The two new scripts run on both GitHub Linux and Windows runners.

**Release boundaries:** Complete native subsets only, not P1/P4 phase
exits, real RAW development, production/physical acceptance or independent
signature gates. Keep Blender unchanged and Vork deferred.
