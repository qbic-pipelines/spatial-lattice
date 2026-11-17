include { MACSIMA_MCMICRO } from '../subworkflows/local/macsima_mcmicro/main'
include { SPATIAL_REGISTRATION_STAINWARPY } from '../subworkflows/local/spatial_registration_stainwarpy/main'
include { SPATIAL_REGISTRATION_RAMI2D } from '../subworkflows/local/spatial_registration_rami2d/main'
include { BUILD_INTEGRATED_OMEZARR } from '../subworkflows/local/build_integrated_omezarr/main'
/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT MODULES / SUBWORKFLOWS / FUNCTIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
include { MULTIQC                    } from '../modules/nf-core/multiqc/main'
include { STAINSEGMY                 } from '../modules/qbic/stainsegmy/main'
include { paramsSummaryMap           } from 'plugin/nf-schema'
include { paramsSummaryMultiqc       } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { softwareVersionsToYAML     } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { methodsDescriptionText     } from '../subworkflows/local/utils_nfcore_spatiallattice_pipeline'

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    RUN MAIN WORKFLOW
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow SPATIALLATTICE {

    take:
    ch_samplesheet // channel: samplesheet read in from --input
    multiqc_config
    multiqc_logo
    multiqc_methods_description
    outdir

    main:

    def ch_versions = channel.empty()
    def ch_multiqc_files = channel.empty()


    // Prototype integration has one backend and a complete reference/moving pair.
    if (params.project)
        error 'The integrated prototype currently requires a per-ROI samplesheet (project mode has no H&E pairing)'
    if (!params.integrated_omezarr)
        error 'BUILD_INTEGRATED_OMEZARR is required in the integrated prototype'
    if (!(params.registration_backend in ['stainwarpy', 'rami2d']))
        error 'registration_backend must be stainwarpy or rami2d'
    if (params.stainwarpy || params.rami2d)
        error 'Replace legacy --stainwarpy/--rami2d flags with --registration_backend stainwarpy|rami2d'
    if (params.fixed_img != 'multiplexed' || params.final_sz != 'multiplexed')
        error 'The prototype uses the MACSima image as the fixed and final reference grid'
    if (params.segmentation != 'cellpose3')
        error 'The integrated prototype currently requires --segmentation cellpose3'

    ch_input = ch_samplesheet.multiMap { meta, macsima, hne ->
        macsima: [meta, macsima]
        hne: [meta, hne]
    }

    MACSIMA_MCMICRO(ch_input.macsima)
    if (params.stainsegmy) {
        STAINSEGMY(ch_input.hne)
    }

    // Key by the full sample/ROI identity. combine allows multiple acquisition
    // exposures to reuse the same moving image; groupTuple rejects ambiguous H&E.
    ch_hne = ch_input.hne.map { meta, image ->
        if (!image) error "Missing H&E image for ${meta.id}"
        [[meta.experiment, meta.sample, meta.rack, meta.well, meta.roi], meta, image]
    }.groupTuple().map { key, metas, images ->
        if (images.size() != 1) error "Duplicate H&E pairing key: ${key}"
        [key, metas[0], images[0]]
    }
    ch_moving_masks = params.stainsegmy
        ? STAINSEGMY.out.hne_seg_mask.map { meta, mask ->
            [[meta.experiment, meta.sample, meta.rack, meta.well, meta.roi], mask]
        }
        : ch_hne.map { key, meta, image -> [key, []] }
    ch_moving = ch_hne.join(ch_moving_masks, failOnDuplicate: true, failOnMismatch: true)
    ch_fixed = MACSIMA_MCMICRO.out.reference.map { meta, image ->
        [[meta.experiment, meta.sample, meta.rack, meta.well, meta.roi], meta, image]
    }
    // Validate both key sets before a keyed one-to-many combination.
    ch_checked_moving = ch_fixed.map { key, meta, image -> [key] }.unique()
        .join(ch_moving, failOnDuplicate: true, failOnMismatch: true)
    ch_registration = ch_fixed.combine(ch_checked_moving, by: 0)
        .map { key, meta, fixed, moving_meta, moving, mask -> [meta, fixed, moving, mask] }

    if (params.registration_backend == 'stainwarpy') {
        SPATIAL_REGISTRATION_STAINWARPY(ch_registration)
        ch_result = SPATIAL_REGISTRATION_STAINWARPY.out.result
    } else {
        SPATIAL_REGISTRATION_RAMI2D(ch_registration)
        ch_result = SPATIAL_REGISTRATION_RAMI2D.out.result
    }

    ch_export = ch_result.map { meta, fixed, native_image, registered, moving_mask, transform, metrics ->
            [meta.id, meta, fixed, registered, native_image, transform, metrics, moving_mask]
        }
        .join(MACSIMA_MCMICRO.out.masks.map { meta, mask -> [meta.id, mask] }, failOnDuplicate: true, failOnMismatch: true)
        .join(MACSIMA_MCMICRO.out.markers.map { meta, markers -> [meta.id, markers] }, failOnDuplicate: true, failOnMismatch: true)
        .map { id, meta, fixed, registered, native_image, transform, metrics, moving_mask, mask, markers ->
            [meta, fixed, mask, registered, native_image, transform, metrics, markers, moving_mask]
        }
    BUILD_INTEGRATED_OMEZARR(ch_export)
    ch_multiqc_files = ch_multiqc_files.mix(BUILD_INTEGRATED_OMEZARR.out.qc)

    //
    // Collate and save software versions
    //
    def topic_versions = channel.topic("versions")
        .distinct()
        .branch { entry ->
            versions_file: entry instanceof Path
            versions_tuple: true
        }

    def topic_versions_string = topic_versions.versions_tuple
        .map { process, tool, version ->
            [ process[process.lastIndexOf(':')+1..-1], "  ${tool}: ${version}" ]
        }
        .groupTuple(by:0)
        .map { process, tool_versions ->
            tool_versions.unique().sort()
            "${process}:\n${tool_versions.join('\n')}"
        }

    def ch_collated_versions = softwareVersionsToYAML(ch_versions.mix(topic_versions.versions_file))
        .mix(topic_versions_string)
        .collectFile(
            storeDir: "${outdir}/pipeline_info",
            name: 'nf_core_'  +  'spatiallattice_software_'  + 'mqc_'  + 'versions.yml',
            sort: true,
            newLine: true
        )

    //
    // MODULE: MultiQC
    //
    ch_multiqc_files = ch_multiqc_files.mix(ch_collated_versions)
    def ch_summary_params = paramsSummaryMap(workflow, parameters_schema: "nextflow_schema.json")
    def ch_workflow_summary = channel.value(paramsSummaryMultiqc(ch_summary_params))
    ch_multiqc_files = ch_multiqc_files.mix(ch_workflow_summary.collectFile(name: 'workflow_summary_mqc.yaml'))
    def ch_multiqc_custom_methods_description = multiqc_methods_description
        ? file(multiqc_methods_description, checkIfExists: true)
        : file("${projectDir}/assets/methods_description_template.yml", checkIfExists: true)
    def ch_methods_description = channel.value(methodsDescriptionText(ch_multiqc_custom_methods_description))
    ch_multiqc_files = ch_multiqc_files.mix(ch_methods_description.collectFile(name: 'methods_description_mqc.yaml', sort: true))
    MULTIQC(
        ch_multiqc_files.flatten().collect().map { files ->
            [
                [id: 'spatiallattice'],
                files,
                multiqc_config
                    ? file(multiqc_config, checkIfExists: true)
                    : file("${projectDir}/assets/multiqc_config.yml", checkIfExists: true),
                multiqc_logo ? file(multiqc_logo, checkIfExists: true) : [],
                [],
                [],
            ]
        }
    )
    emit:
    multiqc_report = MULTIQC.out.report.map { _meta, report -> [report] }.toList() // channel: /path/to/multiqc_report.html
    versions       = ch_versions                 // channel: [ path(versions.yml) ]
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
