process RAMI2D_REGISTER {
    tag "$meta.id"
    label 'process_single'

    // TODO nf-core: See section in main README for further information regarding finding and adding container addresses to the section below.
    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/55/552fcba4585f006314c7844d547f525edea331b3499bd9051dda85a8f129c474/data':
        'community.wave.seqera.io/library/python_pip_rami2d:24a6fa5cf5184fd7' }"

    input:
    tuple val(meta), path(img_fixed), path(img_moving)

    output:
    tuple val(meta), path("${prefix}"), emit: outdir
    tuple val("${task.process}"), val('rami2d'), eval("rami2d-register --version"), topic: versions, emit: versions_rami2d

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    prefix = task.ext.prefix ?: "${meta.id}"
    """
    echo ${img_fixed}
    echo ${img_moving}

    echo ${params.rami2d_mpp_fix}
    echo ${params.rami2d_mpp_mov}

    rami2d-register \\
        -fix ${img_fixed} \\
        -mpp-fix ${params.rami2d_mpp_fix} \\
        -ifix ${params.rami2d_ifix} \\
        -mov ${img_moving} \\
        -mpp-mov ${params.rami2d_mpp_mov} \\
        -imov ${params.rami2d_imov} \\
        -mpp-reg ${params.rami2d_mpp_reg} \\
        -o ${prefix} \\
        $args \\
    """

    stub:
    def args = task.ext.args ?: ''
    prefix = task.ext.prefix ?: "${meta.id}"
    """
    echo $args

    touch ${prefix}.ome.tif
    """
}
