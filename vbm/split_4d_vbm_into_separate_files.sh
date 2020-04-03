set -e

bids_dir=$1
if [ -z ${bids_dir} ]; then
    echo "ERROR: bids-dir not given!"
    exit 1
fi
vbm4d=${bids_dir}/derivatives/vbm/stats/GM_mod_merg.nii.gz
fslsplit $vbm4d ${bids_dir}/derivatives/vbm/tmp -t

files=($(ls ${bids_dir}/derivatives/vbm/tmp*))
subs=($(ls ${bids_dir}/derivatives/vbm/struc/sub*probseg.nii.gz))
for i in ${!files[@]}; do
  sub=$(basename ${subs[$i]})
  sub=${sub/_label-GM_probseg.nii.gz/}
  sub_deriv_dir=${bids_dir}/derivatives/vbm/${sub}
  if [ ! -d $sub_deriv_dir ]; then
    mkdir $sub_deriv_dir
  fi
  new_name=${sub_deriv_dir}/${sub}_desc-VBM_GMvolume.nii.gz
  mv ${files[$i]} ${new_name}
done

rm -r ${bids_dir}/derivatives/vbm/tmp
