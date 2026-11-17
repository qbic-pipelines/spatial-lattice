> Development branch: for the integrated prototype, use the [current README](../README.md), [implementation notes](prototype_subworkflows.md) and [OME-Zarr output guide](integrated_omezarr.md). Legacy options described below may not apply to this entry point.

# nf-core/spatiallattice: Output

## Introduction

This document describes the output produced by the pipeline. Most of the plots are taken from the MultiQC report, which summarises results at the end of the pipeline.

The directories listed below will be created in the results directory after the pipeline has finished. All paths are relative to the top-level results directory.

## Pipeline overview

The pipeline is built using [Nextflow](https://www.nextflow.io/) and processes data using the following steps:

- [macsima2mc](#macsima2mc) - Stage raw MACSima tiles into the MCMICRO format
- [ASHLAR](#ashlar) - Stitch and register the multiplexed images
- [BackSub](#backsub) - Subtract background signal (optional)
- [MACSima segmentation](#macsima-segmentation) - Segment macsima images
- [StainSegMy](#stainsegmy) - H&E tissue segmentation (optional)
- [MultiQC](#multiqc) - Aggregate report describing results and QC from the whole pipeline
- [Pipeline information](#pipeline-information) - Report metrics generated during the workflow execution

### macsima2mc

<details markdown="1">
<summary>Output files</summary>

- `macsima2mc/`
  - `<experiment>/`
    - `<rack>_<well>_<roi>/`
      - `<acquisition_group>/`
        - `markers.csv`: Marker table with channel names, exposure times and background information.
        - `raw/`: Directory containing the staged raw `*.ome.tiff` files.

</details>

[macsima2mc](https://github.com/SchapiroLabor/macsima2mc) is a staging module for MCMICRO that transforms MACSima data sets so they can be registered with ASHLAR. It converts the raw MACSima tiles into the MCMICRO directory structure, generating a `markers.csv` table and the raw `*.ome.tiff` files used by the downstream steps. Each acquisition group is named after its position and exposure, for example `rack-01-well-C01-roi-001-exp-1`.

### ASHLAR

<details markdown="1">
<summary>Output files</summary>

- `ashlar/`
  - `<experiment>/`
    - `<rack>_<well>_<roi>_exp<exposure>.ome.tif`: Stitched and registered pyramidal OME-TIFF image.

</details>

[ASHLAR](https://github.com/labsyspharm/ashlar) stitches and registers the multiplexed images produced by the staging step. It aligns the individual tiles and cycles into a single, registered whole-slide image. One image is produced per acquisition group, named after the rack, well, ROI and exposure (for example `R1_A1_ROI1_exp1.ome.tif`).

### BackSub

<details markdown="1">
<summary>Output files</summary>

- `backsub/`
  - `<experiment>/`
    - `<rack>_<well>_<roi>_exp<exposure>_backsub.ome.tif`: Background corrected pyramidal OME-TIFF image.
    - `<rack>_<well>_<roi>_exp<exposure>_backsub.csv`: Marker table adjusted to match the background corrected image.

</details>

[BackSub](https://github.com/SchapiroLabor/Background_subtraction) performs pixel-by-pixel channel subtraction to remove background signal from the stitched and registered images. This step is optional and only runs when `--background_subtraction` is set (enabled by default).

### MACSima segmentation

<details markdown="1">
<summary>Output files</summary>

- `segmentation/cellpose3/<experiment>/<sample>/`
  - `*_cp_masks.tif`: Labelled segmentation masks from Cellpose 3.
  - `*_flows.tif`: Cellpose flows (only with `--cellpose3_save_flows`).
- `segmentation/cellpose4/<experiment>/<sample>/<id>/`
  - `*_cp_masks.tif`: Labelled segmentation masks from Cellpose 4 (Cellpose-SAM).
- `segmentation/mesmer/<experiment>/<sample>/`
  - `*_mesmer_mask.tif`: Labelled segmentation masks from [Mesmer](https://github.com/vanvalenlab/deepcell-tf).

</details>

The stitched MACSima image (or the background-subtracted image if `--background_subtraction` is set) is segmented with the tools selected via `--segmentation`, a comma-separated list of `cellpose3`, `cellpose4` and `mesmer` (default: `cellpose4`). Several tools can be run in parallel, e.g. `--segmentation cellpose4,mesmer`.

### StainSegMy

<details markdown="1">
<summary>Output files</summary>

- `stainsegmy/`
  - `*.ome.tif`: H&E tissue segmentation masks.

</details>

StainSegMy performs tissue segmentation on the H&E stained images. This step is optional and only runs when `--stainsegmy` is set (disabled by default).

### MultiQC

<details markdown="1">
<summary>Output files</summary>

- `multiqc/`
  - `multiqc_report.html`: a standalone HTML file that can be viewed in your web browser.
  - `multiqc_data/`: directory containing parsed statistics from the different tools used in the pipeline.
  - `multiqc_plots/`: directory containing static images from the report in various formats.

</details>

[MultiQC](http://multiqc.info) is a visualization tool that generates a single HTML report summarising all samples in your project. Most of the pipeline QC results are visualised in the report and further statistics are available in the report data directory.

Results generated by MultiQC collate pipeline QC from supported tools. The pipeline has special steps which also allow the software versions to be reported in the MultiQC output for future traceability. For more information about how to use MultiQC reports, see <http://multiqc.info>.

### Pipeline information

<details markdown="1">
<summary>Output files</summary>

- `pipeline_info/`
  - Reports generated by Nextflow: `execution_report.html`, `execution_timeline.html`, `execution_trace.txt` and `pipeline_dag.dot`/`pipeline_dag.svg`.
  - Reports generated by the pipeline: `pipeline_report.html`, `pipeline_report.txt` and `software_versions.yml`. The `pipeline_report*` files will only be present if the `--email` / `--email_on_fail` parameter's are used when running the pipeline.
  - Reformatted samplesheet files used as input to the pipeline: `samplesheet.valid.csv`.
  - Parameters used by the pipeline run: `params.json`.

</details>

[Nextflow](https://www.nextflow.io/docs/latest/tracing.html) provides excellent functionality for generating various reports relevant to the running and execution of the pipeline. This will allow you to troubleshoot errors with the running of the pipeline, and also provide you with other information such as launch commands, run times and resource usage.

## Integrated OME-Zarr

See the [integration guide](integrated_omezarr.md) for setup, output layout, coordinate conventions, validation and limitations. Artifacts are published under `integrated/<acquisition_id>.ome.zarr`.
