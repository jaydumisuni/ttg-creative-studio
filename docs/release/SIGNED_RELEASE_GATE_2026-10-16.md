# TTG Creative Studio production signing and AI evidence

This document distinguishes **engineering code** from a **legitimate signed release**.

## Signed build authority

The `studio-production-signing.yml` workflow runs **only when manually
dispatched on the `main` branch**, with the exact 40-character current
commit SHA supplied as `approved_sha`. It declares the GitHub environment
`production-signing` for independent approval and secret scoping.

The protected release environment must have these secrets, provided
through the approved GitHub secret-management interface (never committed):

- `TTG_STUDIO_SIGNING_PFX_B64`: base64-encoded genuine code-signing PFX,
  with a valid trusted certificate and accessible private key.
- `TTG_STUDIO_SIGNING_PASSWORD`: the PFX password.
- `TTG_STUDIO_EXPECTED_SIGNER_THUMBPRINT`: 40-character pinned SHA-1
  thumbprint of the expected legitimate certificate.

The workflow rebuilds the approved main commit, executes native GUI
installation tests, signs the Inno Setup executable, verifies Windows
Authenticode trust and exact certificate identity, requires a timestamp,
and verifies the final artifact's SHA-256 custody manifest. PFX material
is transient on the GitHub runner and is removed after signing.

**No certificate or protected secrets were available during this source
qualification.** Do not describe the unsigned CI installer as production
signed. A private PFX is not to be pasted into ChatGPT.

## Actual image-generation evidence

`scripts/qualify_local_ai.py` requires a reachable **loopback ComfyUI**
server that advertises a real installed checkpoint, a substantial matching
local checkpoint file, and a successful opt-in 512×512 inference run.

Output PNG and `.proof.json` are exclusively created, fsynced and
rolled back if publication fails. An existing image or proof is never
overwritten or deleted. Tests that mock the ComfyUI HTTP interface
are **interface tests**, not proof of a GPU-backed generation.

On ATHENA, perform model qualification only after the normal Oracle/Patrol
admission of the **actual** Creative Studio workspace. The observed
`PATH_OUTSIDE_ALLOWED_ROOTS` error remains a machine transport restriction;
do not bypass it by moving production work into a different project.

## Scope and current limitations

- Windows/Linux release-candidate builds and disposable Windows GUI
  install/launch/uninstall tests have passed on GitHub Actions.
- No public Creative Studio GitHub release is published.
- Signed-release workflow remains **blocked** without a legitimate certificate
  and configured environment secrets.
- Real ComfyUI model-backed output on ATHENA is **unproven**.
- Physical ATHENA application installation and user acceptance are **unproven**.
- Owner visual and final commercial release authorization remain distinct
  from code review and automated CI qualification.

Do not mark these production gates closed until their actual artifacts,
physical machine receipts and owner approval have been verified.
