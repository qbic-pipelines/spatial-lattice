"""Check a toy export against process TIFFs and report displacement recovery."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import tifffile
import zarr
import ngff_zarr as ng

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('store')
p.add_argument('inputs')
p.add_argument('--baseline', action='store_true')
a=p.parse_args()
store=Path(a.store)
inputs=Path(a.inputs)
ng.NgffScene.from_ome_zarr(str(store),validate=True)
root=zarr.open_group(str(store),mode='r')
def image(group):
    node=root[group]
    ds=node.attrs['ome']['multiscales'][0]['datasets']
    assert len(ds)==4, (group,len(ds))
    return node[ds[0]['path']][:]
def cyx(data):
    return data.transpose(2,0,1) if data.ndim==3 and data.shape[-1]==3 else data
mac=image('macsima')
mask=image('macsima/labels/cellpose')
he=image('hne_registered')
assert np.array_equal(mac,tifffile.imread(inputs/'fixed.ome.tif'))
assert np.array_equal(mask,tifffile.imread(inputs/'mask.tif'))
assert mac.shape[-2:]==mask.shape==he.shape[-2:]
provenance=root.attrs['spatial_lattice']
assert (store/provenance['native_transform_file']).is_file()
for name,source in provenance['sources'].items():
    if name in ('transform','metrics'):
        digest=hashlib.sha256((store/'provenance'/source['file']).read_bytes()).hexdigest()
        assert digest==source['sha256']
result={'store':store.name,'shape_yx':list(mask.shape),'image_dtype':str(mac.dtype),
    'reference_label_dtype':str(mask.dtype),'reference_labels':int(np.count_nonzero(np.unique(mask))),
    'schema_and_grids_valid':True,'reference_pixels_and_labels_unchanged':True,
    'native_transform_scene_edge':provenance['native_transform_scene_edge']}
if 'labels' in root['hne_registered']:
    moving_mask=image('hne_registered/labels/segmentation')
    assert moving_mask.shape==mask.shape and moving_mask.dtype.kind in 'ui'
    native=tifffile.imread(inputs/('moving_mask.tif' if a.baseline else 'mask.tif'))
    assert set(np.unique(moving_mask))<=set(np.unique(native))|{0}, 'Invented label IDs'
    result['moving_label_ids_preserved']=True
    # Diagnostic only; original labels are not independently segmented H&E.
    fg1=mask>0;fg2=moving_mask>0
    result['synthetic_label_foreground_dice']=float(2*np.count_nonzero(fg1&fg2)/max(1,np.count_nonzero(fg1)+np.count_nonzero(fg2)))
if a.baseline:
    baseline=cyx(tifffile.imread(inputs/'baseline_hne.ome.tif'))
    native=cyx(tifffile.imread(inputs/'moving.ome.tif'))
    # Ignore translation padding for the image comparison; no pass/fail threshold.
    region=(slice(None),slice(40,-40),slice(40,-40))
    result['hne_baseline_mae_before']=float(np.abs(native[region].astype(float)-baseline[region]).mean())
    result['hne_baseline_mae_after']=float(np.abs(he[region].astype(float)-baseline[region]).mean())
print(json.dumps(result,indent=2))
