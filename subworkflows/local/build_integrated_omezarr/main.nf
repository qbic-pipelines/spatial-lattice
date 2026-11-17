include { INTEGRATED_OMEZARR } from '../../../modules/local/integrated_omezarr/main'

// Each tuple contains one acquisition and its matched annotation and registration outputs.
workflow BUILD_INTEGRATED_OMEZARR {
    take:
    ch_inputs
    main:
    INTEGRATED_OMEZARR(ch_inputs)
    emit:
    store = INTEGRATED_OMEZARR.out.store
    qc = INTEGRATED_OMEZARR.out.qc
}
