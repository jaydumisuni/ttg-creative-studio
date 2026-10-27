# Studio Director workspace handoff — 27 October 2026



This is a data-custody adapter around the **existing** Creative Studio `image_info` CLI. It is not a new creative engine, image recognizer, or remote worker.



An authorized Armour/Ptah staging step must first place a file under `~/.local/state/ptah/hunter-creative-inbox/<actor>/<workspaceId>/<fileId>/input.<image-extension>` and a matching private `manifest.json`. The manifest fields are actor, workspaceId, fileId, SHA-256, original filename, byte count, and source `hunter-owner-r2-v1`. The staging root and every folder must be owned by the local process and mode 0700; symlinks, path traversal, unknown formats, hash drift, over-budget files and other actors are rejected.



The Python adapter validates this receipt, calls `src/ttg_creative_studio/cli.py` with a temporary `image_info` job, validates its actual success artifact, and returns a bounded metadata-only receipt without exposing the staging path. It does not claim image semantics, PDF interpretation, user intent reasoning, or finished Creative Director file transport.



Run the seven deterministic tests with `PYTHONPATH=src python3 -m unittest discover -s tests -p test_hunter_workspace_handoff.py -v`. A 5×7 PNG was processed by the real existing Studio CLI; wrong actor, digest tampering, symlinks, traversal, PDF input and non-private staging were all rejected.



**Not yet connected:** account-scoped Hunter R2 -> Ptah/Oracle node write. Hunter's current Oracle account broker admits read-only operations only. The authorized staging protocol, explicit user consent, node lease, operation custody and multi-tenant scope must be admitted upstream before this adapter can receive real user files automatically. Do not expose the adapter as public HTTP or widen it to arbitrary paths.
