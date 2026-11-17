include { RAMI2D_REGISTER_IMAGES } from '../../../modules/local/rami2d/register_images/main'
include { RAMI2D_TRANSFORM_LABELS } from '../../../modules/local/rami2d/transform_labels/main'
include { RAMI2D_EXPORT_RESULT } from '../../../modules/local/rami2d/export_result/main'

workflow SPATIAL_REGISTRATION_RAMI2D {
    take:
    ch_input // [meta, fixed MACSima, moving H&E, moving mask or []]
    main:
    settings = [
        fixed_mpp: params.rami2d_mpp_fix, moving_mpp: params.rami2d_mpp_mov,
        fixed_channel: params.rami2d_ifix, moving_channel: params.rami2d_imov,
        registration_mpp: params.rami2d_mpp_reg, keypoints_mpp: params.rami2d_mpp_key,
        scheme: params.rami2d_scheme, initial_alignment: params.rami2d_initial_alignment
    ]
    if (!(settings.scheme in [1, 2])) error 'RAMI2D prototype supports scheme 1 (rigid) or 2 (rigid then affine)'
    [settings.fixed_mpp, settings.moving_mpp, settings.registration_mpp, settings.keypoints_mpp].each { resolution ->
        if (resolution == null || resolution <= 0) error 'RAMI2D requires explicit positive pixel sizes and registration/keypoint resolutions'
    }
    if (!(settings.fixed_channel.toString() ==~ /[0-9]+/) || !(settings.moving_channel.toString() ==~ /([0-9]+|h|e)/))
        error 'RAMI2D channels must be non-negative indices (moving may also be h or e)'

    RAMI2D_REGISTER_IMAGES(ch_input.map { meta, fixed, moving, mask -> [meta, fixed, moving, settings] })
    ch_transforms = RAMI2D_REGISTER_IMAGES.out.transforms
    ch_mask_inputs = ch_input.filter { meta, fixed, moving, mask -> mask }
        .map { meta, fixed, moving, mask -> [meta.id, meta, mask, moving] }
        .join(ch_transforms.map { meta, transforms, settings_file, log -> [meta.id, transforms] })
        .map { id, meta, mask, moving, transforms -> [meta, mask, moving, transforms, settings.moving_mpp] }
    RAMI2D_TRANSFORM_LABELS(ch_mask_inputs)
    RAMI2D_EXPORT_RESULT(ch_transforms)
    ch_masks = ch_input.filter { meta, fixed, moving, mask -> !mask }
        .map { meta, fixed, moving, mask -> [meta.id, []] }
        .mix(RAMI2D_TRANSFORM_LABELS.out.mask.map { meta, mask -> [meta.id, mask] })
    ch_result = ch_input.map { meta, fixed, moving, mask -> [meta.id, meta, fixed, moving] }
        .join(RAMI2D_REGISTER_IMAGES.out.image.map { meta, image -> [meta.id, image] }, failOnDuplicate: true, failOnMismatch: true)
        .join(ch_masks, failOnDuplicate: true, failOnMismatch: true)
        .join(RAMI2D_EXPORT_RESULT.out.result.map { meta, transforms, metrics -> [meta.id, transforms, metrics] }, failOnDuplicate: true, failOnMismatch: true)
        .map { id, meta, fixed, moving, registered, mask, transforms, metrics ->
            [meta + [registration_backend: 'rami2d'], fixed, moving, registered, mask, transforms, metrics]
        }
    emit:
    result = ch_result
}
