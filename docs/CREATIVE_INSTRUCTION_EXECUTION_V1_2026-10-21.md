# Creative Studio instruction-to-execution bridge — 2026-10-21

Status: bounded native execution verified on KRATOS; photoreal visual acceptance and qualified external workforce execution not claimed.

## Ownership

Creative Studio owns its existing canvas, scene schema, material renderer, image editor, exporter and pixel inspection. ChatGPT or Hunter later may interpret natural language into explicit scene/edit packets. Ptah is the workspace, Oracle transports machine calls. Tenfold Foreman may execute approved substantial engineering campaigns, Cookpit may coordinate declared long-running jobs, CodeOps/Agent Code repairs source when required, and Sergeant independently reviews meaningful engineering changes. Do not instantiate these for every small image edit or impersonate a qualified worker.

## Existing job CLI

Use: python3 -B src/ttg_creative_studio/cli.py --catalog
Then: python3 -B src/ttg_creative_studio/cli.py --job /absolute/approved/job.json --result /absolute/approved/result.json

The task creative_execute has options.schema ttg.studio.creative-instruction.v1 and modes auto, scene, wall_sign, edit_project, campaign. An assistant may supply structured scene data under ttg.studio.scene-spec.v1; Studio compiles it into a real editable TTGProject. For known native office-wall signs the existing BananaActions/CinematicRenderer is used. For edits, only replace_text, move_layer, set_neon_color and set_fill are admitted against compatible unlocked layers. For campaign, Studio reuses its independent Campaign Designer.

Unknown general text in auto mode returns needs_scene_compilation and makes no image; a semantic assistant must author a valid scene specification or select an separately authorized provider. A prompt alone is not proof of visual understanding.

Scene limits: 320x240 to 1920x1440, max 2.1MP, 1–60 native shape/text/text3d layers, supported cinematic materials architectural_lobby/steel_polygon/steel_text/neon. Layer props, colors and geometry are allowlisted and bounded. Source images are available only via existing approved project assets and 128MiB media quota; arbitrary code, scripts, unqualified materials, overwrite, unsupported operation and paid inference fail closed.

A rendered_visual_review_required receipt confirms actual Studio PNG output, editable project save/reopen, pixel-identical re-render, measured image metadata and SHA256. It is not photo realism approval, a Tenfold/Cookpit execution claim, a provider-model inference claim or a Sergeant verdict.

The existing production-director and video/image interfaces remain unchanged. Hunter remains disconnected. No new renderer, LLM checkpoint or billable API introduced.

## Evidence and next qualification

scripts/test_creative_instruction_bridge.py validates a native fresh scene, text and neon edits, existing wall-sign renderer, campaign composer, CLI tool catalogue and real job execution, pixel replay, no overwrites, and rejection of unsafe input. Also run existing Studio regression scripts and a job from an actual Ptah workspace. Tenfold/Cookpit cross-system qualification should be performed with their actual runtimes if a substantial task warrants them; code-quality review belongs to Sergeant; subjective image acceptance remains a separate visual gate.

## Physical KRATOS execution (Ptah QA workspace)

- Workspace: /home/kratos/projects/Ptah-space/.workspace/workspaces/ttg-creative-studio-qa-20261018/scratch/creative-instruction-20261021 (approved scratch, NOT a Ptah E07 production-dispatch claim)
- Interpreter: real Creative Studio CLI invoked under the Ptah workspace cwd through Oracle
- First render SHA256: 695c086abe7410e827247a83e86ae0f03a76281c96ba20ab095c083c232d4325
- Subsequent editable revision SHA256: 4dd111908c4b523a62805089972ebdfaf1324b6fd233007b9b2831dcd708ba37
- Both editable projects re-render identically; changed pixels are independently demonstrated
- Reference image: none. External model usage: none.
- Native Studio proof preview: docs/proofs/studio_directed_scene_20261021.webp
- Preexisting engines and materials reused; new engine: none
- Tenfold/Cookpit production dispatch: not invoked for these two short scenes

The JSON job in examples/creative-instructions/ttg_scene_job_template.json
is an executable *template* after a client replaces the placeholder paths
with absolute paths in an authorized workspace.
