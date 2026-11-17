# Three-subworkflow prototype: implementation review

This branch targets `forward-cycle`. It implements the metro-map grouping while keeping the existing Stainwarpy registration commands and algorithm unchanged. OME vector ROIs are deferred to the [README backlog](../README.md#development-backlog).

## Data flow

`MACSIMA_MCMICRO` → choose `SPATIAL_REGISTRATION_STAINWARPY` (default) or `SPATIAL_REGISTRATION_RAMI2D` → required `BUILD_INTEGRATED_OMEZARR` → MultiQC.

- **MACSIMA_MCMICRO** contains macsima2mc, ASHLAR, optional BACKSUB and the existing MACSIMA_SEGMENTATION subworkflow. It exposes the ASHLAR reference image, segmentation input image, masks and marker sheet. As before, background subtraction changes the segmentation input; registration and export use the ASHLAR image. The example retains Cellpose 3 and its channel-axis setting.
- **SPATIAL_REGISTRATION_STAINWARPY** adapts the existing TIF_REGISTRATION_STAINWARPY subworkflow. Its registration tools, parameters and containers are unchanged. Optional-mask detection now tests for the empty-list sentinel instead of testing whether the mask file is empty.
- **SPATIAL_REGISTRATION_RAMI2D** uses three new modules: RAMI2D_REGISTER_IMAGES, RAMI2D_TRANSFORM_LABELS and RAMI2D_EXPORT_RESULT. Registration produces the registered image and native maps; only associated moving masks go through the transform module. No second image transformation is applied. The inherited RAMI2D wrappers are unused.

Both spatial integration subworkflows take `[meta, fixed, moving, moving_mask_or_empty_list]` and emit:

```text
[meta + registration_backend, fixed, native_moving, registered_moving,
 registered_moving_mask_or_empty_list, native_transform_asset, backend_metrics_json]
```

The tuple and reference-grid semantics are shared; native transform encoding and diagnostic JSON remain backend-specific. Stainwarpy emits its NPY matrix and metrics. RAMI2D emits a TAR archive with ordered ITK/Elastix parameter files and log, plus a versioned JSON record of parameters, file checksums, direction and unassessed alignment quality. The RAMI2D archive retains the `registration/qc/fullres_trf/` directory layout so relative initialization-map links remain valid after extraction. The exporter archives both backends' native assets in `provenance/`.

Pairing uses experiment, sample, rack, well and ROI. A moving image may be reused across acquisition exposures. Duplicate or missing pairing keys and duplicate acquisition IDs fail explicitly. File IDs now encode all five identity fields with length prefixes, so ROIs from one experiment cannot overwrite one another. This changes output filenames compared with the earlier experiment-only ID.

## Scope and migration

- The backend subworkflows are named `SPATIAL_REGISTRATION_STAINWARPY` and `SPATIAL_REGISTRATION_RAMI2D`, under `subworkflows/local/spatial_registration_*`. Update any external selectors that include the old fully qualified process names. The renamed process scopes can invalidate cached registration tasks on resume; tool commands and registration settings are unchanged.

- Use `--registration_backend stainwarpy` or `--registration_backend rami2d`. Legacy `--stainwarpy` and `--rami2d` flags are rejected with a migration message. The solidfox example parameter file is updated.
- OME-Zarr is mandatory. `--integrated_omezarr false` is rejected; it is no longer an optional path.
- This integrated prototype currently requires a per-ROI samplesheet, H&E for every pair, the MACSima fixed/final grid and `--segmentation cellpose3`. Project-folder mode and other segmentation choices remain outside this prototype entry point.
- Optional H&E masks come from `--stainsegmy`. They are transformed using the selected backend and exported under `hne_registered/labels/segmentation`. Cellpose labels remain under `macsima/labels/cellpose`.
- Rigid RAMI2D is the default (`--rami2d_scheme 1`); rigid then affine is available with `2`. Nonlinear schemes, vector annotations and arbitrary additional modalities are deferred.
- RAMI2D requires explicit positive `rami2d_mpp_fix` and `rami2d_mpp_mov`, checked against isotropic OME calibration. Choose the actual DAPI index with `rami2d_ifix`; moving reference defaults to hematoxylin (`rami2d_imov: h`). Keypoint initialization is controlled by `rami2d_initial_alignment`; failure does not silently trigger a different registration strategy.

## Docker setup

Build these local images from the repository root on the machine that will execute Nextflow:

```bash
docker build -f modules/local/rami2d/Dockerfile -t spatial-lattice/rami2d:1.0.2-f6c4cc0 .
docker build -f modules/local/integrated_omezarr/Dockerfile -t spatial-lattice/omezarr:rami2d-rfc5-v1 .
```

These are local build tags, **not published registry images**. The RAMI2D Dockerfile pins the upstream source commit `f6c4cc0f48dbd86b866ade8d3bf67177dd45712f` (version 1.0.2). Upstream pins its direct dependencies; transitive dependencies and the base tag are not a complete reproducibility lock. Record built image digests for deployment. The exporter retains its existing pinned Python requirements. Existing processing modules retain their own containers. Stainwarpy's existing container is amd64 and runs under Docker emulation on Apple Silicon.

Example parameters for the alternative backend (use actual measured input calibration):

```json
{
  "registration_backend": "rami2d",
  "segmentation": "cellpose3",
  "rami2d_mpp_fix": 0.17,
  "rami2d_mpp_mov": 0.5023,
  "rami2d_ifix": 2,
  "rami2d_imov": "h",
  "rami2d_mpp_reg": 1,
  "rami2d_mpp_key": 1,
  "rami2d_scheme": 1,
  "rami2d_initial_alignment": true
}
```

```bash
nextflow run . -profile docker --input samplesheet.csv --outdir results/prototype -params-file params.json
```

The example channel and calibration values are illustrative, not universal defaults.

## Transform metadata limits

The existing Stainwarpy NGFF affine adapter is retained. RAMI2D linear transform chains now produce an RFC-5 edge from native H&E physical coordinates to the calibrated MACSima reference. The Python adapter resolves the saved chain, handles transform centres and output-grid geometry, inverts the resampling map and converts XY to YX. Native parameter files remain archived. See [rami2d_rfc5.md](rami2d_rfc5.md) for the mathematical convention and Transformix validation.

Nonlinear transforms and additive composition are rejected rather than approximated. This adapter is scoped to the pinned RAMI2D 1.0.2 image-coordinate conventions. Already-registered images and masks keep their reference-grid mapping; their registration is not applied twice.

Schema/grid validation and successful process exit do not establish biological alignment. RAMI2D provenance records `alignment_quality: not_assessed`. Float32 spectral data, nonlinear transforms and real MSI data are not validated by this prototype.

## Validation and local review data

See [test commands](../tests/prototype/README.md). Full workflow stubs exercise two ROIs, both backends, moving masks present/absent and background subtraction on/off through MultiQC. Small Docker tests exercise actual registration, label transformation and OME-Zarr writing. A tissue fixture can be derived from the previously downloaded artifact without modifying it.

The tissue fixture uses a 1024-pixel crop, retained Cellpose labels and registered H&E displaced by a known translation. It preserves source crop offsets and test geometry in `fixture.json`. Its moving labels are synthetic annotations, not independently segmented H&E. It tests recovery relative to an existing alignment, not independent biological ground truth. Raw MACSima cycle processing and full-size Cellpose are not validated by that fixture. A full original-data rerun remains necessary when solidfox or the original inputs are available.

## Results of local validation (2026-11-17)

- Both Docker images built; the actual RAMI2D CLI reports 1.0.2.
- Four adapter unit tests passed (calibration, channel selection, transform packaging and missing-transform failure).
- Four complete workflow stub cases passed: Stainwarpy/RAMI2D × moving masks absent/present, each with two distinct ROIs and MultiQC. Parameter-schema validation is enabled.
- Nextflow 26.04.6 lint reported no errors in the tested workflow/module dependency graph. Style warnings remain, including unused tuple fields and inherited warnings.
- Actual RAMI2D registration and export completed on 256×256 synthetic images, with and without moving labels. The mask-present case retained all 55 label IDs and had foreground Dice 1.0 against its synthetic reference mask.
- Both backends completed on the 1024×1024 tissue-derived toy. Schema/grid validation passed; reference pixels and 656 Cellpose label IDs were unchanged; transformed masks introduced no new IDs.

Diagnostic tissue-toy results (no acceptance threshold or biological accuracy claim):

| Diagnostic | Stainwarpy | RAMI2D |
| --- | --- | --- |
| H&E mean absolute difference from the unshifted baseline, before registration | 30.018 | 30.018 |
| H&E mean absolute difference after registration | 20.481 | 20.300 |
| Synthetic moving-label foreground Dice against reference labels | 0.628 | 0.631 |

Image differences use the inner crop excluding 40-pixel borders. These values show partial recovery, not exact displacement recovery. The source H&E was already registered and may retain baseline misalignment. Neither tool was optimized or modified to improve these scores. Visual review remains necessary.

Not tested: original raw-cycle processing, full-size segmentation, real MSI/float32 data, nonlinear registration. The rigid-plus-affine option is wired to upstream but the local registration tests used rigid mode.

## References

- [RAMI2D source pinned for this implementation](https://github.com/VictorDidier/RAMI2D/tree/f6c4cc0f48dbd86b866ade8d3bf67177dd45712f).
- [RAMI2D H&E example](https://github.com/VictorDidier/RAMI2D/blob/f6c4cc0f48dbd86b866ade8d3bf67177dd45712f/examples/imf_he.sh).
- [NGFF RFC-5](https://ngff.openmicroscopy.org/rfc/5/).
- [Original design and Myocarditis lessons](rami2d_prototype.md).
