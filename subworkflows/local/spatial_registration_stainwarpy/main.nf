include { TIF_REGISTRATION_STAINWARPY } from '../tif_registration_stainwarpy/main'

// Both backends emit [meta, fixed, native_moving, registered, moving_mask_or_empty,
//                    native_transform, metrics]. Registered images/masks use the fixed grid.
workflow SPATIAL_REGISTRATION_STAINWARPY {
    take:
    ch_input // [meta, fixed MACSima image, moving H&E image, optional moving mask]
    main:
    TIF_REGISTRATION_STAINWARPY(ch_input)
    ch_masks = ch_input.filter { meta, fixed, moving, mask -> !mask }
        .map { meta, fixed, moving, mask -> [meta.id, []] }
        .mix(TIF_REGISTRATION_STAINWARPY.out.transformed_segmask.map { meta, mask -> [meta.id, mask] })
    ch_result = ch_input.map { meta, fixed, moving, mask -> [meta.id, meta, fixed, moving] }
        .join(TIF_REGISTRATION_STAINWARPY.out.transformed_image.map { meta, image -> [meta.id, image] }, failOnDuplicate: true, failOnMismatch: true)
        .join(ch_masks, failOnDuplicate: true, failOnMismatch: true)
        .join(TIF_REGISTRATION_STAINWARPY.out.transform.map { meta, transform -> [meta.id, transform] }, failOnDuplicate: true, failOnMismatch: true)
        .join(TIF_REGISTRATION_STAINWARPY.out.metrics.map { meta, metrics -> [meta.id, metrics] }, failOnDuplicate: true, failOnMismatch: true)
        .map { id, meta, fixed, moving, registered, mask, transform, metrics ->
            [meta + [registration_backend: 'stainwarpy'], fixed, moving, registered, mask, transform, metrics]
        }
    emit:
    result = ch_result
}
