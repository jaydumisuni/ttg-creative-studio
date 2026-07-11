# THETECHGUY Building Standard

This standard applies across THETECHGUY projects: Hunter, Creative Studio, Software Builder, Tool, Events, Pay Gateway, and future worker systems.

It exists to keep engineering claims honest, implementation complete, visual quality verified, and testing meaningful.

## 1. Finish, then prove

Complete the intended implementation first.

Then:

1. Review it thoroughly.
2. Freeze it.
3. Perform clean-clone/runtime proof.

Do not use runtime testing as a substitute for finishing the implementation.

## 2. Code should justify execution

Do not run code hoping to discover whether it works.

Run it expecting success because the reasoning, review, and implementation already support that conclusion.

If it fails, the failure should be surprising and treated as a finding.

## 3. Claims must match implementation

Documentation, reports, submission notes, and release claims must match the actual code.

Examples:

- If the docs say AI reasoning, the code must not only be regex rules.
- If the docs say video export, the app must actually produce video output or clearly state the required pack/gate.
- If the docs say canvas editing, the user must be able to manipulate objects, not just see a mock panel.

The reviewer must compare claims against implementation before runtime testing.

## 4. Evidence before conclusions

Use live sources:

- Current code.
- Git tree.
- Raw files.
- Actual scripts.
- Test outputs.
- Generated artifacts.
- Screenshots, previews, rendered frames, videos, or UI captures where visual quality matters.

Do not rely on cached summaries or memory when proof is required.

If sources conflict, report the conflict instead of choosing one blindly.

## 5. Tests are proof, not discovery

Runtime tests should confirm the engineering work.

Most issues found after this stage should be:

- Polish.
- Edge cases.
- UX improvements.
- Environment differences.

They should not be fundamental design surprises.

## 6. Visual verification is mandatory for visual work

Implementation proof is not enough for visual work.

Anything involving UI, layout, branding, image generation, video, animation, ads, previews, exports, or customer-facing creative output must be visually verified.

Visual verification means reviewing real output, such as:

- Screenshot.
- Rendered still image.
- Contact sheet.
- GIF preview.
- Video proof.
- UI capture.
- Exported artifact.

For visual work, the proof chain is:

```text
Code review
↓
Workflow/test proof
↓
Visual artifact
↓
Visual review
```

A visual feature is not done just because the code runs. It must look correct for the intended use.

## 7. Engine first, UI last

For user tools, build in this order:

```text
Engine
Workflow
Proof output
UI
Polish
```

A pretty UI without capability is false progress.

A capable engine with an ugly UI is fixable.

The UI should fit on top like a glove after the workflow is proven.

## 8. Editable output first

For creative tools, generated output must remain editable where possible.

Do not flatten useful project state too early.

Preferred flow:

```text
Assets / prompt / user request
↓
Editable project/layers/timeline
↓
Preview proof
↓
Export
```

## 9. Hunter coordinates, workers execute

Hunter should not personally do every specialist task.

Hunter should:

- Plan.
- Coordinate.
- Review.
- Approve.
- Learn from results.

Specialist workers should execute:

- Image work.
- Video work.
- Audio work.
- Export work.
- Device/service workflows.

## 10. Release gate

A feature is not release-ready until:

1. Implementation exists.
2. Claims match implementation.
3. Proof script/workflow exists.
4. Generated artifact or runtime result exists where relevant.
5. Visual artifact/review exists where visual quality matters.
6. Clean environment path is known.
7. Failure mode is documented.
8. UI only exposes what is useful.

## 11. Reviewer standard

The reviewer must ask:

```text
What does the project claim?
What does the code actually do?
What proof exists?
What visual proof exists, if visual quality matters?
Can a clean environment reproduce it?
What is still missing?
```

If the answer is unclear, the feature is not done.

## Short version

```text
Finish, then prove.
Code should justify execution.
Claims must match implementation.
Evidence before conclusions.
Tests are proof, not discovery.
Visual verification is mandatory for visual work.
Engine first, UI last.
Editable output first.
Hunter coordinates, workers execute.
```
