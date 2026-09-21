process STAINWARPY_REGISTER {
    tag "$meta.id"
    label 'process_low'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/c0/c020e2c9696127244a6a2bbb1d945b9d78c18d3595bac54838e26bddcc87f521/data' :
        'community.wave.seqera.io/library/stainwarpy:0.2.4--c8bf19657f01e47a'}"

    input:
    tuple val(meta), path(multiplx_img) ,path(hne_img)

    output:
    tuple val(meta), path("*_transformed_image.ome.tif")                                         , emit: reg_image
    tuple val(meta), path("*_registration_metrics_tform_map.json")                               , emit: reg_metrics_tform
    tuple val(meta), path("*_feature_based_transformation_map.npy")                              , emit: tform_map
    tuple val("${task.process}"), val('stainwarpy'), eval("stainwarpy --version | sed 's/.* //'"), emit: versions_stainwarpy, topic: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def fixed_img = params.fixed_img ?: 'multiplexed'
    def final_sz = params.final_sz ?: 'multiplexed'
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"

    """
    stainwarpy \\
        register \\
        ${multiplx_img} \\
        ${hne_img} \\
        . \\
        ${fixed_img} \\
        ${final_sz} \\
        ${args}

    mv 0_final_channel_image.ome.tif ${prefix}_transformed_image.ome.tif
    mv registration_metrics_tform_map.json ${prefix}_registration_metrics_tform_map.json
    mv feature_based_transformation_map.npy ${prefix}_feature_based_transformation_map.npy
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}_transformed_image.ome.tif
    touch ${prefix}_registration_metrics_tform_map.json
    touch ${prefix}_feature_based_transformation_map.npy
    """
}
