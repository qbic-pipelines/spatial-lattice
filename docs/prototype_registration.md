# Prototype registration subworkflows

> Implementation review: see [prototype_subworkflows.md](prototype_subworkflows.md) for the current code, commands, tests and limitations. The design below records the broader target, not a claim that every feature is implemented. The new RAMI2D modules are built from scratch; vector OME ROIs remain deferred.


Conceptual design only; this does not change pipeline behavior or declare a finalized schema.

The [metro map](images/metromap.svg) groups Stainwarpy registration and transformation into a single `stainwarpy` subworkflow. It is the default backend when registration is selected. A future equivalent `rami2d` subworkflow will be an alternative selected by the user, not a sequential additional registration step. The diagram now includes RAMI2D as a selectable alternative route. See [the RAMI2D implementation proposal](rami2d_prototype.md).

Both backends should accept the same sample/ROI identity, reference and moving images, calibration, and optional labels. Each should emit one versioned registration-result bundle with the same layout and semantics:

| Component | Required meaning |
|---|---|
| Registered images | Images resampled onto the declared reference grid; paths, channel identity, axes, shape, dtype and physical calibration. |
| Transformed labels | Optional labels on the same grid, with integer IDs preserved and nearest-neighbor interpolation recorded. Absence must be explicit. |
| Transform chain | Ordered moving-to-reference transforms, with explicit input/output coordinate systems, axis order, units, direction and composition order. Record rigid, similarity or affine type and numeric parameters; record any preprocessing, cropping and resizing needed to interpret the mapping. |
| Reference grid | Shape, axis order, pixel spacing, origin and pixel-center convention. |
| Provenance | Backend and version, actual model/algorithm parameters, source identifiers/checksums, interpolation and available quality metrics. |
| Native outputs | Original backend transform files retained for provenance, alongside the common representation. |

A proposed bundle layout is `registration.json`, `images/`, `labels/`, `transforms/`, and `provenance/`. File encodings and schema will be agreed before implementation. Nonlinear transforms must be represented explicitly with their coordinate conventions or rejected as unsupported; never silently converted into affine matrices. Inverse mappings are included only when available and valid.

Backend adapters will normalize these outputs. BUILD_INTEGRATED_OMEZARR will consume the common bundle without inspecting backend-specific filenames or parameter conventions. It must distinguish already-resampled images from native images so transforms are not applied twice, and map the declared coordinate systems and transform chain into the target OME-NGFF/RFC-5 representation.

This common output interface supports FAIR reuse but does not by itself establish full FAIR compliance. The existing optional upstream routes are preserved in the diagram pending further prototype design.

