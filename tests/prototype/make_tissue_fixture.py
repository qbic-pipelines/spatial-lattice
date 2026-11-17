"""Derive a small test pair from an existing integrated OME-Zarr.

This reuses registered H&E and Cellpose labels. Its known displacement is test
geometry, not a new independent biological registration ground truth.
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import tifffile
import zarr

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source')
parser.add_argument('output')
parser.add_argument('--size', type=int, default=1024)
a = parser.parse_args()
out = Path(a.output)
out.mkdir(parents=True, exist_ok=False)
root = zarr.open_group(a.source, mode='r')
def level(group, index):
    item = root[group]
    path = item.attrs['ome']['multiscales'][0]['datasets'][index]['path']
    return item[path]
# Pick a tissue-rich location with overlapping H&E signal, using the coarse level.
coarse_labels = level('macsima/labels/cellpose', 3)[:]
coarse_he = level('hne_registered', 3)[:]
size = a.size
h, w = level('macsima/labels/cellpose', 0).shape
best = None
for cy in range(size//2, h-size//2+1, size//2):
    for cx in range(size//2, w-size//2+1, size//2):
        ys = slice((cy-size//2)//8, (cy+size//2)//8)
        xs = slice((cx-size//2)//8, (cx+size//2)//8)
        tissue = coarse_he[:,ys,xs].mean(axis=0)
        score = np.count_nonzero((coarse_labels[ys,xs]>0)&(tissue>15)&(tissue<235))
        if best is None or score > best[0]: best = (score, cy-size//2, cx-size//2)
if best is None: raise ValueError('Source smaller than crop')
_, y0, x0 = best
mac = level('macsima',0)[:,y0:y0+size,x0:x0+size]
he = level('hne_registered',0)[:,y0:y0+size,x0:x0+size]
mask = level('macsima/labels/cellpose',0)[y0:y0+size,x0:x0+size]
scale = root['macsima'].attrs['ome']['multiscales'][0]['datasets'][0]['coordinateTransformations'][0]['transformations'][0]['scale'][-2:]
if not np.allclose(scale, scale[0]): raise ValueError('Toy expects isotropic calibration')
meta = dict(PhysicalSizeX=scale[1],PhysicalSizeY=scale[0],PhysicalSizeXUnit='µm',PhysicalSizeYUnit='µm')
def write(name, data, axes, rgb=False):
    tifffile.imwrite(out/name, data, metadata=dict(meta,axes=axes), photometric='rgb' if rgb else 'minisblack', compression='zlib')
dy, dx = 24, 32
moving = np.full_like(he, np.iinfo(he.dtype).max)
moving[:,dy:,dx:] = he[:,:-dy,:-dx]
moving_labels = np.zeros_like(mask)
moving_labels[dy:,dx:] = mask[:-dy,:-dx]
write('fixed.ome.tif',mac,'CYX')
write('moving.ome.tif',moving.transpose(1,2,0),'YXS',True)
write('baseline_hne.ome.tif',he.transpose(1,2,0),'YXS',True)
write('mask.tif',mask,'YX')
write('moving_mask.tif',moving_labels,'YX')
markers = root.attrs['spatial_lattice']['markers']
with (out/'markers.csv').open('w') as handle:
    writer=csv.DictWriter(handle,fieldnames=list(markers[0])); writer.writeheader();writer.writerows(markers)
manifest = {
    'source_artifact':Path(a.source).name,'source_crop_origin_yx':[y0,x0],
    'shape_yx':list(mask.shape),'spacing_yx_um':scale,
    'synthetic_displacement_yx_pixels':[dy,dx],
    'moving_to_baseline_affine_xy':[[1,0,-dx],[0,1,-dy],[0,0,1]],
    'reference_mask':'reused Cellpose labels; not resegmented',
    'moving_mask':'synthetic shifted reference labels; not H&E-derived segmentation',
    'baseline':'previously registered H&E; underlying biological alignment is not independently verified',
    'native_origin':'crop reset to local zero; source crop offset retained here',
}
(out/'fixture.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
