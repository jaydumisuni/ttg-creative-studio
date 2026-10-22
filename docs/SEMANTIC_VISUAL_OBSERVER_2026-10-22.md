# Creative Studio — opt-in semantic visual-observer handoff (candidate)

This is a bounded integration to the existing Studio creative_execute
interface, not a new renderer, model install, artistic certification, or proof that
a real vision model was tested. Quick Studio rendering works unchanged.

## Schema

options.visual_observer must contain exactly:
- schema: ttg.studio.visual-observer.v1
- endpoint: explicit local http://127.0.0.1:<port> base URL
- model: explicitly named model advertised by that server
- question: brief visual inspection request

The existing LocalVisionServer observes the actual emitted PNG, not an image
source project or fabricated model result. It rejects non-loopback addresses,
proxy redirection, redirects, unexpected models and oversized replies. The
observer record binds image SHA-256 before and after inspection. Output is
unverified advisory; model output never mutates art or certifies acceptance.

If a requested observer is unavailable or the image changes during observation,
the result is visual_observer_unavailable and CLI ok=false. PNG and project are
retained for diagnosis and rerendering.

## KRATOS engineering proof

python3 -B scripts/test_semantic_visual_gate.py

The test renders actual Studio images, reopens editable projects, verifies PNG
digests, tests an absent local model, rejects invalid endpoints, and exercises
a SIMULATED OpenAI-compatible local transport. The mock is NOT real semantic
visual inference or image-quality certification.

## Remaining independently scoped gaps

- Live image-capable model observation and verified visual understanding.
- Open-domain interpretation of unfamiliar user objects and scene constraints.
- Genuine independent image-quality scoring, correction, and bounded retry.
- G6.3/G6.6 provider-authorized photography and ten unseen real images.
- Ptah A05/E07 production enrollment and future Hunter mounting.

Sergeant owns independent engineering review, not artistic approval.
Tenfold/Cookpit are never impersonated by ordinary Studio artwork tasks.
