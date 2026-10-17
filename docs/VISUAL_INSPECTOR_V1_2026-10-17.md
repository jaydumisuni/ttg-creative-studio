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
The same dialog accepts a user-supplied installed **Ollama image-capable model** and explicit \`http://127.0.0.1:11434\` endpoint. When available, Studio verifies the installed model name, sends an actual JPEG encoded from the selected image to the loopback \`/api/chat\` endpoint, and displays the reply in a clearly marked **review-required interpretation** section. The model is instructed to describe only visible content, say when uncertain, and never claim it edited the image.

If the model is absent/offline/invalid, Studio continues with honest pixel measurements and an explicit model-unavailable explanation. No model is downloaded, no image is sent to a remote provider and no model-generated instruction is executed as code. The request refuses redirects and limits response sizes and input images.

The Stable Diffusion 1.5 inference that was physically verified on ATHENA demonstrates image creation, image-to-image and masked inpainting via ComfyUI. It **is not** itself a multimodal image-understanding language model. Install and qualify a separate image-capable model to prove object/scene interpretation.

## Independent GUI and engineering testing
\`python -B scripts/test_visual_understanding.py\` verifies real image pixel measurements, the installed-model discovery and base64 image wire contract against an isolated test HTTP server, explicit unreviewed interpretation status, dangerous redirect rejection, GUI results, effect application, undo and malicious effect rejection. The local mock receiver validates protocol; it is **not** proof of real semantic inference on an installed VLM.

\`python -B scripts/self_test_image_intelligence.py\` now requires real pixel evidence and never invents exported background-removal files. The Windows/Linux release workflow runs both tests.

### Further work before any "ChatGPT-level image intelligence" claim
- Physically install and test an actual local VLM on ATHENA; benchmark real diverse images, text reading, object count/placement, spatial questions and false positives.
- Improve user-specified object masks and segmentation, grounded region selection and model-aided editing with evidence that the targeted region was changed.
- Add iterative visual critique → edit → render → compare, rather than claiming one-shot visual parity.
- Test across high-resolution photographs, posters, non-Latin typography, transparent assets and varied color profiles; measure latency and VRAM.
- Follow actual model licenses and separately qualify source image privacy, commercial distribution and any production release signatures.

These are honest product gaps. This feature is a substantial measurable step, **not** a claim to reproduce OpenAI's proprietary image models or ChatGPT's image-understanding ability.
