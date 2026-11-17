"""Compare the Python adapter with Transformix's physical point mapping."""
import json
from pathlib import Path
import re
import sys
import tarfile
import tempfile
import numpy as np
import itk
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'bin'))
from rami2d_rfc5 import compose_chain, read_archive, scene_mapping, native_resize_mapping
from test_rami2d_rfc5 import parameters


def compare(maps, directory):
    pull, final, order = compose_chain(maps)
    pointset = np.vstack(([0,0],[10,20],np.random.default_rng(14).uniform(-10,150,(30,2))))
    points_file = directory/'points.txt'
    points_file.write_text('point\n'+str(len(pointset))+'\n'+'\n'.join(' '.join(map(str,p)) for p in pointset)+'\n')
    pobj=itk.ParameterObject.New()
    for name in order: pobj.AddParameterMap(maps[name])
    image=itk.image_from_array(np.zeros((96,128),dtype=np.float32))
    image.SetSpacing([.2,.4])
    transformix=itk.TransformixFilter.New(MovingImage=image,TransformParameterObject=pobj)
    transformix.SetFixedPointSetFileName(str(points_file))
    transformix.SetOutputDirectory(str(directory))
    transformix.SetLogToConsole(False)
    transformix.UpdateLargestPossibleRegion()
    text=(directory/'outputpoints.txt').read_text()
    actual=np.array([[float(x) for x in row.split()] for row in re.findall(r'OutputPoint = \[([^]]+)\]',text)])
    predicted=(pull@np.column_stack([pointset,np.ones(len(pointset))]).T).T[:,:2]
    error=float(np.max(np.abs(actual-predicted)))
    np.testing.assert_allclose(actual,predicted,atol=1e-4,rtol=0)
    # Test the complete inverse and output-frame conversion, not only pull maps.
    archive=directory/'transforms.tar'
    with tarfile.open(archive,'w') as tar:
        for name,p in maps.items():
            file=directory/Path(name).name
            file.write_text('\n'.join('('+key+' '+' '.join('"'+str(v)+'"' for v in value)+')' for key,value in p.items()))
            tar.add(file,arcname=name)
    spacing=np.array(final['Spacing'],dtype=float)
    size=np.array(final['Size'],dtype=int)
    result=scene_mapping(archive,size[::-1],spacing[::-1], [23,31], [.5023,.5023])
    forward=np.vstack([result['moving_physical_to_reference_physical_yx'],[0,0,1]])
    resize=np.array(result['native_physical_to_resized_moving_physical_xy'])
    native_physical=(np.linalg.inv(resize)@np.column_stack([predicted,np.ones(len(pointset))]).T).T[:,:2]
    recovered=(forward@np.column_stack([native_physical[:,::-1],np.ones(len(pointset))]).T).T[:,:2]
    direction=np.array(final['Direction'],dtype=float).reshape(2,2,order='F')
    # Scene physical coordinates: zero-based array indices times output spacing.
    expected=((np.linalg.inv(direction)@(pointset-np.array(final['Origin'],float)).T).T - spacing*np.array(final['Index'],float))[:,::-1]
    np.testing.assert_allclose(recovered,expected,atol=1e-10,rtol=0)
    return {'points':len(pointset),'max_transformix_error_um':error,'inverse_and_output_grid_pass':True}


def compare_resize(directory):
    import tifffile
    from rami2d.processing_tools import ImageFileGateway
    shape = (23, 31)
    source = np.arange(np.prod(shape), dtype=np.uint16).reshape(shape)
    path = directory/'native.tif'
    tifffile.imwrite(path, source, metadata={'axes':'YX'}, photometric='minisblack')
    resized = ImageFileGateway(path, .5023).resize(.17)
    matrix, target = native_resize_mapping(shape, [.5023,.5023], [.17,.17])
    yy, xx = np.indices(resized.shape)
    positions = np.stack([xx.ravel()*.17, yy.ravel()*.17, np.ones(xx.size)])
    native_pixels = (np.linalg.inv(matrix) @ positions)[:2] / .5023
    nearest = np.floor(native_pixels + .5).astype(int)
    expected = source[np.clip(nearest[1],0,shape[0]-1),np.clip(nearest[0],0,shape[1]-1)].reshape(resized.shape)
    np.testing.assert_array_equal(resized, expected)
    np.testing.assert_array_equal(target, resized.shape)
    return {'native_shape_yx':list(shape),'resized_shape_yx':list(resized.shape),
            'actual_rami2d_resize_pixels_match':True}


def main():
    results={}
    grid=dict(Size=['128','96'],Spacing=['.2','.4'],Origin=['2','3'],Index=['5','7'],Direction=['0','1','-1','0'],UseDirectionCosines=['true'],
        FixedInternalImagePixelType=['float'],MovingInternalImagePixelType=['float'],ResampleInterpolator=['FinalBSplineInterpolator'],
        FinalBSplineInterpolationOrder=['1'],Resampler=['DefaultResampler'],DefaultPixelValue=['0'],ResultImageFormat=['tif'],ResultImagePixelType=['float'])
    chains={
      'translation':{'a.txt':parameters('TranslationTransform',[7,-9])},
      'centered_rigid':{'a.txt':parameters('EulerTransform',[.37,4,-5],(19,31))},
      'affine_reflection':{'a.txt':parameters('AffineTransform',[-1.2,.3,.2,.8,7,-6],(9,13))},
      'noncommuting_chain':{'a.txt':parameters('TranslationTransform',[7,-9]),
                           'b.txt':parameters('EulerTransform',[.37,4,-5],(19,31),'a.txt'),
                           'c.txt':parameters('AffineTransform',[1.2,.3,.2,.8,7,-6],(9,13),'b.txt')},
    }
    for maps in chains.values():
        for p in maps.values():
            p.update(grid)
            p['NumberOfParameters']=[str(len(p['TransformParameters']))]
    if len(sys.argv)>1: chains['saved_tissue_chain']=read_archive(sys.argv[1])
    with tempfile.TemporaryDirectory() as temp:
        for name,maps in chains.items():
            directory=Path(temp)/name;directory.mkdir()
            results[name]=compare(maps,directory)
        directory=Path(temp)/'resize';directory.mkdir()
        results['unequal_resolution_resize']=compare_resize(directory)
    print(json.dumps(results,indent=2))

if __name__=='__main__': main()
