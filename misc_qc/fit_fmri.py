import os
import click
import numpy as np
import pandas as pd
import os.path as op
import nibabel as nib
from tqdm import tqdm
from glob import glob
from joblib import Parallel, delayed
from nistats.first_level_model import FirstLevelModel
from nistats.second_level_model import SecondLevelModel


TASK_INFO = dict(
    anticipation=dict(
        contrast=['img_negative - img_neutral', 'cue_negative - cue_neutral'],
        name=['imgnegGTimgneu', 'cuenegGTcuepos']
    ),
    workingmemory=dict(
        contrast=['active_change + active_nochange - passive', 'active_change - active_nochange'],
        name=['activeGTpassive', 'changeGTnochange']
    ),
    gstroop=dict(
        contrast=['incongruent - congruent'],
        name=['incongruentGTcongruent']
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


def fit_firstlevel(bids_dir, func, task, out_dir):

    sub_base = op.basename(func).split('_')[0]

    mask = func.replace('preproc_bold', 'brain_mask')
    conf = func.split('space')[0] + 'desc-confounds_regressors.tsv'
    conf = pd.read_csv(conf, sep='\t')
    cols = [col for col in conf.columns if 'cosine' in col]
    cols += ['trans_x', 'trans_y', 'trans_z', 'rot_x', 'rot_y', 'rot_z']    
    conf = conf.loc[:, cols]

    events = op.join(bids_dir, sub_base, 'func', op.basename(func).split('space')[0] + 'events.tsv')
    events = pd.read_csv(events, sep='\t')
    
    flm = FirstLevelModel(
        t_r=nib.load(func).header['pixdim'][4],
        slice_time_ref=0.5,
        hrf_model='glover',
        drift_model=None,
        mask_img=mask,
        smoothing_fwhm=None, 
        noise_model='ar1'
    )
    flm.fit(run_imgs=func, events=events, confounds=conf)

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
                break
        else:  # first time I've used a for-else clause I think
            stats = flm.compute_contrast(contrast, output_type='all')            
            f_base = op.basename(func).split('space')[0]
            f_base += f"contrast-{name}"
            f_out = op.join(sub_out, f_base + '_beta.nii.gz')
            stats['effect_size'].to_filename(f_out)
            stats['effect_variance'].to_filename(f_out.replace('beta', 'varbeta'))


@click.command()
@click.argument('bids_dir', type=click.Path())
@click.argument('out_dir', required=False, type=click.Path())
@click.argument('level', default='participant')
@click.option('--task', default='workingmemory')
@click.option('--smoothing', default=None, type=click.FLOAT)
@click.option('--n_jobs', default=1, type=int)
def main(bids_dir, out_dir, level, task, smoothing, n_jobs):
    """ BIDS-app format. """

    if out_dir is None:
        out_dir = op.join(bids_dir, 'derivatives', 'task_fmri')
    
    if level == 'participant':
        fprep_dir = op.join(bids_dir, 'derivatives', 'fmriprep')
        funcs = sorted(glob(op.join(
            fprep_dir, 'sub-*', 'func', f'*task-{task}_*_space-MNI*_desc-preproc_bold.nii.gz'
        )))
        _ = Parallel(n_jobs=n_jobs)(delayed(fit_firstlevel)(bids_dir, f, task, out_dir) for f in tqdm(funcs))
    else:
        for cname in TASK_INFO[task]['name']:
            betas = sorted(glob(op.join(out_dir, 'sub-*', 'firstlevel', f'*task-{task}_*_contrast-{cname}_beta.nii.gz')))
            if not betas:
                print(f"WARNING: did not find betas for contrast {cname}!")
                continue

            dm = pd.DataFrame(np.ones(len(betas)), columns=['intercept'])
            slm = SecondLevelModel(smoothing_fwhm=smoothing)
            slm.fit(betas, design_matrix=dm)
            group_result = slm.compute_contrast(second_level_contrast='intercept', output_type='z_score')
            f_out = op.join(out_dir, f'task-{task}_contrast-{cname}_desc-grouplevel_zscore.nii.gz')
            group_result.to_filename(f_out)


if __name__ == '__main__':
    main()