# Creative Studio Online Image + Video / Ptah Workspace QA

Creative Studio remains the independent source/product owner. Ptah is a workspace, not a transport or model chooser; Oracle transports execution to KRATOS. No Hunter integration is enabled.

## Features
* Native video editor: real clip import, frame inspection, audio and timeline, save/reopen, MP4 export.
* Online video: external Replicate hosted inference with job submission, status, cancellation and bounded MP4 import.
* Native image editor: effects, adjustments, optional local ComfyUI if installed.
* New online images: official Replicate FLUX Schnell prompt-to-image, and FLUX Kontext Pro instruction-driven image editing/background changes on a public HTTPS source. Images are validated with Pillow before editable Studio-layer import. Precise mask inpainting is available through optional ComfyUI only, not represented as qualified online.
* No local model weights installed onto KRATOS. Optional 92 GiB FreeVideo local weights are deferred until GT502/Spark admission.

## Paid activation
REPLICATE_API_TOKEN is a private, operator-provided credential. The user must explicitly enable TTG_STUDIO_ENABLE_PAID_IMAGE=1 and/or TTG_STUDIO_ENABLE_PAID_VIDEO=1 in an authorized environment. Each billable job requires separately passed paid_approval and an additional GUI confirmation. Do not put credentials in a project, Ptah workspace or GitHub source. AI assistants are not authorized to supply billing consent themselves. Current prices must be confirmed on model pages.

Model API references:
https://replicate.com/black-forest-labs/flux-schnell/api/schema
https://replicate.com/black-forest-labs/flux-kontext-pro/api/schema
https://replicate.com/bytedance/seedance-1-pro-fast

## Actual KRATOS Ptah staging area
/home/kratos/projects/Ptah-space/.workspace/workspaces/ttg-creative-studio-qa-20261018

Studio source checkout:
/home/kratos/projects/TTG-Creative-Studio/.workspace/worktrees/studio-online-image-ptah-20261018

The Ptah workspace has a non-authoritative STAGING_MANIFEST.json, scratch and proof/staging-test-results.json. Test execution uses this Ptah workspace as cwd and points PYTHONPATH at the exact Studio source worktree. No duplicate model files, secrets, app binaries or Studio project source copies are stored in Ptah. Tests were run on KRATOS through Oracle, with zero billable calls.

CRITICAL: A test directory is not itself Ptah A06 authorization, E07 resident production transfer, a Supervisor acceptance, production installer signing or owner visual acceptance. These remain separate independently gated milestones. Nothing in this work changes the Ptah core, Hunter, Oracle permissions or production secrets.

## Qualification
Tier 1 now: source/test GUI and provider protocol checks within Ptah staging, plus hosted Windows/Linux CI, using mock HTTP provider responses (not real generation). Tier 2 after external account activation: actual intentionally approved paid generation and image/video import quality review. Tier 3 after GT502/Spark arrives: opt-in local model installation and hardware proof, no 92 GiB model on KRATOS. Tier 4 before release: Ptah-authorized operational workspace (if requested), physical target-host GUI test, signed release and owner review. Never mark later tiers closed from Tier 1 evidence.


## Follow-on acceptance after the #28 merge

The merged image provider was retained without introducing a competing
second implementation. Image requests now have a **distinct approval token**
from video requests. Even if video billing is admitted, that cannot be used
as the per-request approval for paid image generation. A returned cloud PNG
is saved inside the **current saved editable Studio project** by default,
then imported as a real image layer. GUI/save/reopen are covered by an
independent simulated-provider round-trip test.

One more direct Studio executable probe ran successfully in the actual
Ptah checkout's Patrol-approved scratch directory:

    /home/kratos/projects/Ptah-space/.workspace/scratch/creative-studio-main-20261018

It executed 12 physical image/video job and artifact checks: observable
image metadata, image resizing, native image enhancement, cloud capability
discovery, timestamped storyboard, actual native Studio motion-project
MP4 rendering, cloud-billing refusal for image and video and independent
SHA-256 evidence. Evidence is
`studio-ptah-workspace-proof.json` in that directory, with initial
manifest SHA-256:
`89e41ca85103e61f1a37f3aa0b48cb9f7345eeb6c440d5b41134248033c199be`.

This is **real Studio process execution from a Ptah filesystem workspace
directory**, but **NOT a production-enrolled Ptah Node or A05/A06 grant**.
The earlier PR #28 staging evidence is retained; these observations do
not convert either staging directory into production authority.

Windows source-level recovery regression now compares the *canonical*
path of a snapshot's original file, so Windows short-name/long-name
aliases do not falsely reject a verified recovery. It still verifies
that unsaved edits survived and the original project remained unchanged.

Stage schedule: Tier 1 source/workspace and Windows/Linux image/video
tests are now executable. Tier 2 genuine billed cloud-model generation
must be explicitly authorized with a provider token. Tier 3 local model
downloads await GT502/Spark. Tier 4 separately authorized Ptah resident
workspace and physical signed desktop acceptance remain gated.
