# Creative Studio Blender 3D donor — engineering design

## Purpose

Replace the old ISP Box showcase's 2.5D-looking Python polygon renderer with
the *real, independently installed Blender* 3D renderer: physically based
materials, mesh bevels, emissive OLED/glass/metal, softbox lights, cinematic
camera movement, and editable native \`.blend\` projects.

**Donor:** https://github.com/jaydumisuni/blender, which is a fork of
https://github.com/blender/blender. We have **not cloned its >1 GiB source tree**
into Studio or KRATOS. Studio invokes an independent Blender executable.
Blender's public Python API and documented batch mode are the interoperability
contract, not reverse-engineered internal symbols. The existing
TTG-Reverse-Engineering repo was inspected as a possible read-only source
analysis helper; static source/architecture comparison is sufficient here.
There is no unsupported Ptah deployment or copying of donor binaries.

## Studio's 3D production workflow

1. In Creative Studio, open **Tools → 3D Lab · Model / Light / Render**.
2. Start with the editable ISP Box PBR scene or load a saved
   \`scene.ttg3d.json\`. Scene JSON specifies object types, geometry transforms,
   materials, camera/lens/orbit, area lights, EEVEE/Cycles render engine and
   render budget. Edit/reload without changing a renderer script.
3. Use **Render Still** for a physical PNG, or **Render Cinematic** for a
   physically rendered frame sequence and H.264 MP4. Rendering runs in a
   Qt worker and a separate bounded Blender process. Results include the
   editable \`scene.blend\`, \`poster.png\`, optional \`film.mp4\`, the original
   scene spec and a SHA-256 evidence record.
4. Use **Add Rendered Image/Video to Studio**: the output is treated as a
   normal, editable Studio composition layer/clip. Add typography, audio,
   effects and render/export from Studio. Or **Open Editable .blend in
   Blender** for advanced mesh editing, UV/material nodes and animations.
5. Blender remains a separate executable. Studio itself works without it,
   and the interface reports an unavailable renderer instead of fabricating
   3D footage. Hunter/AI is **not** wired into this change.

The initial preset models an ISP Box *concept*, not engineering CAD or a
manufacturing-accurate design. Shape dimensions, slots and details should be
checked against hardware drawings before portraying them as manufactured
hardware.

## Performance and installation

Blender is an optional program. Install it separately on qualified hardware
and set \`TTG_STUDIO_BLENDER_EXECUTABLE\` to its executable path, or put
\`blender\` on PATH. No Blender source compilation, 92 GiB generative model,
GPU driver changes or model downloads are part of this integration. Cycles
can render on CPU; more hardware helps with professional production quality.
Use lower sample budgets for previews and higher budgets for final images.

The renderer bounds the scene to 96 objects, 12 area lights, 240 frames,
8.3 megapixels per frame, <=512 samples and 1-hour job timeout. It caps
Blender rendering threads to 2 by default to avoid monopolizing KRATOS.
It cleans temporary frames on success to prevent storage waste. It never
silently overwrites an existing output directory. Large final 4K projects
can still consume significant render time and disk: keep them on appropriate
hardware.

## GPL licensing boundary

Your Blender fork's modified \`COPYING\` text does **not** override upstream
Blender source licenses. Blender is GPL-3.0 and source derived from it remains
subject to GPL. The contained standalone
\`integrations/blender/gpl_scene_runner.py\` bridge uses \`bpy\` and is
explicitly **GPL-3.0-or-later**, with source supplied. It executes only inside
Blender and never imports into the main Studio process. The main Studio
application passes JSON data across a CLI process boundary without using
Blender code or the Blender Python API itself, consistent with Blender's
licensing FAQ. Distribution of a bundled/modified Blender executable
would require separate GPL/license/source-compliance work.

Official guidance:
- https://www.blender.org/support/faq/
- https://docs.blender.org/manual/en/latest/advanced/command_line/render.html

## Tests and claims

\`scripts/test_blender_3d.py\` performs model-free validator/UI checks on
both platforms. Its Linux CI job installs distribution-packaged Blender and
performs a *real small Cycles render*, saves a \`.blend\`, outputs PNG + MP4,
checks actual frame decoding, confirms different camera frames, and removes
unneeded intermediates. On Windows the contract is tested without Blender
installed; unavailability must fail closed. Installer/manual visual
acceptance on actual ATHENA or future GT502/Spark remains distinct.

This closes the external high-quality rendering backend gap. It does **not**
claim that Creative Studio has a full embedded mesh-modeling viewport,
Blender-equivalent physics simulation, or Blender's entire UI.
