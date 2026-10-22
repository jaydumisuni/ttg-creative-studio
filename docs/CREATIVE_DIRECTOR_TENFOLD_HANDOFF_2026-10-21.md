# Creative Studio director — approved execution and evidence

## Product boundary

Creative Studio owns scene compilation, rendering, editable projects and
acceptance against explicit creative requirements. Neither Tenfold nor Cookpit
is a new renderer or a creative-language model. Ptah is workspace and
Oracle is transport. Hunter mounting remains separate.

The assistant first inspects Studio's real catalog with
python -B src/ttg_creative_studio/cli.py --catalog .
The creative_execute.scene_capabilities result is produced from Studio's
real supported layer/material allow-lists. It helps an authorized assistant
write a bounded scene specification or recognize an unsupported request.

## Execution and feedback

1. Interpret the user request through an authorized assistant or Studio Director.
   Do not claim Studio's bounded native parser understands arbitrary photos.
2. Submit creative_execute with explicit scene/edits and optionally
   declared exact text/material acceptance.
3. Studio renders, saves an editable project, PNG and receipt.
4. Failed text/material/pixel acceptance produces correction_required with
   CLI ok=false: a valid PNG alone is not completion.
5. Only approved source-wording or bounded layout corrections are applied.
   The `set_text_size` native edit now permits a verified integer font size
   (10–230) only on unlocked text/text3d layers. It changes the saved project
   and rendered pixels, including the existing brushed-metal text material.
   External artistic observations still require an authorized assistant or
   qualified image-capable model to create an explicit edit packet; Studio
   cannot infer aesthetic defects from pixel visibility checks alone.
   The corrected native render and saved-project replay are verified.
6. Passed deterministic checks produce rendered_visual_review_required,
   not semantic or photorealistic approval. Inspect the real image for
   subject, quality and details before describing it as accepted.

## Orchestration and independent qualification

Quick jobs use Studio's Director and render engine directly.
Complex approved *engineering campaigns* may use real Tenfold Gen1.
Run python3 -B scripts/qualify_creative_tenfold.py --tenfold-root
<TENFOLD_CHECKOUT> --qt-deps <OPTIONAL_QT_DIRECTORY> --receipt <EVIDENCE_JSON> on a clean, committed
Studio source worktree. This imports the actual Tenfold Foreman,
scheduler, workforce and isolated workers to run Studio acceptance,
and rejects stale source identity. It does not certify visual quality.

Cookpit can manually run the accepted project profile and capture
recovery/evidence; no timers or registry changes are needed.
Sergeant independently reviews engineering changes and does not
replace product-specific artistic acceptance.

## Separate qualification remains

- Open-ended natural-language inference for unfamiliar photographic
  scenes is not established by deterministic Studio scene tests.
- Independent semantic visual quality requires a separate qualified
  image-inspection route, not just pixel-change evidence.
- Actual paid-model provider G6.3/G6.6 testing remains a separate
  credentials/admission and visual-acceptance boundary.
- Hunter integration remains deferred.
