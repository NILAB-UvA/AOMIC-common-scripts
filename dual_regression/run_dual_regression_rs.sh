set -e
./dual_regression/dual_regression_customized \
    ../derivatives/dual_regression_rs/data/PNAS_Smith09_rsn10_PIOP1.nii.gz \
    1 -1 5000 \
    ../derivatives/dual_regression_rs \
    ../derivatives/dual_regression_rs/data/tpl-MNI152NLin2009cAsym_res-02_desc-brain_mask_PIOP1.nii.gz \
    `ls ../derivatives/dual_regression_rs/preproc/*.nii.gz`
