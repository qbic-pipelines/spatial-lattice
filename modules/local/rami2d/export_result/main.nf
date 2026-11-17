process RAMI2D_EXPORT_RESULT {
    tag "$meta.id"
    label 'process_single'
    container 'spatial-lattice/rami2d:1.0.2-f6c4cc0'
    input:
    tuple val(meta), path(transforms), path(settings), path(registration_log)
    output:
    tuple val(meta), path('transforms.tar'), path('registration.json'), emit: result
    tuple val("${task.process}"), val('rami2d'), eval('rami2d-register --version'), emit: version, topic: versions
    when:
    task.ext.when == null || task.ext.when

    script:
    """
    # Preserve native relative transform links in the archive.
    rami2d_provenance.py export --transforms '$transforms' --settings '$settings' --log '$registration_log'
    """
    stub:
    """
    tar -cf transforms.tar '$transforms'
    echo '{"backend":"rami2d","validation":"stub_only"}' > registration.json
    """
}
