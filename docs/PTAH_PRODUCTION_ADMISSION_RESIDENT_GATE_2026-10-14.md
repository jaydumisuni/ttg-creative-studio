# Creative Studio × Ptah production admission and resident process qualification

**Current stage:** development resident process qualified; production admission BLOCKED by external Ptah authority.

## Resident test on KRATOS — 2026-10-14

The Creative Studio-owned probe (`integrations/ptah/src/bin/resident_probe.rs`) launches `resident_worker.py` through **Ptah A05 NativeProcessProvider in PTY mode**, with a generation-fenced native terminal-control lease. The Python process handles two independently verified Creative Studio jobs during one actual running process lifetime, rejects duplicate requests, and completes via an explicit shutdown message. After Provider-generation advancement, the old A05 lease cannot issue new input. A second separate service lifetime starts and completes the same evidence chain.

**Observed result:** 2 distinct service lifetimes, 4 independently verified editable projects, controlled shutdowns and stale-generation/duplicate rejection all PASS.

Repeat:

```bash
python3 -B scripts/test_ptah_resident.py
```

Retained on KRATOS in `.workspace/scratch/ptah-resident-*/qualification_report.json` with per-lifetime `resident_proof.json` receipts.

## What the proof does not claim

- It does **not** enroll a Ptah production Node or establish Control-issued E02 Reservation/Lease/Fence authority. A05's development PTY input-control lease is an entirely different authority from E02.
- It does **not** install an always-on daemon, allocate production GPU resources, or expose a network service.
- It does **not** prove Control restart, E01 TLS/mutual authentication, E02 lease expiry/recovery, or Node-side fenced dispatch.
- It does **not** turn the existing Ptah HTTP human-workspace shell into an E02 dispatcher.
- Source files and tests remain within Creative Studio's registered Patrol owner path; Ptah's repository and services were not modified.

## Production preflight — read-only

`python3 -B scripts/ptah_production_admission_preflight.py --report .workspace/scratch/ptah-production-preflight.json`

The host survey records whether `ptah-control` and `ptah-node` are currently running and whether the released Ptah Node executable remains a configuration-required client boundary. It reads the historical E05 physical-Linux observation without promoting that old record to current enrollment. No credentials or tokens are inspected.

On KRATOS 2026-10-14 the result is **BLOCKED**: no running Ptah Control/Node processes were detected, the released `ptah-node` command still requires deployment configuration, and the recorded E05 host observation was `blocked` with `runtime_authorized=false`.

## Actual Ptah-owned production gate

A legitimate end-to-end production proof must bring the following evidence from Ptah itself:

1. **A02 + E01**: approved Node enrollment, current authenticated Control-to-Node TLS session bound to exact NodeId, generation and connection epoch; no invented credential.
2. **E05**: current physical Linux platform, intended host-role approval and facility/capability evidence for KRATOS or another explicitly selected host; not an old snapshot.
3. **E02**: Control-created placement, Reservation, Lease and Fence tied to the exact Creative Studio A04 Attempt, validated by the current Node before Provider invocation.
4. **D04 / A05 / A07**: provider/service selection via approved Ptah registry and accepted Recipe, actual resident specialist operation, distinct independent verification, artifact retention and read-back.
5. **Recovery**: stale lease/session rejection, orderly stop, restart, durable completion reconciliation and no duplicate external action.

These are Ptah owner/control changes or deployment operations, **not tasks the Creative Studio adapter may self-authorize**.

## Integration strategy

Once the actual authenticated Ptah Control/Node runtime is deployed, submit `ttg.creative.studio.embedded` as a candidate requiring Ptah's explicit service/recipe admission, with the same Creative Studio engine preserved. The current D04 local observation proves only the in-memory generation-fenced lookup.

A next runner must not dispatch if any E01/E02/E05 gate is unknown. Keep this evidence distinct from the standalone Creative Studio application and never create a second Ptah scheduler inside Studio.
