import os
import sys
import os.path as op
import numpy as np
import pandas as pd
from tqdm import tqdm
from glob import glob
from joblib import Parallel, delayed


def _parallel_proc(sub_dir):
    """ Computes mean FD, linear EC std, prop outliers per slice, prop outliers per volume """    
    eddy_params = op.join(sub_dir, 'eddy_qc', 'eddy_parameters')
    pars = np.loadtxt(eddy_params, skiprows=1)
    diff = pars[:-1, :6] - pars[1:, :6]
    diff[:, 3:6] *= 50
    fd_mean = np.abs(diff).sum(axis=1).mean()

    lin_ecs = pars[:, 6:9].std(axis=0)
    
    outliers_file = op.join(sub_dir, 'eddy_qc', 'eddy_outlier_map')
    outliers = np.loadtxt(outliers_file, skiprows=2)
    if outliers.shape[0] > 33:
        idx = np.ones(outliers.shape[0], dtype=bool)
        idx[32] = False
        if outliers.shape[0] > 65:
            idx[64] = False
        outliers = outliers[idx, :]
    
    return fd_mean, lin_ecs, outliers.sum(), outliers.mean(axis=0) , outliers.mean(axis=1)


if __name__ == '__main__':

    bids_dir = sys.argv[1]
    if not op.isdir(bids_dir):
        raise ValueError(f"{bids_dir} is not a directory!")

    n_jobs = int(sys.argv[2])

    dwipreproc_dir = op.join(bids_dir, 'derivatives', 'dwipreproc')
    sub_dirs = sorted(glob(op.join(dwipreproc_dir, 'sub-*')))
    sub_dirs = [sd for sd in sub_dirs if op.isdir(op.join(sd, 'eddy_qc'))]
    out = Parallel(n_jobs=n_jobs)(delayed(_parallel_proc)(sub_dir) for sub_dir in tqdm(sub_dirs))
     
    df = pd.DataFrame()
    for i, (fd_mean, ecs, ols, ol_per_slice, ol_per_vol) in enumerate(out):
        sub_name = op.basename(sub_dirs[i])
        df.loc[i, 'participant_id'] = sub_name
        df.loc[i, 'FD_mean'] = fd_mean
        df.loc[i, 'total_outliers'] = ols
        for ii, ol in enumerate(ol_per_vol):
            df.loc[i, f'prop_outliers_vol{ii+1}'] = ol

        for ii, ol in enumerate(ol_per_slice):
            df.loc[i, f'prop_outliers_slice{ii+1}'] = ol

        for ii, xyz in enumerate(['x', 'y', 'z']):
            df.loc[i, f'std_ec_{xyz}'] = ecs[ii]

    df.to_csv(op.join(dwipreproc_dir, 'group_dwi.tsv'), sep='\t')
    
