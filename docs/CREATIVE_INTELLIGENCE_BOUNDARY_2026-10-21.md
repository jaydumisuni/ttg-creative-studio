# Creative Studio Native Instruction Intelligence & Correction Extension

This is a continuation of PR #47's \`creative_execute\` operation, not a new renderer or a general-purpose generative image model.

## What is directly executable

- **Bounded natural-language design:** simple typographic posters, cards, banners and flyers with an explicit user-provided headline; Studio compiles the request to the existing \`ttg.studio.scene-spec.v1\` native layers. Requests involving people, objects, photographic images, video or unadmitted subject matter are deferred, rather than silently omitted.
- **Bounded natural-language editing:** one unambiguous instruction to change an exact text layer, move a layer to coordinates or change a single neon accent among blue/purple/gold. Ambiguous edits require the existing explicit \`edits\` contract.
- **Optional opt-in layout correction:** \`auto_correct_layout: true\` checks text-layer anchor bounds and uses actual Studio renderer image differences to determine whether a text layer contributed visible pixels. A text layer occluded by later editable artwork may be raised to the top and genuinely re-rendered. Repairs are bounded and included in receipts.
- **Existing independent replay:** project save/reopen with exact-pixel rendered replay, source/catalog and output boundaries, no overwrites, and local image measurement remain in force.
- **Native CLI:** Studio \`creative_execute\` supports this extension without Hunter or a new renderer. No provider call, checkpoint or billable job is implied.

## Trustworthy acceptance boundary

The pixel-difference check is **not OCR, external image understanding, typography accuracy certification, or independent artistic review**. The review receipt must say \`semantic_review: not_performed_no_OCR_or_vision_model\` and \`visual_acceptance: structural_and_replay_only_semantic_review_pending\`. It is incorrect to claim universal prompt interpretation, arbitrary photographic image generation, visual realism, Tenfold execution, Cookpit orchestration or Sergeant judgment based on these tests alone.

ChatGPT or a later connected Hunter remains responsible for understanding arbitrary user instructions and authoring the existing explicit scene/edit schema. Unsupported natural language returns \`needs_scene_compilation\` or \`needs_edit_compilation\`. The optional neural route retains its explicit paid-job authorization; no automatic charges or model downloads are introduced.

## Separation of concerns

Studio owns \`creative_execute\`, its interpreter, existing scene compiler, renderer, and export. Ptah may provide an authorized workspace, Oracle the machine transport. Existing Cookpit can manage long-running jobs and evidence where a project profile is admitted. Existing Tenfold Foreman can coordinate sufficiently defined and approved engineering campaigns; it is **not** silently launched for routine artwork or replaced with a fake chat-only workforce. CodeOps/Agent Code handle missing engineering changes within their own approval rules. Sergeant independently reviews non-trivial code changes, not artistic taste.

## Proof commands

\`\`\`bash
python3 -B scripts/test_creative_instruction_bridge.py
python3 -B scripts/test_creative_intelligence.py
python3 -B scripts/test_studio_production_director.py
\`\`\`

The GitHub Actions workflow \`.github/workflows/studio-production-director.yml\` runs both bridge and native instruction/correction checks on Windows and Ubuntu. Physical KRATOS proof and CI results must be recorded per candidate HEAD; a green local run does not itself certify CI or merge.

## What is not yet qualified

General open-domain intent parsing, unknown-scene photo realism, independently observed semantic vision-model correction, and Tenfold/Cookpit production dispatch for complex multi-job creative campaigns. Keep these explicit until real executed evidence exists.

## Regression qualification: cinematic material design-space preservation — 2026-10-21

Visual inspection of a real auto-reviewed native wall-sign image exposed an
incorrect automatic layout repair. The existing \`BananaActions\` template
stores cinematic \`steel_text\` transforms in a **1440×1080 authored space**,
which \`CanvasRenderer\` scales at draw time. The first correction implementation
mistakenly clamped such authored coordinates to the **640×480 output canvas**,
moving distinct wordmark and subtitle anchors onto a shared baseline. Both
layers still contributed pixels, so the first pixel-differential visibility
check did not expose the overlap.

The corrected bounded repair uses **material-native design bounds** for
\`cinematic_material=steel_text\`, while retaining output-canvas bounds for
ordinary text. No new renderer, new scene geometry, or image model is added.

Acceptance requires a *real native* image exported with and without opt-in
layout review to have **identical SHA-256** when its material scene is already
valid, and its authored text anchors must remain \`594\` (THETECHGUY) and
\`729\` (DIGITAL SOLUTIONS) on the tested 640×480 wall-sign scene.
The broader independent semantic/artistic acceptance remains open.
