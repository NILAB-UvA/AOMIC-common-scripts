##### FA TEMPLATE CREATION SCRIPT #####
# Creates an FA template and uses the registration params
# to transform the EVECS data to this template (for visualization)
set -e

if [ -z "$1" ]; then
    echo "ERROR: first argument should be a dwipreproc derivatives directory!"
    exit 1
else
    dwipreproc_dir=$1
fi

if [ -z "$2" ]; then
    n_cores=1
else
    n_cores=$2
fi

if [ -z "$3" ]; then
    out_dir=${dwipreproc_dir}/FA_template
else
    out_dir=$3
fi

if [ ! -d ${out_dir} ]; then
    mkdir ${out_dir}
fi

echo "Running with ${n_cores}."
echo "Creating a template from files in ${dwipreproc_dir}."
echo "Storing outputs in ${out_dir}."

fa_dir=${out_dir}/FAs
mask_dir=${out_dir}/masks
evecs_dir=${out_dir}/EVECS

for d in ${fa_dir} ${mask_dir} ${evecs_dir}; do
    if [ ! -d ${d} ]; then
        mkdir ${d}
    fi
done

sub_dirs=($(find ${dwipreproc_dir} -maxdepth 1 -type d -name sub-* -print0 | sort -z | xargs -r0))
for sub_dir in ${sub_dirs[@]}; do
    sub_base=$(basename ${sub_dir})
    
    fa=${sub_dir}/dwi/${sub_base}_model-DTI_desc-WLS_FA.nii.gz
    cp ${fa} ${fa_dir}/${sub_base}.nii.gz
    
    mask=${sub_dir}/dwi/${sub_base}_desc-brain_mask.nii.gz
    cp ${mask} ${mask_dir}/${sub_base}.nii.gz

    evecs=${sub_dir}/dwi/${sub_base}_model-DTI_desc-WLS_EVECS.nii.gz
    cp ${evecs} ${evecs_dir}/${sub_base}.nii.gz
done

population_template ${fa_dir} ${out_dir}/FA_template.nii.gz \
    -type "rigid_affine_nonlinear" \
    -voxel_size 2 \
    -mask_dir ${mask_dir} \
    -warp_dir ${out_dir}/warps \
    -transformed_dir ${out_dir}/transformed \
    -linear_transformations_dir ${out_dir}/linear_transformations \
    -template_mask ${out_dir}/FA_template_mask.nii.gz \
    -nthreads ${n_cores} \
    -force

for sub_dir in ${sub_dirs[@]}; do
    sub_base=$(basename ${sub_dir})
    warp=${out_dir}/warps/${sub_base}_deform.nii.gz
    warpconvert ${out_dir}/warps/${sub_base}.mif warpfull2deformation ${warp} \
        -template ${out_dir}/FA_template.nii.gz \
        -force
    mrtransform ${evecs_dir}/${sub_base}.nii.gz ${evecs_dir}/${sub_base}_space-template.nii.gz \
        -warp ${warp} \
        -force
done

EVECS_median=${out_dir}/EVECS_median.nii.gz
mrmath $(ls ${evecs_dir}/sub*space-template*.nii.gz) median ${EVECS_median} 

