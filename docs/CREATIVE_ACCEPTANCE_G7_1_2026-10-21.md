# Creative Studio G7.1 — assistant-declared creative acceptance and native source correction

Creative Studio retains its existing render engines and creative_execute interface. This extension addresses one previously missing handoff: the assistant specifies what must be visible, Studio verifies that requirement against editable content and real rendered pixels, and explicitly admitted source correction adjusts the native project rather than painting over the output.

## Existing contract extension

Options.acceptance uses schema ttg.studio.creative-acceptance.v1 with bounded arrays named text and materials; every item declares an existing layer_id and exact required value. The acceptance packet is supplied from the user's approved brief or by the assistant working on their behalf.

After Creative Studio renders, inspect_acceptance compares each declared layer's content/material and renders the same project without that layer to prove it actually contributed pixels. Missing, hidden, incorrect and visually absent elements become correction_required findings, rather than fake visual PASS statements.

options.repair_expected_text=true is an explicit opt-in that checks every named layer is present, editable, unlocked and visible before applying any spelling repairs, then the existing full render, save/reload and exact-pixel replay complete. Without opt-in, wording mismatches are reported but not modified. Dry run reports the proposed revisions without creating any output.

These checks prove only exact source text/material declarations and physical pixel contribution. They do not perform OCR, face detection, photorealism appraisal, open-world semantic visual inspection or aesthetic judgment. Receipt fields independent_semantic_review:not_performed and photorealism_certification:false are mandatory regardless of structural PASS.

## Working with existing specialists

An assistant obtains the existing Studio tool catalog, authors a scene/edit packet and declares user-intent acceptance requirements. Studio compiles, renders and checks its owned output. Ptah supplies an admitted workspace; Oracle transports to KRATOS. Cookpit may execute its admitted long-running profile with its actual runner and recorded evidence. The qualified Tenfold system is used for pre-approved substantial engineering campaigns only, never falsely presented as having rendered a short image. CodeOps corrects repository capabilities when needed; Sergeant independently reviews engineering, not brand aesthetics.

No new rendering engine, paid provider, AI weights, Hunter integration or default background timers.

## Physical qualification

Run python3 -B scripts/test_creative_acceptance.py, scripts/test_creative_intelligence.py, scripts/test_creative_instruction_bridge.py and scripts/test_studio_production_director.py on the exact clean candidate source; inspect the real output receipt, project and PNG. The Studio native-production workflow runs the new acceptance test on Windows and Ubuntu. Cookpit manual execution and independent Sergeant review must be recorded separately; these are not inferred from an ordinary Studio test.

## Remaining boundaries

This alone does NOT close arbitrary unknown image subjects, independent semantic image criticism, user-facing assistant orchestration with qualified Tenfold production campaigns, or G6.3/G6.6 real neural model evidence. The existing Studio engine remains authoritative. A broader creative goal closes only with unseen prompts, objective image evidence and qualified orchestrator handoffs.
