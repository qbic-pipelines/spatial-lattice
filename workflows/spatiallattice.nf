/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT MODULES / SUBWORKFLOWS / FUNCTIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
include { MULTIQC                } from '../modules/nf-core/multiqc/main'
include { MCSTAGING_MACSIMA2MC   } from '../modules/nf-core/mcstaging/macsima2mc/main'
include { ASHLAR                 } from '../modules/nf-core/ashlar/main'
include { BACKSUB                } from '../modules/nf-core/backsub/main'
include { paramsSummaryMap       } from 'plugin/nf-schema'
include { paramsSummaryMultiqc   } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { softwareVersionsToYAML } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { methodsDescriptionText } from '../subworkflows/local/utils_nfcore_spatiallattice_pipeline'

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

    // macsima2mc staging
    // input: [ meta, input_dir (parent folder of the raw tiles), output_dir (string) ]
    MCSTAGING_MACSIMA2MC(
        ch_samplesheet.map { meta, raw_images -> [ meta, raw_images, "${meta.id}" ] }
    )

    MCSTAGING_MACSIMA2MC.out.out_dir.view()

    def ch_macsima2mc_out = MCSTAGING_MACSIMA2MC.out.out_dir
        .flatMap { meta, acq_group_dirs ->
            acq_group_dirs.collect { acq_path ->
                def acq_name = acq_path.getFileName().toString()

                // Parse: rack-01-well-C01-roi-001-exp-1
                def parts = acq_name.split('-')
                def rack = parts[1]
                def well = parts[3]
                def roi = parts[5]
                def exposure = parts[7]

                // Get all ome.tif files from the raw subdirectory
                def raw_dir = acq_path.resolve('raw')
                def images = raw_dir.toFile().listFiles()
                    ?.findAll { it.name.endsWith('.ome.tif') || it.name.endsWith('.ome.tiff') }
                    ?.collect { it.toPath() }
                    ?: []

                // Get marker sheet (adjust filename if needed)
                def marker_sheet = acq_path.resolve('markers.csv')

                // Create unique ID for this acquisition group
                def unique_id = "${meta.id}_exp${exposure}"

                def enriched_meta = meta + [
                    id: unique_id,
                    rack: rack,
                    well: well,
                    roi: roi,
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

    // Now you have two separate channels
    def ch_ashlar_i = ch_macsima2mc_out.images
    def ch_markersheet = ch_macsima2mc_out.markers

    ch_ashlar_i.view()
    // ashlar stitching and registration
    ASHLAR(ch_ashlar_i, [], [])

    // background subtraction (optional, off by default)
    if (params.background_subtraction) {

        // merge ashlar output with the corresponding marker sheet by the metamap
        ch_backsub_in = ASHLAR.out.tif
            .join(ch_markersheet)
            .multiMap { meta, ashlar_tif, marker_sheet ->
                images: [meta, ashlar_tif]
                markers: [meta, marker_sheet]
            }

        // seperate agian now that we have the right markersheet for each image into separate channels

        BACKSUB(ch_backsub_in.images, ch_backsub_in.markers)
    }

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
