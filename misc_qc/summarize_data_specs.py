import os.path as op
import pandas as pd
import numpy as np
import nibabel as nib
from glob import glob
from tqdm import tqdm


def summarize_data_specs(data_dir, out_dir=None):

    if out_dir is None:
        out_dir = data_dir

    files = sorted(glob(op.join(data_dir, 'sub-*', '*', '*.nii.gz')))

    if not files:
        files = sorted(glob(op.join(data_dir, 'sub-*', '*', 'ses-*', '*.nii.gz')))
   
    files = [f for f in files if 'bold.' in f or 'T1w.' in f or 'dwi.' in f or 'phasediff' in f]

    n = len(files)
    df = dict(
        x_dim=np.zeros(n),
        y_dim=np.zeros(n),
        z_dim=np.zeros(n),
        dyns=np.zeros(n),
        x_pixdim=np.zeros(n),
        y_pixdim=np.zeros(n),
        z_pixdim=np.zeros(n),
        TR=np.zeros(n)
    )

    for i, f in enumerate(tqdm(files)):
        img = nib.load(f)
        hdr = img.header
        df['x_dim'][i] = hdr['dim'][1]
        df['y_dim'][i] = hdr['dim'][2]
        df['z_dim'][i] = hdr['dim'][3]
        
        if len(img.shape) == 4:
            df['dyns'][i] = hdr['dim'][4]
            df['TR'][i] = hdr['pixdim'][4]
        else:
            df['dyns'][i] = np.nan
            df['TR'][i] = np.nan

        df['x_pixdim'][i] = hdr['pixdim'][1]
        df['y_pixdim'][i] = hdr['pixdim'][2]
        df['z_pixdim'][i] = hdr['pixdim'][3]
    
    df['files'] = [op.basename(f) for f in files]
    df['participant_label'] = [op.basename(f).split('_')[0] for f in files]
    df['data_type'] = [op.basename(op.dirname(f)) for f in files]
    df['file_type'] = [op.basename(f).split('_')[-1].split('.')[0] for f in files]
    df['taskname'] = [op.basename(f).split('_task-')[-1].split('_')[0] if 'task' in op.basename(f)
                      else np.nan for f in files]
    df['space'] = [op.basename(f).split('_space-')[-1].split('_')[0] if 'space' in op.basename(f)
                   else np.nan for f in files]
    df = pd.DataFrame(df)
    df = df.sort_values(by=['data_type', 'file_type', 'taskname', 'space', 'participant_label']).set_index('files')
    
    df.to_csv(op.join(out_dir, 'scans.tsv'), sep='\t', index=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Summarize data specs')
    parser.add_argument('dir', type=str, help='Input')
    args = parser.parse_args()
    summarize_data_specs(args.dir)
