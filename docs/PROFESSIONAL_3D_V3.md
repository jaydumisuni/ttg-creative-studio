# Creative Studio Professional Native 3D V3

This is a substantive, **standalone Creative Studio** engineering extension of
Advanced Native 3D V2 (PR #33). No Hunter, Ptah or AI model is required.
Blender remains a separately installed GPL application through the approved
process bridge, and Studio retains the native editable scene JSON.

## Newly implemented

1. **Local topology-changing sculpt**: mesh face-centre refinement within a
   selected brush radius, with bounded polygon budget and signed offset.
   Unlike earlier inflate/smooth brushes it adds real vertices and faces.
   It intentionally rejects sculpting after UV, rig or multires edits because
   topology changes would invalidate existing mappings. It is not the complete
   Blender Dyntopo brush engine.
2. **UV islands/seams**: per-face, axis-projected UV island packing into
   nonoverlapping 0–1 atlas cells with configurable padding; native per-edge
   seams are persisted and written as actual Blender marked mesh edges.
   This is reliable face-island packing, not a full angle-based unwrap solution.
3. **Rigging**: radial weight painting with add/subtract/replace and
   proportional influence; user-authored IK target and ancestor chain count.
   Blender builds actual armature/vertex group and IK constraints with an
   explicit target object; no IK computation is fabricated inside the Qt app.
4. **Multires**: 1–3 subdivision levels stored in scene and built into the
   real Blender MULTIRES modifier using `bpy.ops.object.multires_subdivide`.
5. **Editable Geometry Node chains**: native UI can append, reorder and
   remove an ordered list of transform, subdivision and wave nodes; the GPL
   bridge constructs the corresponding actual GeometryNodeTree with sockets
   linked in order. Input JSON is schema validated and cannot execute Python.
   This is a bounded visual node-chain editor, not arbitrary Blender node
   tree parity.
6. **Cloth, collision and fluid modifiers**: native Qt selects real Blender
   cloth/collision or SMOKE/Liquid domain/flow properties. Blender runner
   constructs modifiers with bounded quality and 16–64 fluid resolution.
   **Unbaked fluid modifiers are saved with viewport/render evaluation
   disabled**, because older Blender builds crashed while evaluating them.
   Users must separately qualify a compatible fluid bake before enabling
   those modifiers. Building a saved modifier is **not evidence of baked
   physics**, numerical stability, or production-quality simulation.

## Verification and release boundaries

Run `python -B scripts/test_professional_3d.py` on either OS with Studio
dependencies installed. Test builds genuine editable UV/IK/node/physics
scenes, exercises actual Qt buttons and Undo/Redo, validates malformed
inputs, save/reopen and local topology changes. In Linux CI with Blender
installed it also renders and inspects the saved `.blend` for multires,
seams, IK constraints, actual node modifiers, cloth and multiple FLUID
domain/flow modifiers. Windows CI verifies native operations without
pretending that Blender is installed.

The professional engine is usable for individual validated 3D product
design workflows, but **full Blender 3D parity remains outside this V3
scope**: industrial angle-based UV unwrap/multi-island parameterization,
complex Dyntopo strokes and texture sculpt, arbitrary nodes with branches,
full character rigging/weight-paint/IK rig studio, and **baked validated
fluid, smoke, combustion, cloth** under real-world conditions have not
all been demonstrated.

Production release signing is an independent non-bypassable acceptance
gate. No approved publisher certificate/private key was available in
prior signing audits. Do not claim an official signed build from
unsigned packages, self-signed QA artifacts, or a simulated signing
receipt. The existing Builder release authority remains unchanged.

No model checkpoint, extra Blender source checkout, donor import,
temporary generated proof or duplicate media files are shipped here.
