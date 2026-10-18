# Creative Studio Native 3D Modeling Core V1

**Standalone Creative Studio feature** — no Hunter, TTG Reverse Engineering
runtime, AI model download, or Blender source/vendor checkout.

The 3D Lab now includes a **Visual 3D Modeler** tab by default alongside
Advanced Scene JSON. The viewport is drawn in native PyQt6 using bounded
in-process software geometry and is usable **with Blender uninstalled**.

## Interactive native editing

- Orthographic 3D viewport: left click to select, left drag to move, right
  drag to orbit, middle drag to pan, mouse wheel to zoom. XYZ guides.
- Scene object list, add/duplicate/delete primitives; choose object, vertex,
  edge or face selection. Convert cube, cylinder, sphere and torus to actual
  editable mesh vertex/face geometry.
- Numeric object position, scale and rotation, PBR material color,
  metallic, roughness, transmission, emission strength. Select a mesh
  element and move it along X, Y or Z. Subdivide a real mesh (shared edge
  midpoints), extrude selected face with side walls and cap, or delete faces.
- Author bounded transform-keyframe animation via **Key Pose** at selected
  frame. Changes after frame 1 auto-key selected object transforms. The
  viewport displays interpolated poses when scrubbing, and **Undo/Redo**
  covers edits, topology, lighting and animation.
- Direct controls for Blender render-camera lens/location/orbit and area-light
  energy, plus adding/removing lights. Scene JSON retains all of these edits.
- File: existing Scene JSON Save/Load; it now retains meshes and animation
  keyframes. **Export Geometry OBJ** is a native format interchange and
  requires no Blender. Output is new-file-only, atomic; original never
  overwritten.

### Workflow

1. Open **Creative Studio → 3D Lab**. Open **Visual 3D Modeler**.
2. Select a shape in the scene list; change transforms and its material.
3. Choose **Convert to Editable Mesh**, then choose **Vertex**, **Edge**
   or **Face** to edit real topology.
4. Choose a new animation frame and change its transform, or use **Key
   Pose**; scrub frame numbers to see interpolated poses.
5. Save scene JSON or export geometry OBJ to an existing authorized folder.
6. For professional physically based image/video output, keep using the
   separate, established Blender renderer (EEVEE/Cycles) and import the
   resulting image/MP4 into the normal Creative Studio composition.

## Authority, interoperability and resource usage

The existing scene schema `ttg.studio.blender.scene.v1` now accepts
`type="mesh"` with bounded `vertices`/`faces`. The independently
licensed GPL Blender subprocess bridge creates a true Blender mesh via
`from_pydata`, assigns PBR materials and scene transforms, and inserts
authored location, rotation and scale keyframes. The Creative Studio
process does not import `bpy`.

Bounds: maximum 96 objects; per-mesh 8192 vertices and 8192 faces; a
scene-wide total of 20,000 mesh vertices/faces, max 64 keyframes per
object. Editing rejects invalid indices, degeneracy, repeated vertices,
NaNs and oversized scenes. Subdivision/extrusion validates new topology
before it becomes the live project. Undo history holds at most 50 scenes.
Studio retains its original render limits.

This does **not** clone Blender or promise equivalent UX/capabilities.
Advanced sculpt brushes, UV unwrapping, skinning/armature rigs,
bone constraints, geometry nodes, texture paint, fluid simulation,
complex non-destructive modifier stacks and enterprise-scale scene
performance remain outside this native V1. Those still use the
separate Blender editor/backend when needed. Building a full Blender
replacement is a much broader effort and is not honestly complete in V1.

## Qualification

`scripts/test_native_3d.py` exercises procedural topology, subdivision,
face extrusion, vertex/edge selection, mutations/undo/redo,
renderer-compatible mesh contracts, malformed geometry rejection,
save/reopen, actual OBJ output, physical Qt offscreen viewport painting,
camera controls, PBR lighting, animation keyframing and frame
interpolation.

`scripts/test_blender_3d.py` exercises these edited meshes and object
keyframes **inside a real external Cycles scene** whenever Blender is
installed on a qualified host. Windows runs native logic and frozen
installer checks; Linux CI installs Blender to render actual outputs.
No model weights or fork sources downloaded on KRATOS.

The release still requires the project's separate signed binary and
physical release-acceptance gates. A green source/CI result does not
establish Blender feature parity or commercial release acceptance.
