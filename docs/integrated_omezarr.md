# Multi-modal OME-Zarr Integration

**Exporting OME-Zarr and SpatialData artifacts** is the intended scope of this stage. The current implementation exports OME-Zarr only; SpatialData serialization is planned. The implementation identifiers remain `BUILD_INTEGRATED_OMEZARR` (subworkflow) and `INTEGRATED_OMEZARR` (module).

`BUILD_INTEGRATED_OMEZARR` is required in the integrated prototype and runs before MultiQC. It combines the stitched MACSima reference image, its Cellpose 3 mask, registered H&E and an optional transformed moving mask. The registration backend is selected with `registration_backend`; Stainwarpy is the default and RAMI2D is the alternative.

## Subworkflow and module responsibilities

1. `BUILD_INTEGRATED_OMEZARR` receives each acquisition's matched reference image, Cellpose mask, native/registered H&E, optional transformed moving mask, transforms, metrics and marker sheet.
2. `INTEGRATED_OMEZARR` invokes `bin/integrate_omezarr.py` to check array geometry and calibration, build the image/label pyramids and construct the NGFF scene. The RAMI2D adapter in `bin/rami2d_rfc5.py` maps supported native linear chains into the common reference coordinate system.
3. The module writes one OME-Zarr store, retains source and registration provenance, and validates the stored scene before emitting its QC JSON. MultiQC consumes that QC output.
4. A future SpatialData export will reuse the integrated data and coordinate relationships. It is not an additional registration step and is not currently emitted.

## Setup and execution

Build the exporter from the repository root:

```bash
docker build -t spatial-lattice/omezarr:rami2d-rfc5-v1 -f modules/local/integrated_omezarr/Dockerfile .
nextflow run . -profile docker --input samplesheet.csv --outdir results/example
```

For RAMI2D, also build its local image and provide measured calibration and channel settings as described in [prototype_subworkflows.md](prototype_subworkflows.md). The solidfox parameter file is an example containing machine-specific paths; it is not a portable test dataset. Both local container tags must be built on the execution host. Rebuilding a mutable tag alone does not invalidate Nextflow task caches.

The integrated entry point requires per-ROI MACSima/H&E pairs, `segmentation: cellpose3`, and the MACSima fixed/final grid. `integrated_omezarr: false`, project-folder mode and legacy backend booleans are rejected.

## Artifact layout

Each acquisition produces `<acquisition_id>.ome.zarr`:

| Group | Contents |
| --- | --- |
| `macsima` | ASHLAR reference image, with marker names |
| `macsima/labels/cellpose` | Reference Cellpose labels; not transformed |
| `hne_registered` | RGB H&E resampled onto the reference grid |
| `hne_registered/labels/segmentation` | Optional moving labels transformed by the chosen backend |
| `provenance/` | Native registration transforms and metrics; RAMI2D's resolved RFC-5 mapping JSON |

Four pyramid levels are written. Image pyramids use Gaussian downsampling and labels use nearest-neighbour downsampling. Physical calibration comes from the source OME metadata; image and label grids are checked before export. Source checksums, original OME XML, marker information and software versions are retained in root provenance metadata.

In the tissue toy, the moving `segmentation` layer is a deliberately shifted copy of the reference labels, not an independent H&E segmentation. Use `cellpose` for the original MACSima cell annotations.

## Coordinates and validation

The artifact uses the pinned NGFF 0.6/RFC-5 implementation. Scene metadata is stored under `ome.scene` in the root `zarr.json`; affine values are stored as referenced Zarr arrays. Image-level multiscale metadata supplies pixel calibration. Already-registered images and labels share `macsima_physical` without applying registration twice.

Stainwarpy retains its existing affine adapter. RAMI2D's linear chain is converted to a native-H&E-to-MACSima mapping, including pre-resize geometry, centres, composition, inversion and axis ordering. See [rami2d_rfc5.md](rami2d_rfc5.md). Nonlinear mappings are not supported.

The exporter requires isotropic OME calibration and matching reference-grid shapes. Schema/read-back checks produce `integrated_omezarr_mqc.json` for MultiQC. Valid metadata and successful execution do not certify biological registration accuracy.

## Viewing

In the tested `napari-ome-zarr` environment, open the image subgroups rather than the scene root to avoid the reader's path-form transformation limitation:

```bash
napari --plugin napari-ome-zarr example.ome.zarr/macsima example.ome.zarr/hne_registered
```

H&E channels represent RGB. Labels are associated with their image groups. See [test instructions](../tests/prototype/README.md) for generating a local toy example; both backends have also completed full original-ROI runs on solidfox. Those runs disabled H&E segmentation, so full-data moving-mask validation remains pending.
