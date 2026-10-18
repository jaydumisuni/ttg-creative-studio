# Creative Studio Advanced Native 3D V2

Creative Studio now authors advanced editable 3D scene data in the native Qt
editor and renders it through a separate GPL Blender subprocess. No Blender
source fork or AI weights are downloaded to KRATOS.

## Implemented category subsets

- Sculpt brushes: bounded vertex/edge/face inflate, deflate and Laplacian
  smooth with adjustable radius and strength, reversible via Undo.
- UV authoring: planar projection along X/Y/Z, numerical translation and
  selected face-corner edits. Real UV layers are built inside Blender.
- Rigging: bounded parented bone hierarchy, per-vertex weights and bone
  rotation animation keys. Blender builds Armature objects, vertex groups
  and modifiers. No full inverse kinematics system is claimed.
- Constraints: validated COPY_LOCATION or TRACK_TO between scene objects.
- Geometry nodes: explicit editable transform or sine-wave procedural
  presets. Blender builds the actual GeometryNodeTree modifier.
- Physics: rigid-body ACTIVE and PASSIVE configurations with bounded mass,
  friction and Blender rigid-body modifier, not invented local simulation.
- Editable scene save/reopen, scene validation, undo/redo and Blender
  physical rendering through the pre-existing GPL subprocess boundary.

All native controls work without Blender. Cycles rendering, geometry-node
evaluation, rigs and physical simulation require the installed external
Blender backend and are **not** claimed to execute on KRATOS.

## Honest limits: no Blender feature parity claim

Native sculpt does not yet reproduce full Dyntopo and multiresolution,
complete brush systems or texture paint. UVs lack industrial unwrap
packing/seam workflows. Bone editing lacks full IK and weight painting.
Geometry nodes provide validated presets rather than arbitrary authored
visual graphs. Physics supports rigid bodies, not cloth/fluid/fire/smoke
simulation. Those remain substantive larger requirements.

Source-level success does not qualify complete Blender functionality.

## Tests, release and licensing

The advanced test exercises real changes and scene contract validation,
save/reopen, QWidget actions, Undo/Redo and invalid input rejection.
Linux CI installs standalone Blender to render and inspect actual UV,
armature, procedural modifier, constraints and rigid bodies inside .blend.
Windows CI runs the native editor and schema tests and does not fabricate
Blender output. Pre-existing 3D and image/video tests continue to run.

Blender bridge file is GPL-3.0-or-later, distributed with full GPL license
and executed only in a separate Blender process. No TTG Reverse Engineering
runtime dependency, Hunter deployment or Blender source checkout added.

Production signing remains an independent release authority. An unsigned
engineering installer or self-signed QA certificate is not a signed
commercial release; official signing needs an approved identity and keys.
