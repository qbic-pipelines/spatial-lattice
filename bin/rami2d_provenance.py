#!/usr/bin/env python3
"""Validate adapter inputs and archive native RAMI2D results; no registration logic."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
from importlib.metadata import version


def image_info(path):
    import tifffile
    from ome_types import from_xml
    with tifffile.TiffFile(path) as image:
        series = image.series[0]
        axes = series.axes.upper().replace("S", "C")
        if axes not in ("YX", "CYX", "YXC"):
            raise ValueError(f"Unsupported 2D image axes: {axes}")
        shape = dict(zip(axes, series.shape))
        pixels = from_xml(image.ome_metadata).images[0].pixels if image.ome_metadata else None
        return shape, pixels


def validate_calibration(pixels, expected):
    if expected <= 0:
        raise ValueError("Pixel sizes must be positive")
    if pixels is None:
        raise ValueError("OME calibration required for the integrated prototype")
    factors = {"µm": 1, "nm": 0.001, "mm": 1000}
    for axis in ("x", "y"):
        value = getattr(pixels, f"physical_size_{axis}")
        unit = getattr(pixels, f"physical_size_{axis}_unit").value
        if value is None or unit not in factors or abs(value * factors[unit] - expected) > expected * 1e-5:
            raise ValueError("Explicit RAMI2D pixel size disagrees with OME calibration (isotropic images required)")


def validate(fixed, moving, settings):
    for role, path in (("fixed", fixed), ("moving", moving)):
        shape, pixels = image_info(path)
        validate_calibration(pixels, settings[f"{role}_mpp"])
        channel = str(settings[f"{role}_channel"])
        if channel in ("h", "e"):
            if shape.get("C") != 3:
                raise ValueError("H&E stain extraction requires three RGB channels")
        elif not channel.isdigit() or int(channel) >= shape.get("C", 1):
            raise ValueError(f"Invalid {role} reference channel {channel}")


def validate_mask(moving, mask):
    import tifffile
    moving_shape, _ = image_info(moving)
    with tifffile.TiffFile(mask) as image:
        series = image.series[0]
        if series.axes != "YX" or series.shape != (moving_shape["Y"], moving_shape["X"]) or series.dtype.kind not in "ui":
            raise ValueError("Moving mask must be a 2D integer label image on the native moving grid")


def export(transforms, settings, log):
    files = sorted(Path(transforms).glob("*.txt"))
    if not files:
        raise ValueError("No native transform parameter files produced")
    manifest = {
        "schema_version": "1.0", "backend": "rami2d", "software_version": version("rami2d"),
        "parameters": settings, "reference_frame": "macsima_physical",
        "transform_format": "itk-elastix-parameter-files",
        "transform_directory": "registration/qc/fullres_trf",
        "transform_direction": "fixed-output-to-moving-input-resampling",
        "ngff_native_transform_conversion": "not_implemented",
        "alignment_quality": "not_assessed", "transform_files": [],
    }
    with tarfile.open("transforms.tar", "w") as archive:
        for path in files:
            archive.add(path, arcname=f"registration/qc/fullres_trf/{path.name}")
            manifest["transform_files"].append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        archive.add(log, arcname="registration.log")
    Path("registration.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate_parser = commands.add_parser("validate")
    for name in ("fixed", "moving", "settings"):
        validate_parser.add_argument("--" + name, required=True)
    mask_parser = commands.add_parser("validate-mask")
    for name in ("moving", "mask"):
        mask_parser.add_argument("--" + name, required=True)
    export_parser = commands.add_parser("export")
    for name in ("transforms", "settings", "log"):
        export_parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if args.command == "validate":
        validate(args.fixed, args.moving, json.loads(Path(args.settings).read_text()))
    elif args.command == "validate-mask":
        validate_mask(args.moving, args.mask)
    else:
        export(args.transforms, json.loads(Path(args.settings).read_text()), args.log)
