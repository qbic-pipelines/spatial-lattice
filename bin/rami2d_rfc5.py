"""Convert RAMI2D 1.0.2's 2D linear Elastix chain to an RFC-5 affine.

No registration or image resampling occurs here. Matrices use column vectors.
Elastix maps fixed physical points to moving physical points (the pull map).
The exported edge inverts that map and changes XY to the scene's YX order.
"""
from pathlib import PurePosixPath
import re
import shlex
import tarfile

import numpy as np


def parse_parameters(text):
    result = {}
    text = re.sub(r'//[^\n]*', '', text)
    for record in re.findall(r'\(([^()]*)\)', text, flags=re.S):
        fields = shlex.split(record)
        if not fields or fields[0] in result:
            raise ValueError('Empty or duplicate Elastix parameter')
        result[fields[0]] = fields[1:]
    return result


def numbers(parameters, key, count):
    values = np.asarray(parameters.get(key, []), dtype=float)
    if values.shape != (count,) or not np.isfinite(values).all():
        raise ValueError(f'{key} must contain {count} finite numbers')
    return values


def linear_matrix(parameters):
    for dimension in ('FixedImageDimension', 'MovingImageDimension'):
        if parameters.get(dimension) != ['2']:
            raise ValueError('Only 2D transforms are supported')
    if parameters.get('HowToCombineTransforms', ['Compose']) != ['Compose']:
        raise ValueError('Only Compose transform chains are supported')
    kind = parameters.get('Transform', [None])[0]
    center = np.zeros(2)
    if kind == 'TranslationTransform':
        matrix = np.eye(2)
        translation = numbers(parameters, 'TransformParameters', 2)
    elif kind == 'EulerTransform':
        angle, tx, ty = numbers(parameters, 'TransformParameters', 3)
        matrix = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        translation = np.array([tx, ty])
        center = numbers(parameters, 'CenterOfRotationPoint', 2)
    elif kind == 'AffineTransform':
        values = numbers(parameters, 'TransformParameters', 6)
        matrix, translation = values[:4].reshape(2, 2), values[4:]
        center = numbers(parameters, 'CenterOfRotationPoint', 2)
    else:
        raise ValueError(f'Unsupported transform {kind}; nonlinear maps must not be approximated as affine')
    out = np.eye(3)
    out[:2, :2] = matrix
    out[:2, 2] = center + translation - matrix @ center
    if not np.isfinite(np.linalg.cond(out[:2, :2])) or np.linalg.cond(out[:2, :2]) > 1e12:
        raise ValueError('Singular or ill-conditioned affine')
    return out


def compose_chain(maps):
    """Resolve the single linked chain, rather than trusting filename order."""
    parents = {}
    for name, parameters in maps.items():
        refs = parameters.get('InitialTransformParameterFileName', [])
        if len(refs) != 1:
            raise ValueError('Expected one explicit initial transform reference')
        ref = refs[0]
        if ref == 'NoInitialTransform':
            parents[name] = None
        else:
            candidates = {ref, str(PurePosixPath(name).parent / ref)} & maps.keys()
            if len(candidates) != 1:
                raise ValueError(f'Missing or ambiguous initial transform: {ref}')
            parents[name] = candidates.pop()
    leaves = set(maps) - {value for value in parents.values() if value is not None}
    if len(leaves) != 1:
        raise ValueError('Expected a single complete transform chain')
    last = leaves.pop()
    order = []
    current = last
    while current is not None:
        if current in order:
            raise ValueError('Cyclic transform chain')
        order.append(current)
        current = parents[current]
    if len(order) != len(maps):
        raise ValueError('Unconnected transform files')
    order.reverse()
    pull = np.eye(3)
    for name in order:
        pull = linear_matrix(maps[name]) @ pull
    return pull, maps[last], order


def read_archive(path):
    maps = {}
    with tarfile.open(path, 'r:*') as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if member.name.endswith('.txt'):
                if not member.isfile() or name.is_absolute() or '..' in name.parts or member.name in maps:
                    raise ValueError('Unsafe or duplicate transform archive member')
                if member.size > 1024 * 1024:
                    raise ValueError('Transform parameter file exceeds size limit')
                maps[member.name] = parse_parameters(archive.extractfile(member).read().decode('utf-8'))
    if not maps:
        raise ValueError('No transform parameter files')
    return maps


def native_resize_mapping(shape_yx, spacing_yx, output_spacing_yx):
    """Native physical XY → RAMI2D's pre-resized moving physical XY.

    RAMI2D rounds target sizes with numpy.rint and uses skimage.resize's
    pixel-centre geometry. Standard aligned pyramid levels compose to the
    same full-resolution centre mapping.
    """
    shape = np.asarray(shape_yx, dtype=float)
    spacing = np.asarray(spacing_yx, dtype=float)
    output_spacing = np.asarray(output_spacing_yx, dtype=float)
    if any(v.shape != (2,) or not np.isfinite(v).all() or np.any(v <= 0)
           for v in (shape, spacing, output_spacing)):
        raise ValueError('Native shape and pixel sizes must be finite and positive')
    target = np.rint(shape * spacing / output_spacing)
    if np.any(target < 1):
        raise ValueError('RAMI2D resized image would have an empty axis')
    ratio = target / shape
    conversion = np.eye(3)
    conversion[:2, :2] = np.diag((output_spacing * ratio / spacing)[::-1])
    conversion[:2, 2] = (output_spacing * (ratio - 1) / 2)[::-1]
    return conversion, target.astype(int)


def scene_mapping(path, reference_shape_yx, reference_spacing_yx, native_shape_yx=None, native_spacing_yx=None):
    pull, final, order = compose_chain(read_archive(path))
    size = numbers(final, 'Size', 2)
    spacing = numbers(final, 'Spacing', 2)
    origin = numbers(final, 'Origin', 2)
    index = numbers(final, 'Index', 2)
    if not np.array_equal(size, np.asarray(reference_shape_yx)[::-1]):
        raise ValueError('Transform output size differs from the reference image')
    if not np.allclose(spacing, np.asarray(reference_spacing_yx)[::-1], rtol=1e-6, atol=0):
        raise ValueError('Transform spacing differs from the calibrated reference image')
    if final.get('UseDirectionCosines', ['true']) != ['true']:
        raise ValueError('UseDirectionCosines=false is not supported')
    direction = numbers(final, 'Direction', 4).reshape(2, 2, order='F')
    if not np.allclose(direction.T @ direction, np.eye(2), atol=1e-8):
        raise ValueError('Invalid direction cosine matrix')
    # TIFF/NGFF output arrays have zero-based indices even if the ITK grid does not.
    grid = np.eye(3)
    grid[:2, :2] = direction @ np.diag(spacing)
    grid[:2, 2] = origin + grid[:2, :2] @ index
    scene_scale = np.diag([*np.asarray(reference_spacing_yx)[::-1], 1.0])
    resize = np.eye(3)
    resized_shape = None
    if (native_shape_yx is None) != (native_spacing_yx is None):
        raise ValueError('Native shape and spacing must be provided together')
    if native_shape_yx is not None:
        resize, resized_shape = native_resize_mapping(native_shape_yx, native_spacing_yx, spacing[::-1])
    forward = scene_scale @ np.linalg.inv(grid) @ np.linalg.inv(pull) @ resize
    swap = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]])
    return {
        'adapter': 'rami2d-1.0.2-elastix-linear-v1',
        'transform_files_in_composition_order': order,
        'fixed_to_resized_moving_physical_xy': pull.tolist(),
        'native_physical_to_resized_moving_physical_xy': resize.tolist(),
        'resized_moving_shape_yx': resized_shape.tolist() if resized_shape is not None else None,
        'moving_physical_to_reference_physical_yx': (swap @ forward @ swap)[:2].tolist(),
        'output_grid': {'size_xy': size.tolist(), 'spacing_xy_um': spacing.tolist(),
                        'origin_xy_um': origin.tolist(), 'index_xy': index.tolist(),
                        'direction_xy': direction.tolist()},
    }
