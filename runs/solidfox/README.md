# Solidfox MACSima + H&E run

Run on solidfox:

```bash
cd /home/ubuntu/projects/spatial_lattice
./runs/solidfox/run.sh
```

The launcher activates the existing nf-core Conda environment and uses Docker.
The CSV references the original raw MACSima ROI and H&E OME-TIFF under
/home/ubuntu/Caro; image data have not been copied.

params.json preserves the previous run's processing choices, including
Stainwarpy with the multiplexed fixed image and output size, high-exposure
acquisitions, and Cellpose-SAM. This branch replaces cellpose_sam=true with
segmentation=cellpose3, cellpose3_pretrained_model=nuclei, diameter=17 and flow_threshold=0.4.
Cellpose 3 uses 6 CPUs and 36 GB, matching the original successful full-mosaic run.
Background subtraction, H&E segmentation and RAMI2D remain disabled.
Boolean parameters are supplied as JSON because the bare --stainwarpy flag
failed Boolean validation in the installed Nextflow 26.04.6 environment.

Outputs: /home/ubuntu/projects/spatial_lattice/results/solidfox
Work/cache: /home/ubuntu/projects/spatial_lattice/work and .nextflow
-resume reuses this checkout's compatible cached runs; the first run here
does not reuse /home/ubuntu/Caro's cache.

Source setup: /home/ubuntu/Caro, run lonely_raman.
Source checkout commit: 4377b321139210efb769de6a666cace50fccf69c
New checkout baseline: 69ece96b10a3b8d5226498a3b0a91d0c693cdb63 (forward-cycle).
The source run's Stainwarpy registration exited successfully.
This new branch has not yet been run end-to-end.

The single-ROI samplesheet metadata are preserved verbatim. Before adding
multiple ROIs, review the registration joins that currently use meta.project,
which the per-ROI input schema does not supply.
