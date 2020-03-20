import os
import click
import numpy as np
import nibabel as nib
import os.path as op
from glob import glob
from tqdm import tqdm
from nilearn import masking, image
from joblib import Parallel, delayed


def _parallel_tsnr(f, out_dir, space='MNI152NLin2009cAsym_desc-preproc_bold.nii.gz'):
    """ Computes TSNR for a surface (gifti) or volume (nifti) file with a 
    time dimension. """
    base_name = op.basename(f).split(space.split('_')[1])[0]
    sub_out = op.join(out_dir, base_name.split('_')[0], 'tsnr')

    if not op.isdir(sub_out):
        os.makedirs(sub_out, exist_ok=True)

    if 'fsaverage' in space:
        gii = nib.load(f)
        dat = np.vstack([arr.data for arr in gii.darrays])
    else:
        mask = f.replace('preproc_bold', 'brain_mask')
        dat = masking.apply_mask(f, mask)
        
    mean_ = dat.mean(axis=0)
    sd_ = dat.std(axis=0)
    tsnr_ = mean_ / sd_
    for tmp in (mean_, sd_, tsnr_):
        tmp[np.isnan(tmp)] = 0

    if 'fsaverage' in space:
        hemi = f.split('hemi-')[1].split('.')[0]
        for mod, metric in [('mean', mean_), ('std', sd_), ('tsnr', tsnr_)]:
            f_out = op.join(sub_out, base_name + f'hemi-{hemi}_{mod}.npy')
            np.save(f_out, metric)
    else:
        for mod, metric in [('mean', mean_), ('std', sd_), ('tsnr', tsnr_)]:
            img_ = masking.unmask(metric, mask)
            f_out = op.join(sub_out, base_name + f'{mod}.nii.gz')
            img_.to_filename(f_out)

def _mean_tsnr(files, out_dir, mod, task, space):
    """ Averages TSNR across subject-level TSNR fles. """
    if 'fsaverage' in space:
        for i, f in enumerate(files):
            if i == 0:
                sum_ = np.load(f)
            else:
                sum_ += np.load(f)

        mean_ = sum_ / len(files)
        mean_[np.isnan(mean_)] = 0 
        f_out = op.join(out_dir, f'task-{task}_space-{space}_desc-mean_{mod}.npy')
        np.save(f_out, mean_)
    else:
        mean_ = image.mean_img(files)
        f_out = op.join(out_dir, f'task-{task}_space-{space}_desc-mean_{mod}.nii.gz')
        mean_.to_filename(f_out)


@click.command()
@click.argument('bids_dir', type=click.Path())
@click.argument('out_dir', required=False, type=click.Path())
@click.argument('level', default='participant')
@click.option('--n_jobs', default=1, type=int)
def main(bids_dir, out_dir, level, n_jobs):
    """ BIDS-app format. """
    
    if out_dir is None:
        out_dir = op.join(bids_dir, 'derivatives', 'tsnr')

    if not op.isdir(out_dir):
        os.makedirs(out_dir)

    fmriprep_dir = op.join(bids_dir, 'derivatives', 'fmriprep')
    print(f"INFO: using data from {fmriprep_dir}")
    print(f"INFO: storing tsnr data in {out_dir}")
    if level == 'participant':
        for space in ('fsaverage5_hemi-L.func.gii', 'fsaverage5_hemi-R.func.gii', 'MNI152NLin2009cAsym_desc-preproc_bold.nii.gz'):
            print(f"INFO: computing TSNR for space {space.split('_')[0]}")
            funcs = sorted(glob(op.join(fmriprep_dir, 'sub-*', 'func', f'*space-{space}')))
            Parallel(n_jobs=n_jobs)(delayed(_parallel_tsnr)(f, out_dir, space) for f in tqdm(funcs))
    elif level == 'group':
        for space in ('fsaverage5_hemi-L', 'fsaverage5_hemi-R', 'MNI152NLin2009cAsym'):
            for mod in ['mean', 'sd', 'tsnr']:
                files = sorted(glob(op.join(out_dir, 'sub-*', 'tsnr', f'*space-{space}*{mod}*')))
                tasks = np.unique([f.split('task-')[1].split('_')[0] for f in files])
                for task in tasks:
                    these_f = [f for f in files if f'task-{task}' in f]
                    print(f"INFO: computing average {mod} for task {task} from {len(these_f)} files.")
                    _mean_tsnr(these_f, out_dir, mod=mod, task=task, space=space)
    else:
        raise ValueError("Level should be 'participant' or 'group'.")
if __name__ == '__main__':

    main()

    
    
