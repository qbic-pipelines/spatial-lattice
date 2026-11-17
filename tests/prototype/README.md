# Prototype validation

Run from the repository root. Use the existing `nf-core` conda environment for Nextflow/Java and Docker for image processing. Build the two local images documented in [prototype_subworkflows.md](../../docs/prototype_subworkflows.md) first.

## Unit and complete workflow wiring checks

```bash
python -m unittest discover -s tests/prototype -p 'test_*.py' -v
python tests/prototype/run_stub.py "$(command -v nextflow)"
```

The stub runner creates two ROI rows belonging to the same experiment/sample and exercises both backends with masks/background subtraction on and off, checking two distinct stores and MultiQC. It creates private version-command shims and empty image files under ignored `testing/`. These files are wiring tests, never valid scientific output. No real image processing is performed by this runner.

## Actual RAMI2D and exporter on deterministic synthetic images

```bash
docker run --rm -v "$PWD:/workspace" -w /workspace spatial-lattice/omezarr:rami2d-rfc5-v1 \
  python tests/prototype/make_fixture.py
nextflow -C tests/prototype/rami2d.config run tests/prototype/rami2d.nf \
  --fixture "$PWD/testing/prototype-images" -work-dir testing/prototype-real-work
```

This tests image registration, a moving label mask, absence of moving labels, native transform archiving and validated OME-Zarr output. It uses synthetic image patterns and reference labels, not Cellpose. The fixture is intentionally small. Default output: `testing/prototype-rami2d/`.

## Tissue-derived toy pair

Mount the source OME-Zarr and a new destination directory into the exporter container. For example, with both under the repository's ignored `testing/` directory:

```bash
docker run --rm -v "$PWD:/workspace" -w /workspace spatial-lattice/omezarr:rami2d-rfc5-v1 \
  python tests/prototype/make_tissue_fixture.py testing/source.ome.zarr testing/tissue-inputs
nextflow -C tests/prototype/tissue.config run tests/prototype/tissue.nf \
  --fixture "$PWD/testing/tissue-inputs" --outdir testing/tissue-stainwarpy \
  -work-dir testing/tissue-stain-work
nextflow -C tests/prototype/tissue.config run tests/prototype/tissue.nf \
  --fixture "$PWD/testing/tissue-inputs" --outdir testing/tissue-rami2d \
  --registration_backend rami2d -work-dir testing/tissue-rami-work
```

The generator refuses an existing destination. It extracts a 1024×1024 crop with overlapping tissue signal, resets its origin to local zero and records the source offset/calibration in `fixture.json`. The input MACSima channel order must match the previous four-channel example; the tissue test config explicitly selects DAPI at index 2. Adapt this selection for other sources.

The moving H&E is the previously registered image displaced down 24 and right 32 pixels. A similarly displaced copy of the Cellpose labels serves as a synthetic moving annotation. Neither is new native data or independently segmented H&E. No raw MACSima staging, ASHLAR stitching, or full-size Cellpose run occurs in this test. Baseline alignment errors remain in the crop; success here is not proof of biological registration accuracy.

Inspect `macsima`, `hne_registered` and their labels subgroups in napari. Keep the unshifted `baseline_hne.ome.tif` available to compare recovered geometry. Both resulting artifacts must have the same calibrated image/mask grid, integer labels and native transform provenance. Failure or poor matching should remain visible; no automatic fallback changes the registration scheme.

Use an explicit run name with `-resume <name>` when several test sessions exist, so Nextflow resumes the intended test.

## RAMI2D RFC-5 mapping

Run numerical checks against the pinned Transformix implementation:

```bash
docker run --rm -v "$PWD:/workspace" -w /workspace spatial-lattice/rami2d:1.0.2-f6c4cc0 \
  python tests/prototype/validate_rami2d_rfc5.py /workspace/path/to/transforms.tar
```

The archive argument is optional; without it, four deterministic synthetic chains are checked. Tests include non-commuting compositions, centred rotations, affine shear/reflection, nonzero output origins/indices, anisotropic spacing and rotated direction cosines. All point coordinates passed to Transformix are physical coordinates. The script also checks inverse mapping into the zero-based NGFF output frame.

`compare_rfc5_export.py PREVIOUS_STORE CURRENT_STORE` compares every image/label pyramid array and validates the new scene. For RAMI2D it also checks the persisted RFC-5 affine against the adapter result. Run this in the exporter container with both stores mounted.
