# RAMI2D linear transforms in RFC-5

`bin/rami2d_rfc5.py` converts the native transform archive produced by RAMI2D 1.0.2 into a native-H&E-to-MACSima affine. `bin/integrate_omezarr.py` uses it when `backend=rami2d`. The adapter only interprets metadata: it does not register or resample images and adds no production ITK dependency.

## Supported mapping

The adapter accepts 2D `TranslationTransform`, `EulerTransform` and `AffineTransform` chains with `HowToCombineTransforms=Compose`. It follows the explicit initial-transform references, rejecting missing, cyclic, disconnected or ambiguous chains. Affine parameters include their centre: `A(x-c)+c+t`. Nonlinear transforms, additive composition, singular matrices and inconsistent output grids fail explicitly.

The saved Elastix chain is a **pull** mapping from fixed physical XY coordinates to moving physical XY coordinates. With column vectors, each current transform multiplies the preceding composite from the left. The adapter inverts that composite to map moving points into fixed coordinates.

The output grid's origin, direction, spacing and starting index connect ITK physical coordinates to zero-based output-array coordinates. The adapter then applies the reference image's physical scale and changes XY to the scene's YX axis order. It checks that the saved grid size and spacing agree with the exported reference image. RAMI2D first resizes the moving image to the output spacing, rounding dimensions with `numpy.rint`. The adapter includes that resize's pixel-centre shift and scale before inverting the pull map. Its input is the calibrated full-resolution native image; its intermediate frame is RAMI2D's zero-origin, identity-direction resized array. Standard centre-aligned pyramid levels are assumed, matching the tool's size-based pyramid handling. External slide/stage offsets are not introduced.

The scene contains this path:

```text
hne_native_pixels → hne_native_physical → macsima_physical
       calibration       converted forward affine
```

Registered H&E and transformed labels already use the MACSima grid, so their existing grid mapping stays unchanged. The new affine is not applied to their pixels again.

Native maps and original backend metrics remain in `provenance/`. `provenance/rami2d_rfc5.json` records the ordered chain, pull matrix, converted forward matrix and output-grid geometry. The root `spatial_lattice.rami2d_rfc5_mapping` mirrors this record, while the actual RFC-5 edge is stored under `ome.scene.coordinateTransformations` using the pinned ngff-zarr writer. Normalized registration metadata marks conversion as `linear_affine`; the archived original backend JSON records its earlier processing stage.

## Validation

`tests/prototype/validate_rami2d_rfc5.py` compares 32 physical points per case against the pinned ITK/Transformix implementation. Cases cover translation, centred rigid transforms, affine shear/reflection, a non-commuting three-transform chain and the saved tissue-run chain. Synthetic output grids include nonzero origin/index, rotated direction cosines and anisotropic spacing.

All five cases passed; the maximum absolute discrepancy was below **5 × 10⁻⁷ µm**, consistent with Transformix's printed coordinate precision. Inverse/output-frame round trips passed at an absolute tolerance of 10⁻¹⁰ µm. An additional test compares the native-resolution conversion against the actual pinned RAMI2D resize operation (0.5023 µm to 0.17 µm), including rounded dimensions and nearest-neighbour pixels. Unit tests also reject unsupported, singular and invalid chains.

The pipeline comparison reuses the previous registrations and regenerates both OME-Zarrs. This isolates a metadata change from stochastic registration changes. Image/label arrays should remain identical at every pyramid level. It does not establish biological alignment accuracy; the tissue toy retains its previously documented residual misalignment.

## References

- [RFC-5 coordinate systems and transformations](https://ngff.openmicroscopy.org/rfc/5/).
- [Elastix transform parameters and composition](https://elastix.dev/doxygen/transformparameter.html).
- [RAMI2D source pinned for these conventions](https://github.com/VictorDidier/RAMI2D/blob/f6c4cc0f48dbd86b866ade8d3bf67177dd45712f/src/rami2d/utils_reg.py).
