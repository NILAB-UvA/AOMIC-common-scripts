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


TASK_INFO = dict(
    anticipation=dict(
        contrast=['img_negative - img_neutral', 'cue_negative - cue_neutral'],
        name=['imgnegGTimgneu', 'cuenegGTcuepos']
    ),
    workingmemory=dict(
        contrast=['active_change + active_nochange - 2*passive', 'active_change - active_nochange'],
        name=['activeGTpassive', 'changeGTnochange']
    ),
    gstroop=dict(
        column='response_accuracy',
        contrast=['incorrect - correct'],
        name=['incorrectGTcorrect']
    ),
    faces=dict(
        contrast=['joy + anger + pride + contempt - 4*neutral'],
        name=['emoexpGTneutral']
    ),
    emorecognition=dict(
        contrast=['emotion - control'],
        name=['emotionGTcontrol']
    ),
    stopsignal=dict(  # only PIOP2
        contrast=['unsuccesful_stop - go', 'succesful_stop - go', 'unsuccesful_stop - succesful_stop'],
        name=['failedstopGTgo', 'succesfulstopGTgo', 'unsuccesfulstopGTsuccesfulstop']
    )
)


def fit_firstlevel(bids_dir, func, task, space, out_dir):

    sub_base = op.basename(func).split('_')[0]

    conf = func.split('space')[0] + 'desc-confounds_regressors.tsv'
    conf = pd.read_csv(conf, sep='\t')
    cols = [col for col in conf.columns if 'cosine' in col]
    cols += ['trans_x', 'trans_y', 'trans_z', 'rot_x', 'rot_y', 'rot_z']    
    conf = conf.loc[:, cols]

    events = op.join(bids_dir, sub_base, 'func', op.basename(func).split('space')[0] + 'events.tsv')
    events = pd.read_csv(events, sep='\t')

    if 'column' in TASK_INFO[task].keys():
        events = events.drop('trial_type', axis=1)
        events['trial_type'] = events.loc[:, TASK_INFO[task]['column']]
        n_correct = np.sum(events['trial_type'] == 'correct')
        prop_correct = n_correct / events.shape[0]
        if prop_correct < 0.2:
            print(f"{func}: {prop_correct}")
            events['trial_type'] = events['trial_type'].replace({'correct': 'incorrect', 'miss': 'miss', 'incorrect': 'correct'})

    if 'fs' in space:
        func_vol = func.split('space')[0] + 'space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz'
        hdr = nib.load(func_vol).header
        Y = np.vstack([arr.data for arr in nib.load(func).darrays])
    else:
        mask = func.replace('preproc_bold', 'brain_mask')
        Y = masking.apply_mask(func, mask)
        hdr = nib.load(func).header
    
    tr, nvol = hdr['pixdim'][4], hdr['dim'][4]
    frame_times = np.linspace(0.5 * tr, tr * nvol, num=nvol, endpoint=False)
    
    dm = make_first_level_design_matrix(
        frame_times=frame_times, 
        events=events,
        hrf_model='glover',
        drift_model=None,
        add_regs=conf.values,
        add_reg_names=conf.columns.tolist()
    )

    Y -= Y.mean(axis=0)
    X = dm.to_numpy()
    labels, results = run_glm(Y=Y, X=X, noise_model='ar1')

    sub_out = op.join(out_dir, sub_base, 'firstlevel')
    if not op.isdir(sub_out):
        os.makedirs(sub_out)

    for contrast, name in zip(TASK_INFO[task]['contrast'], TASK_INFO[task]['name']):
        items = contrast.replace('-', '').replace('+', '').replace('*', '').split(' ')
        items = [i for i in items if i]
        trial_types = events['trial_type'].unique().tolist()
        for item in items:
            item = ''.join([i for i in item if not i.isdigit()])
            if item not in trial_types:
                break  # condition not present in event file
        else:  # first time I've used a for-else clause I think
            con_val = expression_to_contrast_vector(contrast, dm.columns)
            con = compute_contrast(labels, results, con_val)
            #stats = flm.compute_contrast(contrast, output_type='all')            
            f_base = op.basename(func).split('.')[0]
            f_base += f"_contrast-{name}"
            if 'fs' in space:
                f_out = op.join(sub_out, f_base + '_beta.npy')
                np.save(f_out, con.effect_size())
                np.save(f_out.replace('beta', 'varbeta'), con.effect_variance())
            else:         
                f_out = op.join(sub_out, f_base + '_beta.nii.gz')
                masking.unmask(con.effect_size(), mask).to_filename(f_out)
                masking.unmask(con.effect_variance(), mask).to_filename(f_out.replace('beta', 'varbeta'))


@click.command()
@click.argument('bids_dir', type=click.Path())
@click.argument('out_dir', required=False, type=click.Path())
@click.argument('level', default='participant')
@click.option('--task', default='workingmemory')
@click.option('--space', default='MNI152NLin2009cAsym')
@click.option('--smoothing', default=None, type=click.FLOAT)
@click.option('--n_jobs', default=1, type=int)
def main(bids_dir, out_dir, level, task, space, smoothing, n_jobs):
    """ BIDS-app format. """

    if out_dir is None:
        out_dir = op.join(bids_dir, 'derivatives', 'task_fmri')
    
    if level == 'participant':
        ext = 'func.gii' if 'fs' in space else 'desc-preproc_bold.nii.gz'
        fprep_dir = op.join(bids_dir, 'derivatives', 'fmriprep')
        funcs = sorted(glob(op.join(
            fprep_dir, 'sub-*', 'func', f'*task-{task}_*_space-{space}*{ext}'
        )))
        print(op.join(
            fprep_dir, 'sub-*', 'func', f'*task-{task}_*_space-{space}*{ext}'
        ))
        _ = Parallel(n_jobs=n_jobs)(delayed(fit_firstlevel)(bids_dir, f, task, space, out_dir) for f in tqdm(funcs))
    else:
        for cname in TASK_INFO[task]['name']:
            ext = 'npy' if 'fs' in space else 'nii.gz'
            to_iter = ['_hemi-L', '_hemi-R'] if 'fs' in space else ['']
            for s in to_iter:
                betas = sorted(glob(op.join(out_dir, 'sub-*', 'firstlevel', f'*task-{task}_*{s}_contrast-{cname}_beta.{ext}')))
                if not betas:
                    print(f"WARNING: did not find betas for contrast {cname}!")
                    continue

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
                group_result = compute_contrast(labels, results, [1], contrast_type='t')
                if 'fs' in space:
                    f_out = op.join(out_dir, f'task-{task}_contrast-{cname}{s}_desc-grouplevel_zscore.npy')
                    np.save(f_out, group_result.z_score())
                else:
                    f_out = op.join(out_dir, f'task-{task}_contrast-{cname}_desc-grouplevel_zscore.nii.gz')
                    to_save = masking.unmask(group_result.z_score(), mask)
                    to_save.to_filename(f_out)

if __name__ == '__main__':
    main()
