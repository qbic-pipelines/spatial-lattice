include { MCSTAGING_MACSIMA2MC } from '../../../modules/nf-core/mcstaging/macsima2mc/main'
include { ASHLAR } from '../../../modules/nf-core/ashlar/main'
include { BACKSUB } from '../../../modules/nf-core/backsub/main'
include { MACSIMA_SEGMENTATION } from '../macsima_segmentation/main'

workflow MACSIMA_MCMICRO {
    take:
    ch_raw // [meta, raw MACSima ROI directory]
    main:
    // macsima2mc staging
    MCSTAGING_MACSIMA2MC(
        ch_raw.map { meta, raw_images -> [ meta, raw_images, "${meta.sample}" ] }
    )

    // add metadata to the macsima2mc output for downstream processing
    // get markersheet and images from the macsima2mc output
    def ch_macsima2mc_out = MCSTAGING_MACSIMA2MC.out.out_dir
        .flatMap { meta, acq_group_dirs ->
            def acq_paths = acq_group_dirs instanceof List ? acq_group_dirs : [acq_group_dirs]
            acq_paths.collect { acq_path ->
                def acq_name = acq_path.getFileName().toString()
                // Parse: rack-01-well-C01-roi-001-exp-1
                def parts = acq_name.split('-')
                // Derive the exposure from the 'exp-<value>' token instead of a
                // hard-coded index, so varying acquisition-group name formats
                // (e.g. the stub's 'well-rack-roi-exp') do not break parsing.
                def exp_idx = parts.findIndexOf { token -> token == 'exp' }
                def exposure = (exp_idx >= 0 && exp_idx + 1 < parts.size()) ? parts[exp_idx + 1] : parts[-1]

                // Get all ome.tif files from the raw subdirectory
                def raw_dir = acq_path.resolve('raw')
                def images = raw_dir.toFile().listFiles()
                    ?.findAll { it -> it.name.endsWith('.ome.tif') || it.name.endsWith('.ome.tiff') }
                    ?.collect { it -> it.toPath() }
                    ?: []

                // Get marker sheet (adjust filename if needed)
                def marker_sheet = acq_path.resolve('markers.csv')
                // Create unique ID for this acquisition group
                def unique_id = "${meta.id}_exp${exposure}"

                def enriched_meta = meta + [
                    id: unique_id,
                    exposure: exposure,
                    acquisition_group: acq_name
                ]

                [enriched_meta, images, marker_sheet]
            }
        }
        .multiMap { meta, images, marker_sheet ->
            images: [meta, images]
            markers: [meta, marker_sheet]
    }

    // Separate images and marker sheets for downstream modules.
    def ch_ashlar_in = ch_macsima2mc_out.images
    def ch_markersheet = ch_macsima2mc_out.markers

    // ashlar stitching and registration
    ASHLAR(ch_ashlar_in, [], [])

    // background subtraction (optional, off by default)
    if (params.background_subtraction) {

        // merge ashlar output with the corresponding marker sheet by the metamap
        ch_backsub_in = ASHLAR.out.tif
            .join(ch_markersheet, failOnDuplicate: true, failOnMismatch: true)
            .multiMap { meta, ashlar_tif, marker_sheet ->
                images: [meta, ashlar_tif]
                markers: [meta, marker_sheet]
            }

        BACKSUB(ch_backsub_in.images, ch_backsub_in.markers)

        // segment the background subtracted image
        ch_segmentation_in = BACKSUB.out.backsub_tif
    }
    else {
        ch_segmentation_in = ASHLAR.out.tif
    }

    // segmentation of the multiplexed image with the tool(s) selected via --segmentation
    segmentation_methods = params.segmentation
        ? params.segmentation.tokenize(',').collect { method -> method.trim() }.unique()
        : []

    ch_masks = channel.empty()
    if (segmentation_methods) {
        MACSIMA_SEGMENTATION(ch_segmentation_in, segmentation_methods)
        ch_masks = MACSIMA_SEGMENTATION.out.masks
    }

    emit:
    reference = ASHLAR.out.tif // Preserve the established registration/export image.
    segmentation_image = ch_segmentation_in
    masks = ch_masks
    markers = ch_markersheet
}
