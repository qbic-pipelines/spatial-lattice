include { BUILD_INTEGRATED_OMEZARR } from '../subworkflows/local/build_integrated_omezarr/main'
workflow {
    base = '/home/ubuntu/Caro/spl-out'
    ch = Channel.of([
        [id: 'SAMPLE_1_exp2'],
        file(base+'/ashlar/SAMPLE_1/test/SAMPLE_1_exp2.ome.tif', checkIfExists:true),
        file(base+'/cellpose/SAMPLE_1/test/SAMPLE_1_exp2.ome_cp_masks.tif', checkIfExists:true),
        file(base+'/stainwarpy/SAMPLE_1_exp2_transformed_image.ome.tif', checkIfExists:true),
        file('/home/ubuntu/Caro/hne_crop/20241031_CRC027_crop.ome.tif', checkIfExists:true),
        file(base+'/stainwarpy/SAMPLE_1_exp2_feature_based_transformation_map.npy', checkIfExists:true),
        file(base+'/stainwarpy/SAMPLE_1_exp2_registration_metrics_tform_map.json', checkIfExists:true),
        file(base+'/macsima2mc/SAMPLE_1/test/rack-01-well-A01-roi-001-exp-2/markers.csv', checkIfExists:true), []
    ])
    BUILD_INTEGRATED_OMEZARR(ch)
}
