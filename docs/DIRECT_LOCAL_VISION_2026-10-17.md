# Creative Studio direct local image understanding — 17 October 2026

## Product boundary

Creative Studio's native editor and ComfyUI generation do not depend on an assistant, model manager, or cloud service. Hunter integration is deferred until the standalone editor is proven and accepted. Stable Diffusion 1.5 supports generation and inpainting, not vision-language interpretation.

The Visual Inspector measures actual image pixels offline. For semantic interpretation, Creative Studio now connects DIRECTLY to a user-owned local OpenAI-compatible multimodal inference server, not any model-manager API.

It uses GET /v1/models for model discovery and POST /v1/chat/completions with a JPEG image_url data payload and typed user question. Only local loopback HTTP endpoints are accepted. A Discover Installed Vision Models button uses a Qt worker thread so the editor remains responsive. Server redirects, remote hosts, fake model names, oversized images and unusable responses fail closed. When a model is unavailable the offline pixel evidence remains usable, and no object recognition is claimed.

The model's output is marked unreviewed interpretation. It cannot automatically execute edits: users must approve predefined native, undoable effects. No Ptah or Hunter service is required.

## Optional owned model on ATHENA

A practical candidate for its RTX 4070 is the Q4_K_M variant of ggml-org Qwen2.5-VL-3B-Instruct-GGUF with the MATCHING vision projector, under Apache-2.0 licensing:
https://huggingface.co/ggml-org/Qwen2.5-VL-3B-Instruct-GGUF

An image-capable llama.cpp server can expose the weights via its own HTTP interface without a separate model manager. Obtain binary and model from official repositories, verify license/provenance, and install only in an approved owner-controlled location. Studio never silently downloads checkpoints. Avoid duplicate multi-GB weights and check free storage first.

Interactive Windows startup, with paths changed to actual approved locations:

    powershell -NoProfile -File scripts/start_studio_vision_windows.ps1 -ServerExecutable "C:\approved\llama-server.exe" -Checkpoint "C:\approved\vision-model.gguf" -VisionProjector "C:\approved\mmproj.gguf"

The launcher validates all three files, SHA-256 hashes the model and projector, binds only 127.0.0.1:8000 and remains in the foreground. Stop it with Ctrl+C. It never creates a scheduled task, cloud service or Hunter dependency. Studio's Visual Inspector can then discover the installed model without manually entering its ID.

An approved local inference environment can be qualified using this command after creating the target proof directory in the approved Studio workspace:

    python -B scripts/qualify_studio_vision.py --model creative-vision-local --output ".workspace\proofs\vision-acceptance.json"

It stores source hashes, actual local responses, elapsed time and simple measured benchmark outcomes. The cases cover color/spatial relationships, large lettering and absence of people. This is a small baseline; reliable general object detection, OCR, segmentation and image quality require broader evaluation.

## Test and release status

The deterministic image-inspection fallback, local multimodal image wire format, actual selected-image transmission, asynchronous Qt model discovery, offline fallback, redirect protections and reversible user-approved edits are exercised in scripts/test_visual_understanding.py. The test receiver simulates HTTP responses and DOES NOT demonstrate real model inference. Windows and Linux standalone Studio CI must pass at the exact pushed commit.

The previously verified Stable Diffusion model on ATHENA is for generation and editing; it does not close the local multimodal understanding acceptance gate. A real vision checkpoint, actual RTX inference and visual acceptance are still required before claiming complete semantic-image parity. Production Authenticode signing and authorized ATHENA Studio installation are separate release requirements.
