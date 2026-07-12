# TTG Creative Studio Benchmark Gap Report

This report turns ahead-of-us benchmark tools into practical TTG engineering targets.

## Current visual artifact state

- ttg_reference_still.jpg: present (768632 bytes)
- reference_motion_contact_sheet.jpg: present (344100 bytes)
- reference_motion_preview.gif: present (5750128 bytes)
- ttg_visual_proof_manifest.json: present (1649 bytes)
- VISUAL_PROOF_REVIEW.md: present (1397 bytes)
- ttg_ad_contact_sheet.jpg: missing until visual proof generation runs

## Benchmark gaps

### Penpot / tldraw / Excalidraw class

- Task attempted: Editable canvas, direct manipulation, handles and approachable layout workflow.
- TTG proof: ttg_reference_still.jpg, UI/offscreen workflow tests, canvas interaction tests
- Gap found: Canvas engine exists, but final professional editor feel, cursor states, guides and multi-select polish still need visual comparison.
- Next implementation target: Use benchmark editor feel to tune snapping, handles, guides and layer manipulation UX.

### CreatiPoster class

- Task attempted: Turn asset package into editable poster/ad project.
- TTG proof: ttg_ad_from_zip.ttgstudio.json, ttg_ad_contact_sheet.jpg, app ad ZIP import test
- Gap found: Ad ZIP workflow exists, but visual template quality and automatic layout intelligence must improve against real poster/ad examples.
- Next implementation target: Add benchmark-style layout scoring: hierarchy, spacing, CTA prominence, brand consistency and safe margins.

### OpenShot / Kdenlive / Flowblade / Shotcut class

- Task attempted: Timeline, preview, tracks, keyframes and export workflow.
- TTG proof: reference_motion_contact_sheet.jpg, reference_motion_preview.gif, frame export path, video gate
- Gap found: Timeline primitives and proof preview exist, but full track editor, trimming and polished playback UI are still below NLE benchmarks.
- Next implementation target: Build track-based timeline UI after engine proof, with visible keyframes, playhead and clip handles.

### Remotion / Motion Canvas class

- Task attempted: Repeatable code-driven motion templates and reproducible renders.
- TTG proof: reference_motion_frames, reference_motion_preview.gif, visual proof manifest
- Gap found: Motion render proof exists, but template parametrization and programmable scene systems need stronger abstraction.
- Next implementation target: Create reusable motion-template definitions for ads, intros and product explainers.

### Blender class

- Task attempted: True cinematic 3D text, camera, lights, depth and particles.
- TTG proof: ttg_reference_still.jpg, reference_motion_preview.gif
- Gap found: Current renderer is still mostly 2D/2.5D. True 3D depth/camera/lighting remains the biggest cinematic gap.
- Next implementation target: Add a 3D renderer bridge or dedicated cinematic scene engine for title depth, camera moves, lighting and particles.

## Rule

Benchmark reports are not marketing. They are engineering pressure.

If TTG output looks or feels worse than the benchmark class, the difference becomes the next build target.