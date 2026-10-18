# Studio Physical 3D Gas/Liquid V5 — isolated acceptance

This branch extends merged V4's Blender process isolation for cache-backed
gas and liquid simulations. It changes **no Hunter, Ptah or KRATOS model
storage**. The entire Blender 4.5 LTS runtime download and cache production
occur in a disposable GitHub Actions Ubuntu worker and are deleted afterwards.

The approved Blender download must be an official 4.5.14 archive, checked
against the official SHA-256 manifest. It does not get committed to Studio.
The GPL Blender physics subprocess separately enables matching flow objects,
bakes real smoke/gas or liquid domains, and checks physical cache files
and bytes, a new saved .blend and a fresh Blender reopen. Crashes, missing
cache files, unsupported versions and timeouts cause explicit failure and
cleanup. No generated-looking placeholder can qualify.

The ordinary Studio render still leaves unbaked fluid evaluation disabled
because older Blender builds crashed on it. The separate experimental bake
requires Blender 4.2 or newer. Cache qualification is only a step toward
production-grade fluid work; it does not guarantee visually accurate
simulation, stable long-form physics, collisions, fire, materials or every
Blender-specific feature.

Use scripts/test_simulation_fluid_v5.py under the official CI workflow.
**Do not mark gas/liquid production ready unless both real bakes and
fresh-scene validation pass.** Signed production release remains an
independent blocker.
