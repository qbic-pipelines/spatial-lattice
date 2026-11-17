process INTEGRATED_OMEZARR {
    tag "$meta.id"
    label 'process_medium'
    container 'spatial-lattice/omezarr:rami2d-rfc5-v1'
    input:
    tuple val(meta), path(macsima), path(mask), path(hne), path(native_hne), path(transform), path(metrics), path(markers), path(moving_mask)
    output:
    tuple val(meta), path("*.ome.zarr"), emit: store
    path("integrated_omezarr_mqc.json"), emit: qc
    tuple val("${task.process}"), val('ngff-zarr'), eval("python -c \"from importlib.metadata import version; print(version('ngff-zarr'))\""), emit: version, topic: versions
    when:
    task.ext.when == null || task.ext.when

    script:
    def mask_arg = moving_mask ? "--moving-mask '$moving_mask'" : ''
    def backend = meta.registration_backend ?: 'stainwarpy'
    """
    # RFC-5 adapter includes native-to-resized pixel-centre geometry.
    export XDG_CACHE_HOME=/tmp/ngff-cache
    integrate_omezarr.py --macsima '$macsima' --mask '$mask' --hne '$hne' \
        --native-hne '$native_hne' --transform '$transform' --metrics '$metrics' \
        --backend '$backend' $mask_arg --markers '$markers' --output '${meta.id}.ome.zarr'
    """
    stub:
    """
    mkdir '${meta.id}.ome.zarr'
    echo '{"stub":true}' > '${meta.id}.ome.zarr/zarr.json'
    echo '{"id":"integrated_omezarr","data":{}}' > integrated_omezarr_mqc.json
    """
}
