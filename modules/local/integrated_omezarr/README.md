# Multi-modal OME-Zarr Integration

**Exporting OME-Zarr and SpatialData artifacts** describes the intended integration stage. This module currently exports **OME-Zarr only**; SpatialData serialization remains planned.

`INTEGRATED_OMEZARR` is called by the required `BUILD_INTEGRATED_OMEZARR` subworkflow before MultiQC. It uses ngff-zarr 0.52.0 to write an NGFF 0.6/RFC-5 scene. Viewer support for scene transforms varies.

## Inputs and processing

- One stitched MACSima reference image, its Cellpose 3 mask and marker sheet.
- Native H&E for calibration/provenance, registered H&E and an optional already-transformed H&E mask.
- Native transformation assets and metrics from either Stainwarpy or RAMI2D.

`bin/integrate_omezarr.py` validates calibration and reference-grid shapes, preserves full-resolution image/label pixels, writes four pyramid levels and records coordinate mappings. Images use Gaussian pyramid downsampling; labels use nearest-neighbour downsampling. Image arrays are CYX and labels YX; physical spatial axes use micrometres.

The existing Stainwarpy adapter and `bin/rami2d_rfc5.py` normalize supported linear native-to-reference mappings. Registered H&E and its transformed labels are already on the reference grid: this module does not register or resample them again. MACSima Cellpose labels remain in their original reference frame.

Source OME XML, marker names, checksums, software versions, native transforms and metrics are preserved. The store records the native H&E coordinate relationship but does not include a native H&E pixel array. Per-cycle/tile ASHLAR transforms are not exported; the final mosaic calibration is retained. Nonlinear mappings and anisotropic calibration are unsupported.

## Outputs and validation

- `<acquisition_id>.ome.zarr`: images, associated labels, coordinate transformations and provenance.
- `integrated_omezarr_mqc.json`: scene read-back and grid-validation results for MultiQC.
- Software-version topic entry.

There is currently no SpatialData output. Full-data H&E segmentation/moving-mask tests and future spatial-object support are tracked in the [README backlog](../../../README.md#development-backlog).

See the [integration guide](../../../docs/integrated_omezarr.md) for artifact layout, container setup, calibration and viewing, and [prototype tests](../../../tests/prototype/README.md) for validation commands.
