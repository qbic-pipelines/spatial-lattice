# RAMI2D alternative: first-prototype design

> Implementation review: see [prototype_subworkflows.md](prototype_subworkflows.md) for the current code, commands, tests and limitations. The design below records the broader target, not a claim that every feature is implemented. The new RAMI2D modules are built from scratch; vector OME ROIs remain deferred.


Design proposal only. The metro map now shows mutually exclusive Stainwarpy (default) and RAMI2D routes. Both converge on mandatory BUILD_INTEGRATED_OMEZARR. No runtime changes or registration experiments are part of this documentation update.

## Proposed subworkflow

`REGISTRATION_RAMI2D`: validate pair and calibration → RAMI2D_REGISTER → RAMI2D_TRANSFORM for associated data when present → normalize and validate the registration-result bundle.

Build new register, label-transform and result-export modules; leave the inherited wrappers unused. RAMI2D_REGISTER already creates the registered moving image, so do not transform that image a second time. RAMI2D_TRANSFORM applies the saved maps to additional moving-space images or labels. If no associated data exist, the subworkflow still emits the registered image and its transforms.

Proposed selection: one `registration_backend` value (`stainwarpy` or `rami2d`), rather than two independently enabled backend flags. This is a proposed interface, not an implemented command-line parameter.

Inputs should be per-pair tuples containing stable sample/ROI/section identifiers, fixed and moving paths, selected registration channels, physical calibration, source offsets and optional associated data. Pair identity and section identity must remain distinct. Registration channels are estimation inputs; retain all measurement channels in outputs/native data.

## Starting settings and project lessons

The reviewed Myocarditis project discussion reports that H&E-to-DAPI rigid registration succeeded at overview level after FoxP3-based keypoint matching failed. Automatic MSI registration remained unresolved. These observations motivate the following design; they are not new validation results for this pipeline:

- Start H&E → MACSima with hematoxylin and an explicitly identified DAPI channel. Do not assume channel zero is the desired DAPI acquisition.
- Use a rigid scheme first; expose rigid-plus-affine as an alternative. Initial candidate registration/keypoint spacing is 1 µm for that H&E/DAPI case, subject to the actual image calibration and quality checks.
- Enable keypoint initialization only as an explicit setting. Missing/insufficient matches must produce a visible failed registration status, not silently trigger a different algorithm and mark the result accepted.
- Treat alignment QC separately from successful process exit and file validation. Preserve previews, logs, match counts if available, and review status.
- Keep MSI spectra at native resolution, with separate registered display images. Preserve validity masks, spectral identities and pixel-coordinate offsets. Do not expand every spectral channel onto a microscopy-resolution grid.
- Preserve provisional calibration as an explicit assumption. Manual mappings remain separately labelled references and must not be presented as accepted automatic registration or independent ground truth.
- Exercise float32 spectral-image export explicitly: the project reported a writing failure in that path. Do not silently quantize spectra to work around it.

Project-specific source files, transform maps and exact container digest cannot be rechecked while solidfox is offline. The shared project discussion was reviewed; no remote execution was performed.

## Common output and transformation adapter

Both backends emit the layout in [prototype_registration.md](prototype_registration.md): registered images, optional labels, reference grid, versioned manifest, transforms and provenance. Add explicit `registration_status`, `calibration_status`, and `transform_export_status` fields to the proposed manifest.

Retain RAMI2D's ordered native parameter files from `qc/fullres_trf`, including referenced initialization maps. The adapter must interpret transform centers, composition order, image direction/origin/spacing, flips, crop offsets and coordinate conventions. Do not flatten parameter vectors into a matrix without resolving those semantics.

Distinguish the mapping used for resampling from a forward mapping of moving points into the reference. Validate transform direction against ITK/Transformix on synthetic points and image landmarks; do not assume a file named “transform” is a forward map. Export a forward affine only after its direction and composition are verified. Preserve the native representation regardless.

The project review artifact retained the native H&E chain as provenance rather than RFC-5 edges. Closing that gap is a required acceptance criterion for this adapter. Already-resampled images map by their output grid; the original transform chain records how they were produced and must not be applied again.

Deformable registration is a later increment: preserve the full nonlinear map, domain and units and validate its OME-NGFF representation. A B-spline result must never be replaced by an affine approximation presented as equivalent. Do not claim completed spatial integration when a required mapping is unrepresented.

## Existing wrapper corrections required before implementation

- `RAMI2D_TRANSFORM` declares staged image/map inputs but currently executes using global input/map-path parameters. Wire the staged values through the subworkflow.
- Replace placeholder TIFF/BAM stubs with realistic output-directory structures matching each process declaration.
- Verify supported CLI options against the pinned container: the current transform wrapper adds `-@`, which is absent from the reviewed upstream argument parser.
- Emit explicit image, transform-directory, QC and version channels instead of relying on downstream filename guesses.
- Keep Docker execution. Resolve the existing Wave image to a digest and record the installed RAMI2D version; do not silently substitute a newer release during adapter validation.

## Acceptance tests and implementation order

1. Correct wrappers and validate container CLI/stubs on small inputs.
2. Test rigid and affine transforms with known rotation, translation, scale and off-center rotation; check axis order, crop offsets, unequal pixel sizes and transform composition.
3. Check associated label IDs and nearest-neighbor interpolation, absent labels, float32 data and validity masks.
4. Verify both backends emit the same manifest schema; use at least two ROIs to detect mismatched joins.
5. Test the H&E/DAPI example, inspect overlays, and compare exported coordinates with native transforms.
6. Feed the validated bundle into OME-Zarr, validate RFC-5 edges and reference-grid relationships, and report outcomes in MultiQC.
7. Add deformable and spatial-omics cases only after the linear contract is established.

## Sources reviewed

- [RAMI2D documentation](https://github.com/VictorDidier/RAMI2D/blob/main/README.md): schemes, registration and associated-image transformation.
- [Official H&E/fluorescence example](https://github.com/VictorDidier/RAMI2D/blob/main/examples/imf_he.sh): channel selection, transform directory and label flag.
- [Registration CLI](https://github.com/VictorDidier/RAMI2D/blob/main/src/rami2d/register.py), [transformation CLI](https://github.com/VictorDidier/RAMI2D/blob/main/src/rami2d/transform.py), [registration utilities](https://github.com/VictorDidier/RAMI2D/blob/main/src/rami2d/utils_reg.py).
- Existing [register wrapper](../modules/local/rami2d/register/main.nf) and [transform wrapper](../modules/local/rami2d/transform/main.nf).

Upstream sources were reviewed on 2026-11-16. This proposal does not assert that upstream main matches the existing container.
