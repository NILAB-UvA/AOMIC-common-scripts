set -e

if [ -z "$1" ]; then
    echo "ERROR: you have to provide a BIDS directory as first argument."
    exit 1
fi

bids_dir=$1

echo "Processing BIDS dir ${bids_dir} ..."

if [ -z "$2" ]; then
    n_cores=1
else
    n_cores=$2
fi

echo "Using ${n_cores} cores ..."

if [ -z "$3" ]; then
    out_dir=${bids_dir}/derivatives/dti_fa
else
    out_dir=$3
fi

echo "Setting output directory to ${out_dir} ..."

if [ ! -d ${out_dir} ]; then
    mkdir -p ${out_dir}
fi

tmp_dir=${out_dir}/tmp
if [ ! -d ${tmp_dir} ]; then
    mkdir ${tmp_dir}
fi

sub_dirs=($(ls -d ${bids_dir}/sub-*))
echo "Found ${#sub_dirs[@]} sub dirs!"

for sub_dir in ${sub_dirs[@]}; do
    sub=$(basename ${sub_dir})
    echo "Running BET and DTIFIT on ${sub}"
    dwis=($(find ${sub_dir} -maxdepth 2 -name *_dwi.nii.gz))
    for dwi in ${dwis[@]}; do 
        basen=$(basename ${dwi})
        b0=${tmp_dir}/${basen/.nii.gz/_b0.nii.gz}
        fslroi ${dwi} ${b0} ${idx_b0} 1
        bet ${b0} ${b0} -m -f 0.2 -n -R
        b0_mask=${b0/.nii.gz/_mask.nii.gz}
        fslmaths ${b0_mask} -kernel sphere 2 -ero -bin ${b0_mask} -odt char
        rm ${b0}
        b0_mask=${b0/.nii.gz/_desc-brain_mask.nii.gz}
        bvec=${dwi/.nii.gz/.bvec}
        bval=${dwi/.nii.gz/.bval}

        s_out=${out_dir}/${sub}
        if [ ! -d ${s_out} ]; then
            mkdir ${s_out}
        fi

        dtifit -k ${dwi} -o ${s_out}/${sub}_space-native -m ${b0/.nii.gz/_mask.nii.gz} -r ${bvec} -b ${bval} >/dev/null
        mv ${b0/.nii.gz/_mask.nii.gz} ${s_out}/${sub}_space-native_desc-brain_mask.nii.gz

        for mod in L1 L2 L3 MO S0 V2 V3; do
            rm ${s_out}/${sub}_space-native_${mod}.nii.gz
        done

    done
done

### FNIRT ###
sub_dirs_d=($(ls -d ${out_dir}/sub-*))

for sub_dir in ${sub_dirs_d[@]}; do
    sub=$(basename ${sub_dir})
    echo "Registering ${sub}!"

    imgs=($(ls ${sub_dir}/*space-native*FA.nii.gz))
    for img in ${imgs[@]}; do
        out=${img/native/FSLHCP1065}
        out=${out/.nii.gz/}
        fsl_reg ${img} $FSLDIR/data/standard/FSL_HCP1065_FA_1mm.nii.gz ${out} -FA
        
        md=${img/FA/MD}
        # No clue why I shouldn't use  --premat=${out}.mat, but that messes stuff up
	    applywarp -i ${md} -o ${md/native/FSLHCP1065} -r $FSLDIR/data/standard/FSL_HCP1065_MD_1mm.nii.gz -w ${out}_warp.nii.gz

        v1=${img/FA/V1}
        fslsplit ${v1} ${v1/.nii.gz/_dir}
        for i in 0 1 2; do
            f_in=${v1/.nii.gz/_dir000${i}}
            f_out=${f_in/native/FSLHCP1065}
            applywarp -i ${f_in} -o ${f_out} -r $FSLDIR/data/standard/FSL_HCP1065_FA_1mm.nii.gz -w ${out}_warp.nii.gz
        done
        fslmerge -t ${v1/native/FSLHCP1065} $(ls ${sub_dir}/*space-FSLHCP1065*dir*.nii.gz)
        rm ${sub_dir}/*dir*.nii.gz
        rm ${sub_dir}/*warp*
        rm ${sub_dir}/*.mat
        rm ${sub_dir}/*.log
    done

    #for mod in V1 FA MD; do
    #    echo "Working on ${mod} image"
    #    imgs=($(ls ${sub_dir}/*space-native*${mod}.nii.gz))
    #    for img in ${imgs[@]}; do

    #	    if [ "${mod}" = "V1" ]; then
    #		fslsplit ${img} ${img/.nii.gz/_dir} -t
    #		fslsplit $FSLDIR/data/standard/FSL_HCP1065_V1_1mm.nii.gz ${sub_dir}/tmp_dir -t
    #            for i in 0 1 2; do
    #		    f_in=${img/.nii.gz/_dir000${i}}
    #		    echo "f_in ${f_in}"
    #		    echo "f_out ${f_in/native/FSLHCP1065}"
    #                fsl_reg ${f_in} ${sub_dir}/tmp_dir000${i}.nii.gz ${f_in/native/FSLHCP1065} -FA
    #	        done
    #		fslmerge ${img/native/FSLHCP1065} $(ls ${sub_dir}/*space-FSLHCP1065*dir*.nii.gz) -t
    #		rm ${sub_dir}/*dir*.nii.gz

    #	    else
    #            echo "Not a V1 image!"
    #            out=${img/native/FSLHCP1065}
    #            out=${out/.nii.gz/}
    #            fsl_reg ${img} $FSLDIR/data/standard/FSL_HCP1065_${mod}_1mm.nii.gz ${out} -FA
    #	    fi

    #	    rm ${out}_warp.msf
    #        rm ${out}_warp.nii.gz
    #        rm ${out}.mat
    #        rm ${img/.nii.gz/_to_FSL_HCP1065_${mod}_1mm.log}
    #    done
    #done
done
