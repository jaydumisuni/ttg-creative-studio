# Creative Studio production admission — 15 October 2026

Development PRs #11 and #12 are merged into main. Windows/Linux release
candidate builds previously passed. They are **unsigned engineering builds**,
not production releases. Do not conflate test-only AI responses with
installed diffusion inference.

## Physical ATHENA evidence (read-only Oracle inspection)

- ATHENA: NVIDIA RTX 4070 Laptop GPU, around 48 GiB system RAM.
- D: free space observed around 25.8 GiB; verify available space before
  model, Torch, ComfyUI and release downloads.
- Creative Studio project directory: D:\projects\TTG-Creative-Studio.
  Oracle rejected project execution with PATH_OUTSIDE_ALLOWED_ROOTS.
  Request that *exact root* through the normal operator permission procedure.
  Do NOT use another root merely to evade the denied access control.
- ComfyUI 127.0.0.1:8188 not reachable; no image diffusion checkpoint
  or usable PyTorch/diffusers inference runtime observed. The cached
  faster-whisper model is a speech model, not image generation.
- No approved valid code-signing identity with accessible private key,
  Windows SDK signtool executable, or protected Studio signing configuration
  observed. Oracle has no Creative Studio release provider configured.
- No installed Creative Studio entry seen in standard Windows uninstall
  registration keys. Physical Windows installation is still unqualified.

## New automated gates

- scripts/test_installer_windows.ps1: Windows disposable-runner install of
  the real Inno Setup package, installed GUI executable self-check, then
  uninstallation and absence check. Does not install on ATHENA.
- scripts/qualify_local_ai.py: refuses real inference acceptance without
  a ComfyUI service, advertised installed checkpoint and substantial local
  checkpoint file. The explicit opt-in --infer run obtains a real 512x512 PNG,
  then writes image bytes, SHA256, timings and proof JSON. Readiness alone is
  not generative quality acceptance.
- scripts/test_production_preflight.py: negative tests for missing/fake
  models, redirected prompts/images and installer CI scope.
- src/ttg_image_lab.py: refuses redirects away from loopback, which could
  otherwise leak uploaded product images or private prompts.

## Model readiness procedure

Obtain ComfyUI from its authorized upstream, install with a qualified
NVIDIA/PyTorch configuration inside an approved Studio workspace, and install
an image checkpoint after checking its license and available storage.

A public starter checkpoint with documented checksum is:
https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/blob/main/v1-5-pruned-emaonly.safetensors
File size: 4.27 GB. Published SHA256:
6ce0161689b3853acaa03779ec93eafe75a02f4ced659bee03f50797806fa2fa
Model card license: creativeml-openrail-m; check licensing for intended use.
No checkpoint is redistributed by Creative Studio.

Inside the *approved* project checkout, create the proof directory and run,
after the real ComfyUI service is running:

    python -B scripts/qualify_local_ai.py --checkpoint-dir
      "C:\ComfyUI\models\checkpoints" --checkpoint
      "v1-5-pruned-emaonly.safetensors" --infer
      ".workspace\proofs\real-image-001.png" --verify-public-digest

Use that command on one line with actual installed paths. It refuses to
overwrite an existing receipt. A real result contains a PNG and proof JSON
with checkpoint validation, image SHA256, dimensions and inference duration.
Visually assess real images and inpainting; a network fixture is not proof
of model execution.

## Signing, UI and release boundaries

Production Authenticode signing requires a legitimate business-issued code
signing certificate, protected private key, signing tools, signature chain
validation and explicit release approval. The existing signing gate fails
closed when the identity is absent. Never commit keys or passwords.

Windows CI installation is a disposable-runner qualification, NOT ATHENA
physical GUI verification. On ATHENA verify real native application launch,
editing, imports, save/reopen, undo/redo, installer removal, resource load
and security prompts only after the workspace is authorized.

Final visual/owner approval and signed public release are separate decisions.
No Ptah, Hunter, Oracle policy, live PKI or production routing changes are
authorized by this document.
