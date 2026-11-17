#!/usr/bin/env python
"""Write registered images and masks as a calibrated NGFF scene."""

import argparse, csv, json, hashlib, shutil
from importlib.metadata import version
from pathlib import Path
from contextlib import ExitStack
import numpy as np
from rami2d_rfc5 import scene_mapping
import dask.array as da
import tifffile, zarr, ngff_zarr as ng
from ome_types import from_xml
from ngff_zarr.v06.zarr_metadata import (
    Axis,
    CoordinateSystem,
    CoordinateSystemIdentifier as Ref,
    Affine,
)


def read(stack, path):
    t = stack.enter_context(tifffile.TiffFile(path))
    s = t.series[0]
    axes = s.axes.lower().replace("s", "c")
    store = s.levels[0].aszarr()
    stack.callback(store.close)
    node = zarr.open(store, mode="r")
    data = da.from_zarr(node["0"] if isinstance(node, zarr.Group) else node)
    if axes == "yxc":
        data = data.transpose(2, 0, 1)
        axes = "cyx"
    if axes not in ("cyx", "yx"):
        raise ValueError(f"Unsupported axes {axes}")
    xml = t.ome_metadata
    return data, axes, from_xml(xml).images[0].pixels if xml else None, xml


def spacing(p):
    factors = {"µm": 1, "nm": 0.001, "mm": 1000}
    if p is None or p.physical_size_x is None or p.physical_size_y is None:
        raise ValueError("Physical calibration is required")
    return np.array(
        [
            p.physical_size_y * factors[p.physical_size_y_unit.value],
            p.physical_size_x * factors[p.physical_size_x_unit.value],
        ],
        dtype=float,
    )


def checksum(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(path):
    scene = ng.NgffScene.from_ome_zarr(str(path), validate=True)
    shapes = {k: list(v.images[0].data.shape) for k, v in scene.images.items()}
    assert (
        shapes["macsima"][-2:]
        == shapes["hne_registered"][-2:]
        == shapes["macsima/labels/cellpose"]
    )
    if 'hne_registered/labels/segmentation' in shapes:
        assert shapes['hne_registered/labels/segmentation'] == shapes['hne_registered'][-2:]
    Path("integrated_omezarr_mqc.json").write_text(
        json.dumps(
            {
                "id": "integrated_omezarr",
                "section_name": "Integrated OME-Zarr",
                "description": "Scene read-back and reference-grid validation.",
                "plot_type": "table",
                "data": {Path(path).name: {"images": len(shapes), "validated": 1}},
            },
            indent=2,
        )
    )


def export(a):
    out = Path(a.output)
    if out.exists():
        raise ValueError(f"Refusing to overwrite {out}")
    with ExitStack() as stack:
        mac, axes, mp, mx = read(stack, a.macsima)
        mask, la, _, _ = read(stack, a.mask)
        he, ha, hp, hx = read(stack, a.hne)
        native_he, _, npix, nx = read(stack, a.native_hne)
        px = spacing(mp)
        npx = spacing(npix)
        assert np.allclose(px, px[0]) and np.allclose(npx, npx[0]), (
            "Anisotropic inputs unsupported by this adapter"
        )
        assert mac.shape[-2:] == mask.shape == he.shape[-2:], "Reference grids disagree"
        assert np.allclose(px, spacing(hp)) and la == "yx" and mask.dtype.kind in "ui"
        markers = list(csv.DictReader(open(a.markers)))
        names = [r["marker_name"] for r in markers]
        assert len(names) == mac.shape[0], "Marker count mismatch"
        moving_mask = None
        if a.moving_mask:
            moving_mask, moving_axes, _, _ = read(stack, a.moving_mask)
            assert moving_axes == 'yx' and moving_mask.dtype.kind in 'ui'
            assert moving_mask.shape == he.shape[-2:], 'Moving mask is not on the registered image grid'
        images = {}
        edges = []
        layers = [
            ("macsima", mac, axes, False, names),
            ("macsima/labels/cellpose", mask, la, True, None),
            ("hne_registered", he, ha, False, ["Red", "Green", "Blue"]),
        ]
        if moving_mask is not None:
            layers.append(('hne_registered/labels/segmentation', moving_mask, 'yx', True, None))
        for name, data, dims, label, channels in layers:
            image = ng.to_ngff_image(
                data,
                dims=tuple(dims),
                name=name.split("/")[-1],
                scale=dict(zip("yx", px)),
                axes_units={"y": "micrometer", "x": "micrometer"},
                channel_names=channels,
            )
            images[name] = ng.to_multiscales(
                image,
                scale_factors=[2, 4, 8],
                method=ng.Methods.DASK_IMAGE_NEAREST
                if label
                else ng.Methods.DASK_IMAGE_GAUSSIAN,
                chunks={d: 1 if d == "c" else 512 for d in dims},
            )
            matrix = (
                [[0, 1, 0, 0], [0, 0, 1, 0]]
                if dims == "cyx"
                else [[1, 0, 0], [0, 1, 0]]
            )
            edges.append(
                Affine(
                    input=Ref(path=name, name="intrinsic"),
                    output=Ref(name="macsima_physical"),
                    affine=matrix,
                )
            )
        systems = [
            CoordinateSystem(
                "macsima_physical",
                [Axis("y", "space", "micrometer"), Axis("x", "space", "micrometer")],
            )
        ]
        small = None
        rami_mapping = None
        if a.backend == 'stainwarpy':
            systems.extend([
                CoordinateSystem("hne_native_pixels", [Axis("y", "space"), Axis("x", "space")]),
                CoordinateSystem("registration_pixels", [Axis("y", "space"), Axis("x", "space")]),
                CoordinateSystem("hne_native_physical", [Axis("y", "space", "micrometer"), Axis("x", "space", "micrometer")]),
            ])
            edges.append(Affine(
                input=Ref(name="hne_native_pixels"), output=Ref(name="hne_native_physical"),
                affine=[[float(npx[0]), 0, 0], [0, float(npx[1]), 0]],
            ))
            m = np.load(a.transform, allow_pickle=False)
            assert m.shape == (3, 3) and np.allclose(m[2], [0, 0, 1]), (
                "Only affine/similarity transforms supported"
            )
            swap = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]])
            edges.append(
                Affine(
                    input=Ref(name="hne_native_pixels"),
                    output=Ref(name="registration_pixels"),
                    affine=(swap @ m @ swap)[:2].tolist(),
                )
            )
            full = np.array(mac.shape[-2:])
            small = (full / (npx[0] / px[0])).astype(int)
            ratio = full / small
            # skimage.resize pixel-center mapping from registration grid to original reference.
            edges.append(
                Affine(
                    input=Ref(name="registration_pixels"),
                    output=Ref(name="macsima_physical"),
                    affine=np.column_stack(
                        (np.diag(px * ratio), px * (ratio - 1) / 2)
                    ).tolist(),
                )
            )
        else:
            rami_mapping = scene_mapping(a.transform, mac.shape[-2:], px, native_he.shape[-2:], npx)
            systems.extend([
                CoordinateSystem("hne_native_pixels", [Axis("y", "space"), Axis("x", "space")]),
                CoordinateSystem("hne_native_physical", [Axis("y", "space", "micrometer"), Axis("x", "space", "micrometer")]),
            ])
            edges.extend([
                Affine(input=Ref(name="hne_native_pixels"), output=Ref(name="hne_native_physical"),
                       affine=[[float(npx[0]), 0, 0], [0, float(npx[1]), 0]]),
                Affine(input=Ref(name="hne_native_physical"), output=Ref(name="macsima_physical"),
                       affine=rami_mapping['moving_physical_to_reference_physical_yx']),
            ])
        ng.to_ngff_zarr(
            out,
            ng.NgffScene(images, edges, systems),
            version="0.6",
            consolidate_metadata=False,
        )
        root = zarr.open_group(str(out), mode="a")
        root["macsima/labels"].attrs["ome"] = {"version": "0.6", "labels": ["cellpose"]}
        g = root["macsima/labels/cellpose"]
        meta = dict(g.attrs["ome"])
        meta["image-label"] = {"version": "0.6", "source": {"image": "../../"}}
        g.attrs["ome"] = meta
        if moving_mask is not None:
            root['hne_registered/labels'].attrs['ome'] = {'version': '0.6', 'labels': ['segmentation']}
            label_group = root['hne_registered/labels/segmentation']
            label_metadata = dict(label_group.attrs['ome'])
            label_metadata['image-label'] = {'version': '0.6', 'source': {'image': '../../'}}
            label_group.attrs['ome'] = label_metadata
        # Retain native transforms alongside the standardized scene mapping.
        provenance = out / 'provenance'
        provenance.mkdir()
        shutil.copyfile(a.transform, provenance / Path(a.transform).name)
        shutil.copyfile(a.metrics, provenance / Path(a.metrics).name)
        registration_metrics = json.load(open(a.metrics))
        if rami_mapping is not None:
            (provenance / 'rami2d_rfc5.json').write_text(json.dumps(rami_mapping, indent=2) + '\n')
            registration_metrics = dict(registration_metrics, ngff_native_transform_conversion='linear_affine')
        root.attrs["spatial_lattice"] = {
            "adapter": a.backend + '-fixed-and-final-multiplexed',
            "native_transform_file": 'provenance/' + Path(a.transform).name,
            "native_transform_scene_edge": True,
            "rami2d_rfc5_mapping": rami_mapping,
            "alignment_quality": "not_assessed",
            "native_hne_spacing_um": npx.tolist(),
            "registration_shape_yx": small.tolist() if small is not None else None,
            "source_ome_xml": {"macsima": mx, "hne_native": nx, "hne_registered": hx},
            "markers": markers,
            "registration_metrics": registration_metrics,
            "software": {
                name: version(name)
                for name in ("ngff-zarr", "zarr", "tifffile", "dask")
            },
            "sources": {
                name: {"file": Path(value).name, "sha256": checksum(value)}
                for name, value in vars(a).items()
                if name not in ("output", "backend") and value
            },
        }
    validate(out)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for n in (
        "macsima",
        "mask",
        "hne",
        "native-hne",
        "transform",
        "metrics",
        "markers",
        "output",
    ):
        p.add_argument("--" + n, required=True)
    p.add_argument('--backend', choices=['stainwarpy', 'rami2d'], default='stainwarpy')
    p.add_argument('--moving-mask')
    export(p.parse_args())
