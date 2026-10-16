# Creative Studio registered for THETECHGUY Software Builder

**Identity:** `ttg-creative-studio` — Builder's single immutable App Lifecycle identity.

The `techguy-build.json` in this repository was initialized and normalized
using the *existing* Builder's `app.services.app_lifecycle.ensure_lifecycle`
and `app.services.app_setup.save_app_setup` APIs, not a new builder.

The project remains independent and offline-capable. Windows and Linux are
selected. The Builder's GitHub distribution provider points to
`jaydumisuni/ttg-creative-studio`. Storefront, automatic updates, account
requirements and public publication remain off until the product is qualified
and the owner deliberately releases it.

## Required Builder release gates

The manifest requires THETECHGUY's own custom graphical installer, registered
uninstall and **actual production code signing**. These requirements cannot
be waived simply by passing the current GitHub source/build tests.

The existing Builder's `ReleaseReadinessEvaluator` ran against this exact
project under an *isolated temporary app registry* on KRATOS. It recognized
`ttg-creative-studio` in testing state and correctly returned **NO-GO** for
release mode with these distinct outstanding proofs:

1. Verified application build readback
2. Builder custom graphical installer qualification
3. Production hardening evidence
4. Genuine installer Authenticode signing

This is not a claim that the Builder itself must be redeveloped. Existing
Builder features own these gates. The standalone native Studio installer
is an engineering candidate until Builder accepts it under its own authority.

## Using the existing Builder

In Builder, select the **canonical** Creative Studio project directory,
not a copy of source inside Builder. The machine-local App Registry should
register the project as `ttg-creative-studio`, and Builder can retain
that external path. It must not create a second app identity or move project
files into Builder.

Use Builder's graphical installer, signing configuration and
`Release Control -> GitHub` publishing after all qualification gates are
green. Do not upload an unsigned candidate as a signed production release.
The signing certificate and private key are *not* part of source control.

This project is at stage `testing` with `public=false`; it is not live.
The Builder's release gate remains the release authority.

## Verification

From the Creative Studio root:

```bash
python -B scripts/test_builder_manifest.py
```

On a machine with THETECHGUY Software Builder, use its own app registry,
`ReleaseReadinessEvaluator(...).evaluate(project, mode="release")` and
completion authority to audit the final candidate.

ATHENA's `D:\projects\TTG-Creative-Studio` and its separate Builder path
are currently blocked by Oracle's approved-root enforcement. No alternate
project root should be used to evade that refusal. KRATOS can validate the
Builder manifest; actual ATHENA app installation still requires admitted
Oracle execution on the approved original project path.

## Unresolved production dependencies

- Legitimate company code-signing identity, certificate and signing tools
- Approved ATHENA workspace for Builder's Windows installer/GUI acceptance
- Local GPU image-inference runtime and installed diffusion checkpoint;
  network fixture tests do not count as actual model-backed generation
- Final owner acceptance of visual quality and signed public release

No Ptah changes, bypassed system permissions or invented certificates.
