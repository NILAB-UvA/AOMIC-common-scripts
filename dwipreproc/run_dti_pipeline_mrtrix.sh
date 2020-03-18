##### SIMPLE DWI PREPROCESSING PIPELINE USING MRTRIX3 AND FSL #####
#
# Lukas Snoek, March 2020

set -e

########### UTILS ############
function check_and_copy {
    # Checks contents and copies them to a
    # new directory for template creation
    dwi=$1
    sub_out=$2
    bval=${dwi/nii.gz/bval}
    if [ ! -f ${bval} ]; then
        echo "ERROR: did not find ${bval}."
        exit 1
    fi
    bvec=${dwi/nii.gz/bvec}
    if [ ! -f ${bvec} ]; then
        echo "ERROR: did not find ${bvec}."
        exit 1
    fi

    # Do actual copying    
    for f in ${dwi} ${bval} ${bvec}; do
        cp ${f} ${sub_out}
    done
}

function concatenate_dwis {
    # If there are multiple DWIs, concatenate them
    # (as well as the bvals and bvecs)
    dwis=$1
    bvecs=$2
    bvals=$3
    sub_out=$4
    sub_base=$(basename $(dirname ${sub_out}))
    fslmerge -t ${sub_out}/${sub_base}_dwi.nii.gz ${dwis[@]}
    paste ${bvecs[@]} > ${sub_out}/${sub_base}_dwi.bvec
    paste ${bvals[@]} > ${sub_out}/${sub_base}_dwi.bval
}
####################################

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
export OMP_NUM_THREADS=${n_cores}

if [ -z "$3" ]; then
    out_dir=${bids_dir}/derivatives/dwipreproc
else
    out_dir=$3
fi

echo "Setting output directory to ${out_dir} ..."

if [ ! -d ${out_dir} ]; then
    mkdir -p ${out_dir}
fi

sub_dirs=($(ls -d ${bids_dir}/sub-*))
echo "Found ${#sub_dirs[@]} sub dirs!"

# Start preprocessing loop across subjects
for sub_dir in ${sub_dirs[@]}; do
    sub_base=$(basename ${sub_dir})
    sub_out=${out_dir}/${sub_base}/dwi

    if [ -f ${sub_out}/${sub_base}_desc-dti_FA.nii.gz ]; then
    	echo "Already preprocessing ${sub_base} - skipping!"
	    continue
    fi

    if [ ! -d ${sub_out} ]; then
        mkdir ${sub_out} -p
    fi

    # Find DWIs and check how many we have
    dwis=($(find ${sub_dir} -maxdepth 2 -name *_dwi.nii.gz -print0 | sort -z | xargs -r0))
    n_dwi=${#dwis[@]}

    # Concatenate or not?
    if [ ${n_dwi} -eq 0 ]; then
        echo "Did not found DWIs for ${sub_base} ..."
        continue
    elif [ ${n_dwi} = 1 ]; then
        # Nothing to concatenate!
        echo "Found exactly one DWI for ${sub_base} ..."
        check_and_copy ${dwis[0]} ${sub_out}
    else
        # Check if the data is complete
        bvals=($(find ${sub_dir} -maxdepth 2 -name *_dwi.bval -print0 | sort -z | xargs -r0))
        bvecs=($(find ${sub_dir} -maxdepth 2 -name *_dwi.bvec -print0 | sort -z | xargs -r0))
        
        for nr in ${#bvals[@]} ${#bvecs[@]}; do
            if [ ! ${nr} -eq ${n_dwi} ]; then
                echo "ERROR: number of DWIs, bvals, and bvecs are not equal."
                exit 1
            fi
        done

        # Let's concatenate the data!
        echo "Found ${n_dwi} DWIs for ${sub_base} - going to merge!"
        concatenate_dwis ${dwis} ${bvecs} ${bvals} ${sub_out} 
    fi

    # These files are now concatenated (if >1)
    dwi=${sub_out}/${sub_base}_dwi.nii.gz
    if [ ! -f ${dwi} ]; then
        echo "ERROR: ${dwi} does not exist."
        exit 1
    fi

    bvec=${dwi/nii.gz/bvec}
    bval=${dwi/nii.gz/bval}

    # Denoise
    denoised=${dwi/_dwi/_desc-denoised_dwi}
    noise_map=${dwi/_dwi/_noisemap}
    dwidenoise ${dwi} ${denoised} \
        -noise ${noise_map} \
        -nthreads 10 \
        -force  

    # Correct gibbs ringing
    mrdegibbs ${denoised} ${denoised} -axes 0,1 -force

    # dwiprepoc
    preproc_dwi=${dwi/_dwi/_desc-preproc_dwi}
    preproc_bvec=${bvec/_dwi/_desc-preproc_dwi}
    preproc_bval=${bval/_dwi/_desc-preproc_dwi}
    
    qc_dir=${sub_out}/eddy_qc
    if [ ! -d ${qc_dir} ]; then
        mkdir ${qc_dir}
    fi

    #seq 0 59 > slspec.txt
    dwipreproc ${denoised} ${preproc_dwi} \
        -rpe_none \
        -pe_dir PA \
        -readout_time 0.1 \
        -eddy_options "--flm=quadratic --slm=linear --repol " \
        -eddyqc_text ${qc_dir} \
        -fslgrad ${bvec} ${bval} \
        -export_grad_fsl ${preproc_bvec} ${preproc_bval} \
        -force

    #rm slspec.txt
    rm ${denoised}  # don't need this anymore

    # biascorrection
    dwibiascorrect ${preproc_dwi} ${preproc_dwi} \
	    -ants \
        -bias ${preproc_dwi/_desc-preproc_dwi/_biasfield} \
	    -fslgrad ${preproc_bvec} ${preproc_bval} \
	    -nthreads ${n_cores} \
	    -force
    
    # Create mask
    mask=${dwi/_dwi/_desc-brain_mask}
    dwi2mask ${preproc_dwi} ${mask} \
        -fslgrad ${preproc_bvec} ${preproc_bval} \
        -force

    # Check grads
    dwigradcheck ${dwi} \
    	-fslgrad ${preproc_bvec} ${preproc_bval} \
    	-export_grad_fsl ${preproc_bvec/_dwi/_tmp} ${preproc_bval/_dwi/_tmp} \
    	-nthreads ${n_cores} \
    	-force

    # Force doesn't work with dwigradcheck, so move back manually
    mv ${preproc_bvec/_dwi/_tmp} ${preproc_bvec}
    mv ${preproc_bval/_dwi/_tmp} ${preproc_bval}

    # dwi2tensor
    tensor=${preproc_dwi/_desc-preproc_dwi/_model-DTI_desc-WLS_diffmodel}
    dwi2tensor ${preproc_dwi} ${tensor} \
        -mask ${mask} \
        -fslgrad ${preproc_bvec} ${preproc_bval} \
    	-force

    # Remove NaNs???
    fslmaths ${tensor} -nan ${tensor}

    # tensor2metric
    fa_out=${tensor/_diffmodel/_FA}
    v1_out=${tensor/_diffmodel/_EVECS}
    tensor2metric -fa ${fa_out} \
        -vector ${v1_out} -num 1 \
	    -modulate none \
	    -mask ${mask} \
	    ${tensor} \
	    -force

    # Remove NaNs
    fslmaths ${v1_out} -nan ${v1_out}

    # register to template
    #fa_reg_out=${fa_out/_desc-dti_FA.nii.gz/_space-FSLHCP1065_desc-dti_FA}
    #echo "fsl_reg:  [....] registering \"${fa_out}\""
    #fsl_reg ${fa_out} $FSLDIR/data/standard/FSL_HCP1065_FA_1mm.nii.gz ${fa_reg_out} -FA
    
    # Do this separately for all vols in v1
    #fslsplit ${v1_out} ${v1_out/.nii.gz/_dir}
    #for i in 0 1 2; do
    #    f_in=${v1_out/.nii.gz/_dir000${i}}
    #    f_out=${f_in/_desc-dti/_space-FSLHCP1065_desc-dti}
    #	echo "applywarp: [$(( ${i} + 1))/3] apply warp to \"${f_in}\""
    #    applywarp -i ${f_in} -o ${f_out} -r $FSLDIR/data/standard/FSL_HCP1065_FA_1mm.nii.gz -w ${fa_reg_out}_warp.nii.gz
    #done
 
    #echo "fslmerge: [....] merging warped V1 volumes into single file"
    #fslmerge -t ${v1_out/_desc-dti/_space-FSLHCP1065_desc-dti} $(ls ${sub_out}/*space-FSLHCP1065*dir*.nii.gz)
    
    # Cleanup
    #rm ${sub_out}/*dir*.nii.gz
    #rm ${sub_out}/*warp*
    #rm ${sub_out}/*.mat
    #rm ${sub_out}/*.log

    # Remove orig files
    rm ${dwi} ${bval} ${bvec}
done

