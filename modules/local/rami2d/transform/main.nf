process RAMI2D_TRANSFORM {
    tag "$meta.id"
    label 'process_single'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/55/552fcba4585f006314c7844d547f525edea331b3499bd9051dda85a8f129c474/data':
        'community.wave.seqera.io/library/python_pip_rami2d:24a6fa5cf5184fd7' }"

    input:
    tuple val(meta), path(mov_img_annotation), path(tform_map)

    output:
    tuple val(meta), path("${prefix}"), emit: outdir
    tuple val("${task.process}"), val('rami2d'), eval("rami2d-transform --version"), topic: versions, emit: versions_rami2d

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    prefix = task.ext.prefix ?: "${meta.id}"
    """
    rami2d-transform \\
        -i ${params.rami2d_transform_input} \\
        -mpp ${params.rami2d_transform_mpp} \\
        -tdir ${params.rami2d_transform_tdir} \\
        -o ${prefix} \\
        $args \\
        -@ $task.cpus
    """

    stub:
    def args = task.ext.args ?: ''
    prefix = task.ext.prefix ?: "${meta.id}"
    """
    echo $args

    touch ${prefix}.bam
    """
}
