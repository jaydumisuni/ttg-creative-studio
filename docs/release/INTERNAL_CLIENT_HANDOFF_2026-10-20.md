# Creative Studio — internal AI-client handoff readiness (20 October 2026)

**Purpose:** Verify Studio's existing engine can accept tool calls from a future
authorized client. This is not a Hunter deployment or an authorization for
commercial release. The test intentionally exercises Studio *without* Hunter.

## Internal-use result versus commercial release

The shared JSON CLI, image metadata/resizing, storyboard planning and video
capability discovery can be qualified independently on KRATOS. Existing
`scripts/test_video_agent_contract.py` separately verifies native MP4
rendering and explicit denial of uncontrolled paid generation.

Run from the Studio repository:

```bash
python -B scripts/test_internal_client_handoff.py
```

The test creates only temporary assets, unsets potentially billable provider
credentials in child processes, calls the real CLI and checks outputs. Success
means **Studio's independent client contract is ready for integration work**,
not that Hunter is connected or authorized to execute it. An eventual Hunter
connection needs its own approved executor, task/filesystem scopes, identity,
idempotency and job acceptance tests; do not attach an unrestricted shell or
claim Oracle access is granted because the local CLI passes.

**Image understanding and video editing do not require a provider token.**
Actual AI image/video generation remains opt-in cloud work, requiring an
account, per-request billing consent and real-provider results. The optional
roughly 92 GiB FreeVideo checkpoint is deferred to GT502/Spark; no weights go
onto KRATOS.

## Physical and commercial NO-GO gates (not overridden)

As of this audit:

- ATHENA's exact `D:\\projects\\TTG-Creative-Studio` workspace is refused by
  Oracle with `PATH_OUTSIDE_ALLOWED_ROOTS`. An existing directory is not an
  executable admission. Do not work around it via unrelated allowed roots.
- No installed Creative Studio application entry was found on ATHENA.
- No verified usable business code-signing identity or configured Oracle
  `creative-studio` release provider was observed.
- No provider token or operator billing enablement was observed on either
  target session. No real paid model-backed image/video test was authorized
  or run.
- Owner commercial release and visual approval have not been recorded.
- No signed public release exists.

Consequently **internal-client contract PASS and G1–G5 commercial release
NO-GO can coexist**. The production acceptance ledger
`docs/release/PRODUCTION_ACCEPTANCE_2026-10-20.md` remains authoritative.
No modification to Hunter, Ptah, Oracle policies, machine certificates,
provider credentials or production release state is part of this change.
