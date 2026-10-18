# Creative Studio — Image + Video in the Ptah Workspace
18 October 2026 · Standalone Creative Studio · KRATOS first

## What's ready

Creative Studio owns both native editors. The image editor already supports
offline enhancement, masks, effects, and local ComfyUI adapter (conditional
on a real checkpoint). The video editor supports real imported footage, layer
composition, timeline scrubbing, trim, audio, and native MP4 rendering.

The **online-first, model-weight-free layer** supports:

| Operation | External inference | Actual local model required? |
|---|---|---|
| Cloud image generation | Replicate FLUX Schnell | No |
| Cloud image prompt-based editing | Replicate FLUX Kontext Pro | No |
| Cloud video generation | Replicate Seedance provider | No |
| Image enhancement, masks, local retouching | Creative Studio native/Pillow | No |
| Video inspection, composing, MP4 export | Creative Studio FFmpeg | No |
| Offline ComfyUI image generation | Optional local checkpoint | Yes, when enabled |
| Offline FreeVideo AI video generation | Optional future GT502/Spark | Yes, only when enabled |

**Hunter is not connected.** Ptah supplies an optional workspace only; it
does not replace Oracle as transport, authorize billing, provide creative
decisions, or execute GPU inference without an admitted compute provider.

## Actual KRATOS workspace evidence

The Studio executable job CLI was launched with the working directory:

    /home/kratos/projects/Ptah-space/.workspace/scratch/creative-studio-20261018

The job suite actually created and independently checked an enhanced PNG,
resized PNG, editable .ttgstudio project, timestamped storyboard and a
newly rendered MP4. It tested an image/video capability report and confirmed
that a missing cloud billing authorization blocks both generation routes.
All input and output receipts, SHA256 digests and the manifest were written
inside that Ptah scratch directory. **12/12 physical workspace checks PASS.**

Evidence: studio-ptah-workspace-proof.json in that directory; manifest SHA256
f33be81c05ce7342286072ed0e597d1fe8dc7ca21ee6efddca5a5c475921e7b1
(at initial qualification).

**Qualification boundary:** this proves Creative Studio jobs run from a
Patrol-authorized Ptah workspace directory. It is not authenticated Ptah
production Node/Control admission, A05 production service routing, a
verified paid cloud inference result or physical ATHENA GUI acceptance.
Existing Ptah adapter PRs #8/#9 have separately qualified embedded A04/A05/
A06/A07 operations, but remain unmerged and unadmitted for production.
Never infer permission to merge or launch those production services from
this directory-level test.

When an operator enrolls a persistent production Ptah Workspace and its
authorized Creative Studio specialist execution, use a separate admitted
Workspace root and durable A07 artifacts rather than treating the scratch
test directory as that production service.

## Online setup — no model download on KRATOS

Install only the lightweight Studio application plus its already existing
image/video editing dependencies. A provider API token is optional and should
be injected **at runtime through an approved secret manager**, not saved in
Studio projects, repositories, workspace receipts or screenshots.

Replicate account/model information:
- https://replicate.com/black-forest-labs/flux-schnell
- https://replicate.com/black-forest-labs/flux-kontext-pro
- https://replicate.com/bytedance/seedance-1-pro-fast
- https://replicate.com/docs/topics/predictions/create-a-prediction

For the first real *image* paid test, the operator must explicitly supply
REPLICATE_API_TOKEN, enable TTG_STUDIO_ENABLE_PAID_IMAGE=1 in an authorized
session and approve **that specific request** in the Studio dialog.
The provider computes the result remotely. Cloud editing uses an explicitly
supplied **public HTTPS source image URL**; the app does not quietly upload
private local files. Its verified PNG is imported into an editable Studio
image layer.

For *video*, the equivalent gate is TTG_STUDIO_ENABLE_PAID_VIDEO=1,
plus the private token and per-request UI consent. The cloud MP4 download is
bounded and must pass the existing Studio media probe before import.

Neither model price nor provider quota is controlled by a ChatGPT
subscription. Checking status/download is not a new generation request;
starting another job may incur a new charge.

Local checkpoint downloads are deliberately excluded. On future GT502 or
Spark admission, provide a separate disk quota, verify the actual license,
obtain the required FreeVideo model files (~92 GiB inspected for its full
manifest) and qualify real inference before enabling local generation.

## Testing schedule and authority

**Already performed now on KRATOS:**
- 32/32 cloud image protocol/security checks, synthetic HTTP, NO live billing.
- 32/32 cloud video protocol/security checks, synthetic HTTP, NO live billing.
- 12/12 shared AI video-tool checks and 24/24 real standalone-video checks.
- 29/29 Image Lab completion checks and 60/60 Campaign Designer checks.
- Complete Creative Studio release engineering review gate PASS.
- 12/12 real filesystem/jobs in authorized Ptah scratch workspace.

**Next acceptance tests after an approved provider account is available:**
- Operator approves ONE inexpensive genuine cloud image request.
- Import resulting verified PNG into an editable project in the admitted
  Ptah workspace, render and independently checksum it.
- Operator separately approves ONE genuine cloud video request.
- Check prediction until succeeded, fetch actual MP4 into the admitted
  workspace, inspect real streams/frame content, edit timeline and export.
- Preserve billed provider ID, timestamp, destination digest, byte count,
  and whether human approves the visual output; no claimed result until run.

**GT502 or Spark hardware stage, later:** optional local diffusion
and FreeVideo model installation, licensed-weight checks, VRAM/storage
qualification and *offline* generation quality assessment.

**Physical app release stage:** when the intended workstation/execution root
is Oracle-admitted, install the exact signed candidate and test the full
interactive GUI, assets, update/rollback and source provenance. That is
not established by this workspace smoke or hosted CI alone.
