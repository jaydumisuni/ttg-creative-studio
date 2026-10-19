# Creative Studio production-acceptance inventory — 20 October 2026

This is a point-in-time, **read-only production evidence ledger** for the Creative
Studio project. It does not authorize purchases, production certificate issuance,
AI model downloads, Oracle policy changes, or public distribution.

## Source and CI custody

- GitHub repository: `jaydumisuni/ttg-creative-studio`.
- GitHub `main` observed at audit start: `d9573f305af080ceb4b34bb010e3036723884fde`.
- The last commit modifies only two proof-project JSONs and carries
  `[skip ci]`; its parent, `ac4df5a2e4d8f6300f20c6baa0d37bee81bd0b52`,
  is the qualified build source for the release-candidate workflow.
  **Those artifacts must not be represented as exact `d9573f3` binaries.**
- Windows/Linux release-candidate CI:
  https://github.com/jaydumisuni/ttg-creative-studio/actions/runs/39245975362
  Both native-desktop jobs passed, including an installed Windows GUI self-check.
- GitHub Actions artifact **ZIP** custody observed on 20 October 2026:

| Artifact | API artifact ID | ZIP SHA-256 | Bytes | Classification |
| --- | ---: | --- | ---: | --- |
| Windows unsigned | 12183995352 | `937a03d2a55d1457f693bb0ef0273889e50bcc6561ec33d92913b488e1886ec8` | 50,819,026 | UNSIGNED candidate |
| Windows GUI proof | 12183995358 | `cff5003321f0133099259f22ab8dcda7c983afc90f798a946d61cd6222c571df` | 39,590 | Disposable runner, not ATHENA |
| Linux portable | 12182857537 | `0e677dfb44226e853745375335629352ca442ee0b0e6bf189d562b48253af3ac` | 95,874,138 | Candidate, not signed release |
| Linux GUI proof | 12183970295 | `544315dba29ea57c86c2422d0526970bd5260b2b747a006b528521a3087ebb4d` | 62,706 | Runner proof, not physical workstation |
| Windows custody JSON ZIP | 12182669904 | `747bd89ac99c0428ec6d07ec8b6bcb56137e2b68ea166c73aee0bc46b50a5e19` | 639 | Contains inner file identity |
| Linux custody JSON ZIP | 12183865487 | `0998a551f94e0d09ae460b0afcabc71de64f13cebea4bb8d647bff4987132627` | 641 | Contains inner file identity |

GitHub confirms these artifacts are not expired, with the displayed expiration
of 17 January 2027. **ZIP digests are not executable/tarball inner digests**;
use the existing custody JSON verifier on any extracted binaries.

## Current engineering validation on KRATOS

A clean, isolated worktree based on the exact current `main` passed:

- `scripts/test_studio_g4_stress.py`: 13 tests PASS.
- `scripts/test_online_image_provider.py`: 28 tests PASS (mock/provider contract).
- `scripts/test_online_video_provider.py`: 32 tests PASS (mock/provider contract).
- `scripts/test_signed_release_gate.py`: PASS (negative signing/inference gating).
- `scripts/test_production_preflight.py`: PASS.
- `scripts/review_gate_all.py`: PASS.

The review gate's prior report misleadingly labeled an **AI-generated
visual reference approval** as **human visual approval**. The checked-in
reviewer in `docs/VISUAL_APPROVAL.json` is
`OpenAI GPT-5.6 Thinking visual review`. The updated engineering
decision report identifies the reference reviewer and explicitly states
that owner release authorization, physical acceptance and trusted signing
are not established. This wording fix does not bypass the review gate.

## Current physical machine / release state

- ATHENA: Oracle node online, RTX 4070 Laptop GPU; observed D: free 23.1 GiB
  and C: free 35.6 GiB.
- **Exact project workspace `D:\projects\TTG-Creative-Studio` still denied**
  for direct Oracle terminal execution:
  `PATH_OUTSIDE_ALLOWED_ROOTS`. Its presence alone is not admission.
  Do not execute through another path to bypass this control.
- No installed Creative Studio entry observed in the standard Windows
  uninstall registry locations. Interactive physical ATHENA acceptance
  remains **NOT VERIFIED**.
- No currently valid code-signing certificate with private key found in
  CurrentUser\My or LocalMachine\My; `signtool.exe` not in PATH.
  Oracle release provider `creative-studio` not configured on either host.
  A remote CA/cloud signer could exist elsewhere, but is **not connected or
  verified**.
- No `REPLICATE_API_TOKEN` or `TTG_STUDIO_ENABLE_PAID_VIDEO`
  present in the observed KRATOS/ATHENA terminal environments.
  Actual paid image and video inference not run/qualified; the protocol
  fixture tests cannot substitute for a real successful model invocation.
  Provider credentials may exist in other stores that were not inspected.
- ATHENA ComfyUI loopback 127.0.0.1:8188 unavailable.
  **Local model inference is optional/deferred** under the online-first
  product design. Do not download FreeVideo's ~92 GiB model on KRATOS.
- GitHub Releases API returns an empty release list.
  No **signed published commercial release** exists.

## Closure (production workstreams, not merely code delivery)

| Workstream | Status | Why |
| --- | --- | --- |
| G0 — Current source/CI/artifact inventory | **PASS** | Pinned GitHub artifacts, actual SHA identity and live machine inventory |
| G1 — Physical ATHENA install, GUI, removal | **BLOCKED** | Exact Oracle workspace not admitted |
| G2 — Genuine image and video inference | **BLOCKED for real online acceptance** | No observed approved credential/billing and no authorized paid test; optional local models deferred |
| G3 — Commercial signed installer | **BLOCKED** | No verified trusted signing identity/provider |
| G4 — CI stress, visual reference proof | **ENGINEERING PASS**, physical and owner acceptance pending | Automated stress passed; AI review is not owner decision |
| G5 — Public production release | **NO-GO** | G1/G2/G3/owner acceptance absent |

## Non-substitutable external acceptance

1. Approve Oracle root access to the **exact** ATHENA workspace and perform
   real install/interactive GUI/remove testing.
2. Authorize a bounded paid provider test with appropriate credentials and
   billing. Verify actual returned image and video frames, save/reopen and
   digest receipts without disclosing API tokens.
3. Provide an approved trusted business code-signing identity through the
   protected release environment; run Authenticode/timestamp and checksum
   verification.
4. Review the actual owner acceptance package and authorize a public release,
   then publish only signed/proven binaries. Signing or publishing is **not**
   implicitly approved by requesting progress on this engineering task.

**Hunter stays disconnected; Ptah remains an optional workspace, not a
transport or release decision-maker.** No production credentials, workstation
allowed-root policies, or physical project contents were changed in this audit.
