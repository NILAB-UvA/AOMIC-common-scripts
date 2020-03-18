import yaml
import random
import logging
import shutil
import os
import json
import pandas as pd
import os.path as op
from glob import glob
from tqdm import tqdm
from joblib import delayed, Parallel


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(funcName)-8.8s] [%(levelname)-7.7s]  %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler()
    ]
)


EXCLUDE_FROM_CHECK = [
    'gz', 'm3z', 'mgh', 'mgz', 'gii', 'h5', 'svg', 'edf', 'phy',
    'area', 'mid', 'pial', 'avg_curv', 'curv', 'defect_borders', 'defect_chull',
    'defect_labels', 'inflated', 'H', 'K', 'nofix', 'jacobian_white', 'midthickness',
    'orig', 'smoothwm', 'crv', 'sphere', 'reg', 'sulc', 'thickness', 'volume', 'preaparc',
    'white'
]


def _fix_permissions(root_dir):
    """ Sets default permissions for dirs (0755)
    and files (0644). """
    for root, _, files in os.walk(root_dir):
        os.chmod(root, 0o755)
        for f in files:
            os.chmod(op.join(root, f), 0o644)


def _check_contents_for_id(f):

    with open(f, 'r') as f_in:
        data = f_in.read()

    if 'sub-' in data:
        raise ValueError(f"File {f} contains the word 'sub-'.")


def _check_contents_for_id_and_replace(f, old_id, new_id):
    
    try:
        with open(f, 'r') as f_in:
            data = f_in.read()
    except UnicodeDecodeError:
        return 

    data = data.replace(old_id, new_id)
    data = data.replace(  # for fmriprep work-dir paths
        'subject_' + old_id.split('-')[1],
        'subject_' + new_id.split('-')[1],    
    )
    data = data.replace(  # for fmriprep HTML reports
        'Subject ID: ' + old_id.split('-')[1],
        'Subject ID: ' + new_id.split('-')[1],    
    )
    data = data.replace(  # for fmriprep HTML reports
        'participant-label ' + old_id.split('-')[1],
        'participant-label ' + new_id.split('-')[1],    
    )
    data = data.replace(  # for MRIQC jsons
        f"\"subject_id\": \"{old_id.split('-')[1]}\"",
        f"\"subject_id\": \"{new_id.split('-')[1]}\""
    )

    with open(f, 'w') as f_out:
        f_out.write(data)


def _copy_file_and_check(to_copy, bids_dir, out_dir, mapping, old_id=None):
    src = op.join(bids_dir, to_copy)
    dst = op.join(out_dir, to_copy)
    if op.isfile(src):
        shutil.copyfile(src, dst)
        os.chmod(dst, 0o644)
    else:
        return None

    base_dst = op.basename(dst)
    if 'sub-' in op.basename(base_dst):
        old_id = base_dst.split('.')[0].split('_')[0]
        dst_new = op.join(op.dirname(dst), base_dst.replace(old_id, mapping[old_id]))
        os.rename(dst, dst_new)
        dst = dst_new
    
    if old_id is not None:
        ext = dst.split('.')[-1]
        if ext not in EXCLUDE_FROM_CHECK:
            _check_contents_for_id_and_replace(dst, old_id, mapping[old_id])

    return dst


def _recursive_walk(d, mapping, old_id=None, new_id=None):
    for root, _, files in os.walk(d):
        root_base = op.basename(root)
        if f'sub-{old_id}' in root_base:
            root_new_base = root_base.replace(old_id, new_id)
            root_new = op.join(op.dirname(root), root_new_base)
            os.rename(root, root_new)
            # Because we renamed, we need to run it again
            _recursive_walk(root_new, mapping, old_id=old_id, new_id=new_id)

        for f in files:
            f_full = op.join(root, f)
            if 'sub-' in f:
                old_id = f.split('_')[0]
                f_new = op.join(root, f.replace(old_id, mapping[old_id]))
                os.rename(f_full, f_new)
                f_full = f_new

            ext = f.split('.')[-1]
            if ext not in EXCLUDE_FROM_CHECK and old_id is not None:
                _check_contents_for_id_and_replace(f_full, old_id, mapping[old_id])


def _copy_dir_and_check(to_copy, bids_dir, out_dir, mapping, old_id=None):
    src = op.join(bids_dir, to_copy)
    if 'sub-' in op.basename(src):
        old_id = op.basename(src).split('_')[0].split('.')[0]
        new_id = mapping[old_id]
        dst = op.join(out_dir, op.dirname(to_copy), op.basename(to_copy).replace(old_id, new_id))
    else:
        new_id = None
        dst = op.join(out_dir, to_copy)
    
    if op.isdir(src) and not op.isdir(dst):
        #print(f'src: {src}')
        #print(f'dst: {dst}')
    
        shutil.copytree(src, dst)
        _fix_permissions(dst)
        _recursive_walk(dst, mapping, old_id=old_id, new_id=new_id)

def _delete(all_data):

    for d in all_data:
        if op.isfile(d):
            os.remove(d)
        else:
            shutil.rmtree(d)


def main(bids_dir, out_dir, seed=None, n_jobs=1, skip=None):
    """ Anonymizes a BIDS directory by shuffling subject IDs.

    Parameters
    ----------
    bids_dir : str
        Path to BIDS directory.
    out_dir : str
        Output directory for shuffled data. If None, 'bids_anon' is used.
    seed : int
        Random seed for shuffling.
    """
    
    if skip is None:
        skip = []

    if bids_dir == out_dir:
        raise ValueError("bids_dir and out_dir are the same!")
    
    #resp = input(f'Going to remove contents from {op.abspath(out_dir)}, continue? (y, n) ')
    resp = 'y'
    if resp in ['y', 'Y']:
        if 'bids' not in skip:
            to_remove = [f for f in glob(op.join(out_dir, '*')) if f != 'derivatives']
            _delete(to_remove)

        for ddir in ['fmriprep', 'mriqc', 'physiology', 'freesurfer']:
            if ddir not in skip:
                _delete(glob(op.join(out_dir, 'derivatives', ddir, '*')))

    log = logging.getLogger(__name__)
    
    bids_subs = sorted(  # find BIDS subject directories
        [d for d in glob(op.join(bids_dir, 'sub-*'))
        if op.isdir(d)]
    )
    
    bids_unique = sorted(list(set([op.basename(d) for d in bids_subs])))
    log.info(f"Found {len(bids_unique)} unique BIDS directories.")

    all_files = sorted(glob(op.join(bids_dir, '**', 'sub-*'), recursive=True))
    all_unique = sorted(list(set([op.basename(f).split('_')[0].split('.')[0] for f in all_files])))
    log.info(f"Found {len(all_unique)} unique files.")

    # Check if the derivatives do not contain subs that do not have BIDS files
    diff = set(all_unique) - set(bids_unique)
    if diff:
        raise ValueError(f"Found files that do not have a BIDS dir: {diff}")
    
    random.seed(seed)  # set random seed
    new_ids = ['sub-' + str(i).zfill(4) for i in range(1, 1+len(bids_unique))]
    random.shuffle(new_ids)
    mapping = {bids_unique[i]: new_ids[i] for i in range(len(bids_unique))}
    for k, v in mapping.items():
        if k == v:
            raise ValueError(f"Mapping is the same for {k}!")

    ##### 0. Code
    _copy_dir_and_check('code', bids_dir, out_dir, mapping, old_id=None)

    ##### 1. Random stuff
    dst = _copy_file_and_check('participants.tsv', bids_dir, out_dir, mapping, old_id=None)

    if dst is not None:
        df = pd.read_csv(dst, sep='\t').set_index('participant_id')
        df = df.loc[bids_unique, :].reset_index()
        df['participant_id'] = new_ids
        df = df.sort_values('participant_id', axis=0).fillna('n/a')
        df.to_csv(dst, sep='\t', index=False)
    
    md_files = [f for f in glob(op.join(bids_dir, '*')) if op.isfile(f)]
    for f in md_files:
        if op.basename(f) in ['participants.tsv', 'LICENSE', 'README.md']:
            continue

        _copy_file_and_check(op.basename(f), bids_dir, out_dir, mapping, old_id=None)
    
    ##### 2. BIDS data
    ### 2.1. Sub-directories
    Parallel(n_jobs=n_jobs)(delayed(_copy_dir_and_check)
        (op.basename(sub_dir), bids_dir, out_dir, mapping)
        for sub_dir in tqdm(bids_subs, desc='bids')
    )

    ##### 2. Derivatives
    ### 2.1. Fmriprep
    fmriprep_dir = op.join('derivatives', 'fmriprep')
    _copy_dir_and_check(op.join(fmriprep_dir, 'logs'), bids_dir, out_dir, mapping)
    for f in ['dataset_description.json', 'desc-aparcaseg_dseg.tsv', 'desc-aseg_dseg.tsv']:
        to_check = op.join('derivatives', 'fmriprep', f)
        _copy_file_and_check(to_check, bids_dir, out_dir, mapping)

    sub_dirs = [d for d in sorted(glob(op.join(bids_dir, fmriprep_dir, 'sub-*')))
                if op.isdir(d)]
    #for sub_dir in tqdm(sub_dirs):
    #    _copy_dir_and_check(op.join(fmriprep_dir, op.basename(sub_dir)), bids_dir, out_dir, mapping)
    Parallel(n_jobs=n_jobs)(delayed(_copy_dir_and_check)
        (op.join(fmriprep_dir, op.basename(sub_dir)), bids_dir, out_dir, mapping)
        for sub_dir in tqdm(sub_dirs, desc='fmriprep dir')
    )
    
    html_files = sorted(glob(op.join(bids_dir, fmriprep_dir, 'sub-*.html')))
    Parallel(n_jobs=n_jobs)(delayed(_copy_file_and_check)
        (op.join(fmriprep_dir, op.basename(f)), bids_dir, out_dir, mapping)
        for f in tqdm(html_files, desc='fmriprep html')
    )

    ### 2.2. Freesurfer
    fs_dir = op.join('derivatives', 'freesurfer')
    fsav_dirs = glob(op.join(bids_dir, fs_dir, 'fsaverage*'))
    for fsav_dir in fsav_dirs:
        _copy_dir_and_check(op.join(fs_dir, op.basename(fsav_dir)), bids_dir, out_dir, mapping)
    
    sub_dirs = sorted(glob(op.join(bids_dir, fs_dir, 'sub-*')))
    Parallel(n_jobs=n_jobs)(delayed(_copy_dir_and_check)
        (op.join(fs_dir, op.basename(sub_dir)), bids_dir, out_dir, mapping)
        for sub_dir in tqdm(sub_dirs, desc='freesurfer')
    )

    ### 2.3. MRIQC
    mriqc_dir = op.join('derivatives', 'mriqc')
    sub_dirs = sorted(glob(op.join(bids_dir, mriqc_dir, 'sub-*')))
    Parallel(n_jobs=n_jobs)(delayed(_copy_dir_and_check)
        (op.join(mriqc_dir, op.basename(sub_dir)), bids_dir, out_dir, mapping)
        for sub_dir in tqdm(sub_dirs, desc='mriqc dir')
    )
    
    html_files = glob(op.join(bids_dir, mriqc_dir, 'sub-*.html'))
    Parallel(n_jobs=n_jobs)(delayed(_copy_file_and_check)
        (op.join(mriqc_dir, op.basename(f)), bids_dir, out_dir, mapping)
        for f in tqdm(html_files, desc='mriqc html')
    )

    ### 2.4. physiology
    physio_dir = op.join('derivatives', 'physiology')
    sub_dirs = sorted(glob(op.join(bids_dir, physio_dir, 'sub-*')))
    Parallel(n_jobs=n_jobs)(delayed(_copy_dir_and_check)
        (op.join(physio_dir, op.basename(sub_dir)), bids_dir, out_dir, mapping)
        for sub_dir in tqdm(sub_dirs, desc='physio')
    )

    # Double check
    _fix_permissions(out_dir)

if __name__ == '__main__':
    project = op.basename(op.dirname(__file__))
    with open('../RND_SEEDS.yml', 'r') as f_in:
        rnd_seeds = yaml.safe_load(f_in)
        seed = rnd_seeds[project]

    main('bids', 'bids_anon', seed=seed, n_jobs=1, skip=['bids', 'fmriprep'])
