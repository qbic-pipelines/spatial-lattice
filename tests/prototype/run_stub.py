#!/usr/bin/env python3
"""Exercise the complete workflow with two ROIs and stub tools, never real images.

Usage: python tests/prototype/run_stub.py /absolute/path/to/nextflow
Requires Java and the pipeline's nf-schema plugin. Version shims are private to
these stub runs; no registration/segmentation accuracy is claimed.
"""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

repo = Path(__file__).resolve().parents[2]
root = repo / 'testing' / 'prototype-stubs'
root.mkdir(parents=True, exist_ok=True)
shims = root / 'shims'
shims.mkdir(exist_ok=True)
for tool in ('python', 'ashlar', 'backsub', 'cellpose', 'stainwarpy', 'stainsegmy', 'rami2d-register', 'rami2d-transform', 'multiqc'):
    script = shims / tool
    script.write_text('#!/bin/sh\necho "Version: stub-only"\necho "cellpose version: stub-only"\n')
    script.chmod(0o755)
rows = []
for index in range(2):
    raw = root / f'raw{index}'
    raw.mkdir(exist_ok=True)
    he = root / f'he{index}.ome.tif'
    he.touch()
    rows.append(['experiment', 'sample', 'rack', 'well', f'ROI{index}', str(raw), str(he)])
sheet = root / 'samplesheet.csv'
with sheet.open('w') as handle:
    writer = csv.writer(handle)
    writer.writerow(['experiment','sample','rack','well','roi','raw_images_ROI','HnE_ROI'])
    writer.writerows(rows)
env = dict(os.environ, PATH=str(shims) + os.pathsep + os.environ['PATH'])
for backend, masks in [('stainwarpy', False), ('stainwarpy', True), ('rami2d', False), ('rami2d', True)]:
    name = f'{backend}-masks-{masks}'
    output = root / name
    parameters = root / f'{name}.json'
    parameters.write_text(json.dumps(dict(input=str(sheet), outdir=str(output), registration_backend=backend, stainsegmy=masks, background_subtraction=masks)))
    command = [sys.argv[1], 'run', str(repo), '-stub-run', '-ansi-log', 'false',
        '-c', str(repo/'tests/prototype/stub.config'), '-work-dir', str(root/'work'/name),
        '-params-file', str(parameters)]
    with (root/f'{name}.log').open('w') as log:
        result = subprocess.run(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError((root/f'{name}.log').read_text())
    stores = list(output.rglob('*.ome.zarr'))
    assert len(stores) == 2, (name, stores)
    assert len({s.name for s in stores}) == 2, 'ROI outputs collided'
    assert list(output.rglob('*multiqc_report.html')), 'MultiQC did not complete'
    print(f'PASS {name}: two distinct stores and MultiQC', flush=True)
