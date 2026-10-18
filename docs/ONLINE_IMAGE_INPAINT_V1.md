# Creative Studio Online Mask Inpainting V1

**Standalone Creative Studio, no Hunter/Ptah service and no local checkpoint.**

Creative Studio already supports non-destructive mask painting and ComfyUI
local inpainting when an eligible checkpoint is installed. This work adds
**optional online masked inpainting** using the official
[Replicate FLUX Fill Pro](https://replicate.com/black-forest-labs/flux-fill-pro)
model as an additional paid operation.

## Usage

Open **Tools → Generate Online Image**, select **Inpaint with mask · FLUX
Fill Pro** and provide a text instruction, the source image and a mask.
For the mask, **white pixels indicate the area to edit; black pixels are
preserved**. Source and mask should have the same pixel dimensions.

Source and mask may be separate public HTTPS URLs, or explicitly chosen
local PNG/JPEG/WebP files under 235 KB each. Local files are encoded in
memory as small validated data URLs for the external provider request.
For larger private sources, Studio does not automatically upload files or
expose local project paths: prepare a user-approved public URL instead.
If both local inputs are used, the app verifies matching dimensions before
initiating a paid call. If either reference is remote, the provider validates
its dimensions; mismatches may fail after submission.

Every image request still requires:
1. Private `REPLICATE_API_TOKEN` configured outside the repository.
2. Operator setting `TTG_STUDIO_ENABLE_PAID_IMAGE=1`.
3. A new per-request paid consent checkbox and GUI confirmation.

Image consent cannot authorize video charges. There is no guaranteed
spend ceiling; review the live provider price first. Image and mask bytes
are sent to Replicate only after explicit confirmation, not during file
selection, mask painting, previews or unit tests.

Studio submits an asynchronous official-model prediction, checks status,
then can download the verified PNG into the current editable project
and retain it through save/reopen. Actual neural inference is carried
out by Replicate, not on KRATOS. The optional FreeVideo and offline
image checkpoints remain for GT502/Spark later.

## Test scope

`python -B scripts/test_online_inpainting.py` exercises the inpainting
request schema, mask input requirements, invalid/mismatched inputs,
bounded local PNG serialization, URL constraints, exact model selection,
separate consent, and GUI local-source/mask selection using synthetic
HTTP replies. It makes no remote calls and spends no money.

A genuine production inpainting acceptance still requires operator
credentials, external billing permission and an explicitly authorized
live image/mask test. The current passing mock tests do **not** prove
that the remote model produced a real image.

No installed checkpoint, token, media asset or source data is committed.
