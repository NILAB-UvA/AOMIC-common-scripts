import os
import os.path as op
import pandas as pd
from nilearn import image, masking, signal
from glob import glob
from joblib import Parallel, delayed
from tqdm import tqdm


def preproc(f, out_dir):
    mask = f.replace('preproc_bold', 'brain_mask')
    if not op.isfile(mask):
        raise ValueError(f"Mask {mask} does not exist.")
    
    conf = f.split('restingstate')[0] + 'restingstate_acq-mb3_desc-confounds_regressors.tsv'
    if not op.isfile(conf):
        raise ValueError(f"Confound file {conf} does not exist.")
    
    masked = masking.apply_mask(f, mask)
    conf = pd.read_csv(conf, sep='\t')
    conf_cols = [col for col in conf.columns if 'cosine' in col] + ['rot_x', 'rot_y', 'rot_z', 'trans_x', 'trans_y', 'trans_z']
    clean = signal.clean(masked, detrend=True, confounds=conf.loc[:, conf_cols].values)
    smooth = image.smooth_img(masking.unmask(clean, mask), fwhm=5)
    
    if not op.isdir(out_dir):
        os.makedirs(out_dir)
    
    f_out = op.basename(f).replace('preproc', 'preproc+masked+hp+motionreg+smooth')
    smooth.to_filename(op.join(out_dir, f_out))


if __name__ == '__main__':
    
    files = sorted(glob('../derivatives/fmriprep/sub*/func/*task-rest*space-MNI*bold.nii.gz'))
    out_dir = '../derivatives/dual_regression_rs/preproc'
    Parallel(n_jobs=10)(delayed(preproc)(f, out_dir) for f in tqdm(files))
