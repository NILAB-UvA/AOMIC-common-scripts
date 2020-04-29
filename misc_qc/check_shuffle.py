import os.path as op
import pandas as pd
import numpy as np
import nibabel as nib
from glob import glob
from scipy.stats import pearsonr
from tqdm import tqdm


def check(bids, bids_anon):
   
    results = dict(raw_t1=[], physio=[], m
    for d in [bids, bids_anon]:
        p_df = pd.read_csv(op.join(d, 'participants.tsv'), sep='\t')
        p_df = p_df.fillna(0)
        age = p_df['age'].to_numpy()

        t1s = sorted(glob(op.join(d, 'sub*', 'anat', '*.nii.gz')))
        x = np.array([nib.load(t1).get_fdata().mean() for t1 in tqdm(t1s)])
        









if __name__ == '__main__':
    import sys
    bids = sys.argv[1]
    bids_anon = sys.argv[2]

    check(bids, bids_anon)
