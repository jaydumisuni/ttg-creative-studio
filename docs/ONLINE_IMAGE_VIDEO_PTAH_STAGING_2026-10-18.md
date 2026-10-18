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
