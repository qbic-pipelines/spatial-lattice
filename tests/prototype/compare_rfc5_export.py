"""Verify an RFC-5 re-export preserves all image/label pyramid pixels."""
import argparse
import json
import numpy as np
import zarr
import ngff_zarr as ng

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('previous')
p.add_argument('current')
a=p.parse_args()
old=zarr.open_group(a.previous,mode='r')
new=zarr.open_group(a.current,mode='r')
ng.NgffScene.from_ome_zarr(a.current,validate=True)
checks=[]
for group in ('macsima','macsima/labels/cellpose','hne_registered','hne_registered/labels/segmentation'):
    for left,right in zip(old[group].attrs['ome']['multiscales'][0]['datasets'],new[group].attrs['ome']['multiscales'][0]['datasets'],strict=True):
        before=old[group][left['path']]
        after=new[group][right['path']]
        assert before.dtype==after.dtype
        np.testing.assert_array_equal(before[:],after[:])
        checks.append(group+'/'+right['path'])
meta=new.attrs['spatial_lattice']
if meta['rami2d_rfc5_mapping']:
    mapping=meta['rami2d_rfc5_mapping']
    edges=new.attrs['ome']['scene']['coordinateTransformations']
    edge=next(e for e in edges if e['input'].get('name')=='hne_native_physical' and e['output'].get('name')=='macsima_physical')
    stored=new[edge['path']][:] if 'path' in edge else np.asarray(edge['affine'])
    np.testing.assert_allclose(stored,mapping['moving_physical_to_reference_physical_yx'],atol=1e-12)
print(json.dumps({'pyramid_arrays_identical':len(checks),'ngff_scene_valid':True,
                  'native_transform_scene_edge':meta['native_transform_scene_edge'],
                  'rami2d_mapping':meta['rami2d_rfc5_mapping']},indent=2))
