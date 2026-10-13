# TTG Creative Studio — Ptah embedded specialist adapter

**Status:** development-qualified embedded proof; not admitted as a production Ptah Node/Provider or live service.

This is a Creative Studio-owned consumer of **existing, unchanged Ptah APIs**, not a fork of Ptah, not Hunter, and not a competing workspace.

## Implemented boundary

- Ptah A06 — creates a durable Workspace in an isolated ledger.
- Ptah A04 — Activity / Operation / Attempt state and evidence receipts.
- Ptah A05 — launches the actual Creative Studio Python worker and an independent verifier as separate native processes; a spawn acknowledgment is not accepted as completion.
- Ptah A07 — registers each independently checked result in local content-addressed storage, verifies a read-back hash and requires a separate promoted Artifact operation.
- Creative Studio — owns request semantics, editable project format, actual rendering, assets, contact sheet and request-vs-result checks.

## Local prerequisites

Linux with Python 3 + Pillow, Rust toolchain and an existing sibling checkout:

```
<projects>/TTG-Creative-Studio
<projects>/Ptah-space
```

Ptah remains read-only; Rust uses sibling crates via relative Cargo paths. No always-on daemon, GPU, Hunter, privileged operation or external generator is required for the two initial operations. Building with Cargo requires package dependencies already installed or accessible; `--offline` is supported when cached.

## Discoverable specialist contract

`studio_tool.json` identifies the candidate and two supported task names. It is **Creative Studio's own manifest**, not proof that Ptah's registry has discovered or admitted this adapter.

```json
{
  "schema":"ttg.creative.ptah.request.v1",
  "request_id":"scene_edit_v1",
  "operation":"scene_edit",
  "text":"THETECHGUY",
  "move_x":108
}
```

Or:

```json
{
  "schema":"ttg.creative.ptah.request.v1",
  "request_id":"ad_campaign_v1",
  "operation":"ad_from_assets",
  "asset_dir":"<absolute Studio .workspace assets directory>",
  "title":"THETECHGUY DIGITAL SOLUTIONS"
}
```

Place request JSON, inputs and result directory within Creative Studio's `.workspace` boundary. The ad task requires 2–6 images, each no more than 15 MB. Symlinked/foreign-source files are rejected. External client delivery requires human acceptance.

```bash
cargo build --offline --manifest-path integrations/ptah/Cargo.toml
integrations/ptah/target/debug/ttg-creative-ptah-adapter --describe
integrations/ptah/target/debug/ttg-creative-ptah-adapter \
  --request .workspace/scratch/<proof>/fixtures/<request>.json \
  --run-dir .workspace/scratch/<proof>/runs/<request>
```

Supply `CARGO_TARGET_DIR` to move build outputs under `.workspace/scratch` for clean repositories.

## Product outputs

Each successful run retains a Ptah ledger, native process + Activity/Attempt/Receipt history, registered CAS bytes, exact SHA-256/Location/Revision/Artifact IDs and `ptah_proof_manifest.json`. It registers exactly three Artifacts: an editable `.ttgstudio.json`, the preview image, and a portable `project_bundle.zip` with all asset dependencies. The ad source files remain unchanged.

Note that the standalone `.ttgstudio.json` refers to relative `assets/` paths. It must be used **with its extracted bundle**, not in isolation.

## Replay/uncertainty contract

`--resume` reopens the retained ledger and checks request identity, SHA-256 and exact stored CAS and output bytes. Ad requests also fence original asset digests. A verified completed request is reused without dispatching a second Attempt. A new run without resume at an occupied run directory is rejected. A partial/uncertain run without a final manifest is **not automatically rerun**; deliberate reconciliation/new Attempt is required.

No production Node enrollment, renewed provider lease, intermittent E06 synchronization, resident Ptah HTTP dispatcher, native Ptah plugin-registry admission, multi-host recovery or complete edit-history recovery is claimed. An independently redrawn preview does not establish marketing/design quality or owner visual acceptance.

## Qualification

Use `scripts/test_ptah_adapter.py` on KRATOS for real positive, replay and adversarial tests. All evidence and generated inputs remain in the Creative Studio-owned `.workspace`. No Ptah repository changes or system services are needed.
