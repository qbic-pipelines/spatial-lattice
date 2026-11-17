#!/usr/bin/env bash
set -e
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
conda activate nf-core
set -uo pipefail
cd /home/ubuntu/projects/spatial_lattice
exec nextflow run . \
  -profile docker \
  -c runs/solidfox/nextflow.config \
  -params-file runs/solidfox/params.json \
  -resume -ansi-log false "$@"
