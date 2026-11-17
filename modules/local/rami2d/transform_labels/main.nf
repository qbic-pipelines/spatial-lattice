process RAMI2D_TRANSFORM_LABELS {
    tag "$meta.id"
    label 'process_medium'
    container 'spatial-lattice/rami2d:1.0.2-f6c4cc0'
    input:
    tuple val(meta), path(mask, stageAs: 'labels/*'), path(moving, stageAs: 'moving/*'), path(transforms), val(moving_mpp)
    output:
    tuple val(meta), path('labels_out/*_transformed.tif'), emit: mask
    tuple val("${task.process}"), val('rami2d'), eval('rami2d-transform --version'), emit: version, topic: versions
    when:
    task.ext.when == null || task.ext.when

    script:
    """
    rami2d_provenance.py validate-mask --moving '$moving' --mask '$mask'
    export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=$task.cpus
    rami2d-transform -i '$mask' -mpp $moving_mpp -tdir '$transforms' -labels -o labels_out
    """
    stub:
    """
    mkdir labels_out
    touch labels_out/mask_transformed.tif
    """
}
