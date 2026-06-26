# UI Last Rule

TTG Creative Studio should not be built by designing panels first.

The UI must sit on top of working capability like a glove.

## Build order

```text
1. Engine
2. Workflow
3. Proof output
4. UI
5. Polish
```

## Why

A pretty UI without capability creates false progress.

A capable engine without a clean UI is ugly, but fixable.

The correct path is:

```text
make it work
prove it works
then make it beautiful and easy
```

## Rules

- Do not add UI controls before the underlying action exists.
- Do not expose every internal feature as a button.
- Prefer fewer visible controls with stronger capability.
- Every UI section must map to a real workflow.
- Easy Mode should hide complexity.
- Advanced Mode should reveal power only when needed.
- Motion Mode should expose timeline/video controls only after the still/edit workflow is solid.

## Current priority

The current priority is not making the window prettier.

The current priority is making these core workflows actually work:

```text
Canvas editing
Properties editing
Asset import
Ad project generation
Timeline/motion
Export proof
```

After those work, the UI should be redesigned around proven workflows.
