process STAINSEGMY {
    tag "$meta.id"
    label 'process_gpu'

    container "ghcr.io/qbic-pipelines/stainsegmy:b2cdae02ed0ff7116ab8500a83ae14ae55c259aa"

    input:
    tuple val(meta), path(hne_img)

    output:
    tuple val(meta), path("*_hne_segmentation_mask.ome.tif")                     , emit: hne_seg_mask
    tuple val("${task.process}"), val('stainsegmy'), eval("stainsegmy --version"), topic: versions, emit: versions_stainsegmy

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    stainsegmy \\
        -i ${hne_img} \\
        -o . \\
        ${args} \\

    mv Segmentation_mask.ome.tif ${prefix}_hne_segmentation_mask.ome.tif
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """   
    touch ${prefix}_hne_segmentation_mask.ome.tif
    """
}
