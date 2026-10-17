# TTG Creative Studio — Visual Inspector V1 (17 October 2026)

## Why this exists
This is a Creative Studio feature, **not a new Ptah backend**. Ptah's reverse-engineering work decompiles executable and firmware formats, not images. Its useful architectural patterns are bounded evidence capture, verifiable source hashes, separation between measured facts and inferred claims, and explicit qualification before approving an action.

Creative Studio's earlier \`ttg_image_intelligence.py\` declared "Vision Encoder", "Layout Reasoner" and "Edit Planner" but returned \`stubbed_native_architecture\` without examining the pixels. This update replaces that behavior for actual image analysis.

## What works offline
Open Studio, select a raster image layer, and choose **Tools → Visual Inspector · Analyze Image**. The inspector reads the actual asset and computes:

- Pixel dimensions, orientation, transparent alpha, SHA-256 of original bytes
- Luminance average and standard deviation from a bounded thumbnail
- Measured edge energy (a rough detail signal, **not** true resolution/sharpness classification)
- Dominant sampled colors and approximate shares

The deterministic suggestion engine can propose safe native brightness, contrast and sharpening effects when measured conditions warrant them. **Nothing is applied automatically.** Select a suggestion, click **Apply Selected Edit**, and Studio records an undoable effect on that exact unlocked image layer. It refuses unknown effects, changed assets and changed/locked targets. For non-image selected layers it renders the current canvas to a temporary local snapshot for analysis, with suggestions non-applicable.

**Important:** Color histograms and edges do not identify people, objects, logos or textual content. Do not label pixel measurements as semantic vision.

## Optional real local vision-model interpretation
The dialog now accepts an explicitly configured image-capable local model ID and an OpenAI-compatible server endpoint, default http://127.0.0.1:8000. Creative Studio obtains advertised model IDs from /v1/models and sends the real selected image as a typed JPEG image_url data payload to /v1/chat/completions. This direct local interface requires no Hunter, model manager or cloud service. An owned llama.cpp-style vision server and an installed multimodal checkpoint can provide the model. Replies are marked review-required, and no edit is automatically executed.

With no local vision checkpoint or a service failure, Studio continues with actual pixel measurements and states that semantic interpretation is unavailable. No model download, remote upload or invisible edit is performed. HTTPS redirects and external endpoints are rejected; image and response sizes are bounded.

The Stable Diffusion 1.5 inference that was physically verified on ATHENA demonstrates image creation, image-to-image and masked inpainting via ComfyUI. It **is not** itself a multimodal image-understanding language model. Install and qualify a separate image-capable model to prove object/scene interpretation.

## Independent GUI and engineering testing
python -B scripts/test_visual_understanding.py validates real pixel statistics, local OpenAI-compatible model discovery, JPEG image-url payloads, model name verification, redirect rejection, user-visible GUI results and undoable reviewed effects against an isolated local HTTP fixture. The fixture tests protocol only, not a genuine vision model.

\`python -B scripts/self_test_image_intelligence.py\` now requires real pixel evidence and never invents exported background-removal files. The Windows/Linux release workflow runs both tests.

### Further work before any "ChatGPT-level image intelligence" claim
- Physically install and test an actual local VLM on ATHENA; benchmark real diverse images, text reading, object count/placement, spatial questions and false positives.
- Improve user-specified object masks and segmentation, grounded region selection and model-aided editing with evidence that the targeted region was changed.
- Add iterative visual critique → edit → render → compare, rather than claiming one-shot visual parity.
- Test across high-resolution photographs, posters, non-Latin typography, transparent assets and varied color profiles; measure latency and VRAM.
- Follow actual model licenses and separately qualify source image privacy, commercial distribution and any production release signatures.

These are honest product gaps. This feature is a substantial measurable step, **not** a claim to reproduce OpenAI's proprietary image models or ChatGPT's image-understanding ability.
