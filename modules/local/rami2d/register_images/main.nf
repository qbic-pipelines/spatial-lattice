process RAMI2D_REGISTER_IMAGES {
    tag "$meta.id"
    label 'process_medium'
    container 'spatial-lattice/rami2d:1.0.2-f6c4cc0'
    input:
    tuple val(meta), path(fixed, stageAs: 'fixed/*'), path(moving, stageAs: 'moving/*'), val(settings)
    output:
    tuple val(meta), path('registration/*_registered.ome.tif'), emit: image
    tuple val(meta), path('registration/qc/fullres_trf'), path('settings.json'), path('registration.log'), emit: transforms
    tuple val("${task.process}"), val('rami2d'), eval('rami2d-register --version'), emit: version, topic: versions
    when:
    task.ext.when == null || task.ext.when

    script:
    def initial = settings.initial_alignment ? '-a' : ''
    """
    cat > settings.json <<'SETTINGS'
    ${groovy.json.JsonOutput.toJson(settings)}
    SETTINGS
    rami2d_provenance.py validate --fixed '$fixed' --moving '$moving' --settings settings.json
    export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=$task.cpus
    rami2d-register -fix '$fixed' -mov '$moving' \
        -ifix ${settings.fixed_channel} -imov ${settings.moving_channel} \
        -mpp-fix ${settings.fixed_mpp} -mpp-mov ${settings.moving_mpp} \
        -mpp-reg ${settings.registration_mpp} -mpp-key ${settings.keypoints_mpp} \
        -rsc ${settings.scheme} $initial -pl 4 -comp None -o registration \
        > registration.log 2>&1
    """
    stub:
    """
    mkdir -p registration/qc/fullres_trf
    touch registration/moving_registered.ome.tif registration/qc/fullres_trf/trf_00.txt registration.log
    echo '${groovy.json.JsonOutput.toJson(settings)}' > settings.json
    """
}
