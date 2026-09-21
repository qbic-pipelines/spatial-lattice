//
// Register H&E stained and multiplexed tissue images and transform segmentation masks using stainwarpy
//

include { STAINWARPY_REGISTER         } from '../../../modules/local/stainwarpy/register/main'
include { STAINWARPY_EXTRACTCHANNEL   } from '../../../modules/local/stainwarpy/extractchannel/main'
include { STAINWARPY_TRANSFORMSEGMASK } from '../../../modules/local/stainwarpy/transformsegmask/main'

workflow TIF_REGISTRATION_STAINWARPY {

    take:
    ch_stainwarpy_input     // channel: [ val(meta), path to macsima.tiff, path to hne.tiff, segmenation mask ]
    //ch_hne              // channel: [ val(meta), path to .tif ]
    //ch_multiplexed      // channel: [ val(meta), path to .tif ]
    //ch_segmask          // channel: [ val(meta), path to .tif ] (optional)
    //val_fixed_img       // val: fixed image to use ("multiplexed" or "hne")
    //val_final_img_sz    // val: final image size to use ("multiplexed" or "hne")

    main:
    ch_transformed_segmask = channel.empty()
    ch_multiplexed_forward = channel.empty()

    ch_segmask = ch_stainwarpy_input.map { meta, multiplx_img, hne_img, seg_mask ->
        [meta, seg_mask]
    }

    if ( params.fixed_img == 'multiplexed') {
        // get the multiplexed image from the input channel and extract the channel to be registered
        ch_multiplexed = ch_stainwarpy_input.map { meta, multiplx_img, hne_img, seg_mask ->
            [meta, multiplx_img]
        }
        STAINWARPY_EXTRACTCHANNEL ( ch_multiplexed )
        ch_multiplexed_single_ch = STAINWARPY_EXTRACTCHANNEL.out.single_ch_image

        // join channels and swap multiplex image with single channel multiplexed
        ch_register_input = ch_multiplexed_single_ch
                            .join(ch_stainwarpy_input)
                            .map {
                                meta, single_ch_img, multiplexed_img, hne_img, seg_mask ->
                                    [meta, single_ch_img, hne_img]
                            }
        STAINWARPY_REGISTER (ch_register_input )


    } else {
        ch_register_input = ch_stainwarpy_input.map { meta, multiplx_img, hne_img, seg_mask ->
            [meta, multiplx_img, hne_img]
        }
        STAINWARPY_REGISTER (ch_register_input )
    }


    // transform segmentation masks if they exist
    // filter channel for non-null segmmasks
    ch_transform_input = ch_stainwarpy_input
                        .join(STAINWARPY_REGISTER.out.tform_map)
                        .filter {meta , multiplx_img, hne_img, seg_mask, tform_map -> !seg_mask.isEmpty() }

    STAINWARPY_TRANSFORMSEGMASK (ch_transform_input)
    ch_transformed_segmask = STAINWARPY_TRANSFORMSEGMASK.out.transformed_seg_mask


    emit:
    transformed_image   = STAINWARPY_REGISTER.out.reg_image                     // channel: [ val(meta), *_transformed_image.ome.tif             ]
    metrics             = STAINWARPY_REGISTER.out.reg_metrics_tform             // channel: [ val(meta), *_registration_metrics_tform_map.json   ]
    transformed_segmask = ch_transformed_segmask                                // channel: [ val(meta), *_transformed_segmentation_mask.ome.tif ]
}
