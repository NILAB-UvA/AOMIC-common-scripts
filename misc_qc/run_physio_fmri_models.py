import os
import click
import numpy as np
import pandas as pd
import os.path as op
import nibabel as nib
from tqdm import tqdm
from glob import glob
from joblib import Parallel, delayed
from nilearn import masking, image
from nistats.design_matrix import make_first_level_design_matrix
from nistats.first_level_model import run_glm
from nistats.contrasts import compute_contrast, expression_to_contrast_vector
from nistats.second_level_model import SecondLevelModel


def fit_firstlevel(bids_dir, sub, acq, space, out_dir):

    sub_base = op.basename(sub)
    ext = 'func.gii' if 'fs' in space else 'desc-preproc_bold.nii.gz'
        
    funcs = sorted(glob(op.join(
        sub, 'func', f'*{acq}*_space-{space}*{ext}'
    )))
    
    to_save = ['resp', 'cardiac', 'interaction', 'hrv', 'rvt']
    cons = {}
    for func in funcs:
        f_base = op.basename(func).split('space')[0]
        ricor = op.join(bids_dir, 'derivatives', 'physiology', sub_base, 'physio', f_base + 'recording-respcardiac_desc-retroicor_regressors.tsv')
        if not op.isfile(ricor):
            continue

        ricor = pd.read_csv(ricor, sep='\t')
        conf = op.join(bids_dir, 'derivatives', 'fmriprep', sub_base, 'func', f_base + 'desc-confounds_regressors.tsv')
        conf = pd.read_csv(conf, sep='\t')
        cols = [col for col in conf.columns if 'cosine' in col]
        cols += ['trans_x', 'trans_y', 'trans_z', 'rot_x', 'rot_y', 'rot_z']    
        conf = conf.loc[:, cols]
        dm = pd.concat((conf, ricor), axis=1)

        if 'fs' in space:
            Y = np.vstack([arr.data for arr in nib.load(func).darrays])
        else:
            mask = func.replace('preproc_bold', 'brain_mask')
            Y = masking.apply_mask(func, mask)

        Y -= Y.mean(axis=0)
        X = dm.to_numpy()
        labels, results = run_glm(Y=Y, X=X, noise_model='ar1')

        for contrast in dm.columns.tolist():
            if not any(ts in contrast for ts in to_save):
                continue

            con_val = expression_to_contrast_vector(contrast, dm.columns)
            this_beta = compute_contrast(labels, results, con_val).effect_size()
            if not contrast in cons.keys():
                cons[contrast] = []
            
            if 'fs' not in space:
                this_beta = masking.unmask(this_beta, mask)

            cons[contrast].append(this_beta)
    
    sub_out = op.join(out_dir, sub_base, 'firstlevel')
    if not op.isdir(sub_out):
        os.makedirs(sub_out)

    f_base = sub_base + acq
    for contrast, values in cons.items():

        if 'fs' in space:
            mean_con = np.r_[values].mean(axis=0)
        else:
            mean_con = image.mean_img(values)

        f_base_con = f_base + f"_contrast-{contrast}"
        if 'fs' in space:
            f_out = op.join(sub_out, f_base_con + '_beta.npy')
            np.save(f_out, mean_con)
        else:         
            f_out = op.join(sub_out, f_base_con + '_beta.nii.gz')
            mean_con.to_filename(f_out)
    

@click.command()
@click.argument('bids_dir', type=click.Path())
@click.argument('out_dir', required=False, type=click.Path())
@click.argument('level', default='participant')
@click.option('--acq', default=None)
@click.option('--space', default='MNI152NLin2009cAsym')
@click.option('--smoothing', default=None, type=click.FLOAT)
@click.option('--n_jobs', default=1, type=int)
def main(bids_dir, out_dir, level, acq, space, smoothing, n_jobs):
    """ BIDS-app format. """

    if acq is None:
        acq = ''
    else:
        acq = f'_acq-{acq}'

    if out_dir is None:
        out_dir = op.join(bids_dir, 'derivatives', 'physio_fmri')
    
    if level == 'participant':
        fprep_dir = op.join(bids_dir, 'derivatives', 'fmriprep')
        subs = sorted(glob(op.join(fprep_dir, 'sub-????')))
        _ = Parallel(n_jobs=n_jobs)(delayed(fit_firstlevel)(bids_dir, sub, acq, space, out_dir) for sub in tqdm(subs))
    else:
        ext = 'npy' if 'fs' in space else 'nii.gz'
        to_iter = ['_hemi-L', '_hemi-R'] if 'fs' in space else ['']
        for cname in ['resp*', 'cardiac*', 'interaction*', 'hrv', 'rvt']:
            for s in to_iter:
                betas = sorted(glob(op.join(out_dir, 'sub-*', 'firstlevel', f'*{acq}*{s}_contrast-{cname}*_beta.{ext}')))
                if not betas:
                    print(f"WARNING: did not find betas for contrast {cname}!")
                    continue
                else:
                    print(f"INFO: found {len(betas)} images for {cname}!")

                if '*' in cname:
                   types = [op.basename(f).split('contrast-')[1].split('_beta')[0] for f in betas]
                   dm = pd.DataFrame(types, columns=['ricor'])
                   dm = pd.get_dummies(dm)
                else:
                    dm = pd.DataFrame(np.ones(len(betas)), columns=['intercept'])

                if 'fs' not in space:
                    if smoothing is not None:
                        betas = [image.smooth_img(b, smoothing) for b in betas]
                    
                    mean_img = image.mean_img(betas)
                    mask = (mean_img.get_fdata() != 0).astype(int)
                    mask = nib.Nifti1Image(mask, affine=mean_img.affine)
                    Y = masking.apply_mask(betas, mask)
                else:
                    Y = np.vstack([np.load(b) for b in betas])

                labels, results = run_glm(Y, dm.values, noise_model='ols', n_jobs=n_jobs)
                if '*' in cname:
                    cname = cname.replace('*', '')
                    these_cols = [col for col in dm.columns if cname in col]
                    con_def = np.eye(len(these_cols))
                    con_type = 'F'
                else:
                    con_def = [1]
                    con_type = 't'

                cname = cname.replace('*', '')
                group_result = compute_contrast(labels, results, con_def, contrast_type=con_type)
                out = group_result.z_score()

                if 'fs' in space:
                    f_out = op.join(out_dir, f'contrast-{cname}{s}{acq}_desc-grouplevel_zscore.npy')
                    np.save(f_out, out)
                else:
                    f_out = op.join(out_dir, f'contrast-{cname}{acq}_desc-grouplevel_zscore.nii.gz')
                    to_save = masking.unmask(out, mask)
                    to_save.to_filename(f_out)

if __name__ == '__main__':
    main()
