"""Independent real-data checks; run with the exporter environment."""

import sys
from pathlib import Path
from contextlib import ExitStack
import numpy as np
import ngff_zarr as ng
import zarr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
from integrate_omezarr import read

store = Path(sys.argv[1])
scene = ng.NgffScene.from_ome_zarr(str(store))
base = Path("/home/ubuntu/Caro/spl-out")
sources = {
    "macsima": base / "ashlar/SAMPLE_1/test/SAMPLE_1_exp2.ome.tif",
    "hne_registered": base / "stainwarpy/SAMPLE_1_exp2_transformed_image.ome.tif",
    "macsima/labels/cellpose": base
    / "cellpose/SAMPLE_1/test/SAMPLE_1_exp2.ome_cp_masks.tif",
}
with ExitStack() as stack:
    for name, path in sources.items():
        source, _, _, _ = read(stack, path)
        target = scene.images[name].images[0].data
        assert source.shape == target.shape and source.dtype == target.dtype
        for y, x in [(0, 0), (2000, 3000), (7900, 12500)]:
            selection = (slice(None),) * (source.ndim - 2) + (
                slice(y, y + 32),
                slice(x, x + 32),
            )
            np.testing.assert_array_equal(
                source[selection].compute(), target[selection].compute()
            )
        print(name, source.shape, source.dtype, "pixel patches match")
root = zarr.open_group(str(store), mode="r")
provenance = root.attrs["spatial_lattice"]
matrix = np.array(provenance["registration_metrics"]["Transformation Map"])
edges = scene.coordinateTransformations
registration = next(
    e
    for e in edges
    if e.input.name == "hne_native_pixels" and e.output.name == "registration_pixels"
)
resize = next(e for e in edges if e.input.name == "registration_pixels")
for x, y in [(0, 0), (100, 200), (5567, 10799)]:
    xy = matrix @ np.array([x, y, 1.0])
    yx = np.array(registration.affine) @ np.array([y, x, 1.0])
    np.testing.assert_allclose(yx, xy[:2][::-1])
    full = np.array([7985, 12602])
    small = np.array(provenance["registration_shape_yx"])
    expected = ((yx + 0.5) * full / small - 0.5) * 0.17
    np.testing.assert_allclose(np.array(resize.affine) @ np.r_[yx, 1.0], expected)
print("Forward XY/YX and resize pixel-center checks passed")
assert (
    root["macsima/labels/cellpose"].attrs["ome"]["image-label"]["source"]["image"]
    == "../../"
)
print("Label source reference verified")
