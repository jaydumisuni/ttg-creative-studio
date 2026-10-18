# Creative Studio Professional 3D V4 — executable feature extension

Independent Studio native authoring plus **external Blender execution**. No
Hunter, Ptah or model checkpoints.

## Added

- Real Blender Smart Project / Angle Based / Conformal UV solver command, with
  margin and projection-angle constraints. Unlike face-island projection, the
  GPL Blender subprocess now invokes `bpy.ops.uv.smart_project` or
  `bpy.ops.uv.unwrap` and fails if the generated UV layer is missing.
  Existing hand-authored UVs are never silently overwritten.
- Validated directed acyclic geometry graph with explicit source links,
  independently processed branches, an actual Join Geometry node and a chosen
  terminal. A node can only use an earlier named source, limiting cycles and
  arbitrary code execution. Whitelisted transform, wave, subdivision and join.
- Two-bone IK pole controller created as a real Blender empty and pose IK
  constraint. Also normalized skin weights and a bounded multi-dab
  topology-changing sculpt stroke in the native editor.
- Qt controls integrated with existing undo/redo and Studio scene JSON; the
  scene validator rejects invalid node edges/outputs, bad UV settings and
  unsupported pole targets before invoking Blender.

## Evidence and limits

`python -B scripts/test_pro_3d_v4.py` runs native authoring/Qt, invalid
input handling, saved scene roundtrips and, when Blender is available,
real .blend inspection. Dedicated Windows/Linux GitHub CI uses Blender
only on the Linux runner and tests the complete V3 regression suite.

**Do not claim complete Blender parity.** This V4 adds real UV algorithms and
multi-branch Geometry Nodes, not every arbitrary Blender socket/data type.
Topology stroke is mesh-changing native brush but not every Blender Dyntopo
mode or sculpt texture/brush. IK pole/weight normalization adds important rig
operations but is not a full industry character animation/retargeting editor.
Physical simulation baking needs independent compatible engine qualification;
old Blender 3.4 fluid evaluation had a hard crash and is not silently enabled.
Commercial release signing is an independent gate.

No temporary test renders, duplicated weight files or donor checkout belong
in the repository.

## Isolated cloth simulation baking

The 3D Lab now exposes **Bake Cloth Cache · Isolated Blender** only after a
real Blender scene with a cloth object has rendered. It launches a separate
Blender GPL worker via `src/ttg_blender_simulation.py` and accepts the run
only if the physical cloth point-cache reports baked, a new `.blend` is
saved, and a JSON digest receipt is emitted. The source scene is preserved;
failed or crashed runs cannot claim completion. `test_simulation_bake.py`
qualifies this in an actual separate Blender process on Linux CI, without
running Blender on KRATOS.

Gas/liquid cache baking is implemented as a separate *opt-in experimental*
path that rejects Blender versions earlier than 4.2 and requires actual cache
files and a saved `.blend` before reporting success. Blender 3.4's previously
observed fluid evaluation crash means gas/liquid production acceptance is
**not achieved** by this workflow. Complex collision systems and long-running
production-quality simulations remain distinct from bounded cache existence.
