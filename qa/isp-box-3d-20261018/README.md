# TechGuy ISP Box — cinematic 3D concept render (2026-10-18)

This is a more demanding **true modeled 3D scene** than the earlier flat Prism artwork. It includes perspective-projected CNC aluminium enclosure, bevels, screened OLED, single top button, projected brand label, two front gold-finger slot openings and moving 3D camera. Surface normals drive two-light shading; a world-space stage and cast shadow establish depth.

**View:** [Poster](ispbox_3d_poster.png) · [Five-second film](ispbox_3d_final.mp4) · [Three-shot comparison](ispbox_3d_contact_sheet.jpg)

- **Poster:** 1280×720 native Creative Studio still.
- **Film:** 1280×720, five seconds, 20 fps, 100/100 successfully decoded H.264 frames, verified changed images.
- **Editable Creative Studio projects:** [still](ispbox_3d_poster.ttgstudio.json) and [motion](ispbox_3d_motion.ttgstudio.json). The layout and nine layer objects remain editable, while the real 3D footage is linked as an ordinary video layer.
- **Reproducible source:** [procedural 3D mesh/camera scene](render_3d_scene.py) and [Creative Studio composition/export](build_studio_showcase.py). Both are Python files and generate real assets, not packaged neural models.
- **Assets:** [3D footage](assets/ispbox_3d_source.mp4) and [3D still](assets/ispbox_3d_still.png), needed to reopen without rerendering the 3D helper.
- **Evidence:** [manifest](render_manifest.json), including exact hashes, output sizes and frame comparison.

**Important boundary:** Existing Creative Studio's core renderer is **2D/2.5D**, not a general interactive 3D mesh editor. This QA adds a genuine external 3D geometry render pass and uses *Creative Studio itself* for the editable typography, animation, image composition, poster and final MP4. The source geometry is editable in the included deterministic 3D script; it is not editable as vertices inside Studio's GUI. This is a *design visualization / prototype concept*, not a manufactured device photo or validated CAD.

**Reproducibility:** [23-check regression suite](test_3d_showcase.py) passes on KRATOS (3D orbit geometry, physical film decode, actual Studio layer stack, hash custody). Run `python -B qa/isp-box-3d-20261018/test_3d_showcase.py` from repository root with Pillow and NumPy.

**Zero cloud inference:** No Replicate token, paid requests or downloaded image/video model weights. This proves stronger 3D-assisted creative production, not live neural image or video generation.

Assets are intentionally isolated on the QA branch; **do not merge the binary renders into production main**. Scratch frames and video-export temp directories were deleted after rendering/verification.
