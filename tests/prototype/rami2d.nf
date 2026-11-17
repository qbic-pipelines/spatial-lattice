include { SPATIAL_REGISTRATION_RAMI2D } from '../../subworkflows/local/spatial_registration_rami2d/main'
include { BUILD_INTEGRATED_OMEZARR } from '../../subworkflows/local/build_integrated_omezarr/main'

workflow {
    base = file(params.fixture)
    inputs = channel.of(
        [[id: 'with_mask'], base/'fixed.ome.tif', base/'moving.ome.tif', base/'mask.tif'],
        [[id: 'without_mask'], base/'fixed.ome.tif', base/'moving.ome.tif', []]
    )
    SPATIAL_REGISTRATION_RAMI2D(inputs)
    outputs = SPATIAL_REGISTRATION_RAMI2D.out.result.map { meta, fixed, moving, registered, mask, transforms, metrics ->
        [meta, fixed, base/'mask.tif', registered, moving, transforms, metrics, base/'markers.csv', mask]
    }
    BUILD_INTEGRATED_OMEZARR(outputs)
}
