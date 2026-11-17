include { SPATIAL_REGISTRATION_STAINWARPY } from '../../subworkflows/local/spatial_registration_stainwarpy/main'
include { SPATIAL_REGISTRATION_RAMI2D } from '../../subworkflows/local/spatial_registration_rami2d/main'
include { BUILD_INTEGRATED_OMEZARR } from '../../subworkflows/local/build_integrated_omezarr/main'

// Starts from a tissue crop, not raw MACSima acquisition cycles.
workflow {
    base = file(params.fixture)
    inputs = channel.of([[id: "tissue_${params.registration_backend}"],
        base/'fixed.ome.tif', base/'moving.ome.tif', base/'moving_mask.tif'])
    if (params.registration_backend == 'stainwarpy') {
        SPATIAL_REGISTRATION_STAINWARPY(inputs)
        result = SPATIAL_REGISTRATION_STAINWARPY.out.result
    } else {
        SPATIAL_REGISTRATION_RAMI2D(inputs)
        result = SPATIAL_REGISTRATION_RAMI2D.out.result
    }
    outputs = result.map { meta, fixed, moving, registered, mask, transforms, metrics ->
        [meta, fixed, base/'mask.tif', registered, moving, transforms, metrics, base/'markers.csv', mask]
    }
    BUILD_INTEGRATED_OMEZARR(outputs)
}
