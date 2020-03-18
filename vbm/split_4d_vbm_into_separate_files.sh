set -e

vbm4d=../derivatives/vbm/stats/GM_mod_merg_s3.nii.gz
fslsplit $vbm4d ../derivatives/vbm/tmp -t

files=($(ls ../derivatives/vbm/tmp*))
subs=($(ls ../derivatives/vbm/struc/sub*probseg.nii.gz))
for i in ${!files[@]}; do
  sub=$(basename ${subs[$i]})
  sub=${sub/_label-GM_probseg.nii.gz/}
  sub_deriv_dir=../derivatives/vbm/${sub}
  if [ ! -d $sub_deriv_dir ]; then
    mkdir $sub_deriv_dir
  fi
  new_name=${sub_deriv_dir}/${sub}_desc-VBM_GMvolume.nii.gz
  mv ${files[$i]} ${new_name}
done
