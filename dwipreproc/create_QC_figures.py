import os
import os.path as op
import numpy as np
import pandas as pd
import nibabel as nib
import seaborn as sns
import matplotlib.pyplot as plt
from glob import glob
from tqdm import tqdm


plt.style.use("dark_background")


def plot_DEC(evecs, fa, f_out, coords=(35, 45, 24)):

    v1 = nib.load(evecs).get_fdata()
    fa_ = nib.load(fa).get_fdata()

    # trim off zero slices
    x_idx = v1.sum(axis=(1, 2, 3)) != 0
    y_idx = v1.sum(axis=(0, 2, 3)) != 0
    z_idx = v1.sum(axis=(0, 1, 3)) != 0

    v1 = v1[x_idx, :, :, :]
    v1 = v1[:, y_idx, :, :]
    v1 = v1[:, :, z_idx, :]

    fa_ = fa_[x_idx, :, :]
    fa_ = fa_[:, y_idx, :]
    fa_ = fa_[:, :, z_idx]

    # Take absolute and rescale (0-255)    
    v1 = np.abs(v1)
    v1 = (v1 - v1.min()) / (v1.max() - v1.min()) * 255
    v1 = v1.astype(int)
    
    fig, axes = plt.subplots(nrows=3, ncols=3, figsize=(15, 12))
    for i in range(3):
        fa_slc = np.take(fa_, coords[i], axis=i)
        fa_slc = fa_slc.T
         
        v1_slc = np.take(v1, coords[i], axis=i)
        v1_slc = v1_slc.transpose(1, 0, 2)

        axes[0, i].imshow(fa_slc, origin='lower', cmap='Greys_r', vmin=0, vmax=0.9)
        axes[0, i].axis('off')
        axes[0, i].set_title(['X', 'Y', 'Z'][i] + ' = ' + str(coords[i]), fontsize=20)

        axes[1, i].imshow(v1_slc, origin='lower', vmin=0, vmax=255)
        axes[1, i].axis('off')
        
        v1_mod = (v1_slc * fa_slc[:, :, np.newaxis]).astype(int)
        v1_mod[v1_mod > 255] = 255
        axes[2, i].imshow(v1_mod, origin='lower', vmin=0, vmax=255)
        axes[2, i].axis('off')
        
        if i == 0:
            for ii, mod in enumerate(['FA', 'EVECS', 'Mod. FA']):
                axes[ii, 0].text(-15, fa_slc.shape[0] // 2, mod, fontsize=25, rotation=90, verticalalignment='center')

    axes[0, 0].text(s=op.basename(fa).split('_FA')[0], x=-15, y=80, fontsize=25)
    fig.savefig(f_out)
    plt.close()


def plot_eddy_qc(eddy_qc, f_out):

    fig = plt.figure(constrained_layout=False, figsize=(15, 10))
    gs = fig.add_gridspec(nrows=4, ncols=3, left=0.1, right=0.9, wspace=0.05, hspace=1)
    
    ts_params = [
        ('eddy_movement_rms', (0, 1)),
        ('eddy_restricted_movement_rms', (0, 1)),
        ('eddy_parameters', (-.5, .5))
    ]

    for i, (name, ylim) in enumerate(ts_params):
        dat = np.loadtxt(op.join(eddy_qc, name))
        ax = fig.add_subplot(gs[i, :])
        ax.plot(dat)
        ax.set_xlim(0, dat.shape[0])
        ax.set_ylim(ylim)
        ax.set_title(name, fontsize=20)

        if i != len(ts_params) - 1:
            ax.set_xticks([])
        else:
            ax.set_xlabel("Directions", fontsize=15)
        
        if i == 0:
            sub_base = op.basename(op.dirname(eddy_qc))
            ax.text(0, ylim[1] + 0.3 * ylim[1], sub_base, fontsize=20)

    names = ['eddy_outlier_map', 'eddy_outlier_n_sqr_stdev_map', 'eddy_outlier_n_stdev_map']
    for i, name in enumerate(names):
        dat = np.loadtxt(op.join(eddy_qc, name), skiprows=1)
        ax = fig.add_subplot(gs[len(ts_params), i])
        ax.imshow(dat, aspect='auto')
        ax.set_title(name, fontsize=13)
        if i != 0:
            ax.set_yticks([])
        else:
            ax.set_ylabel('Directions', fontsize=12)

        ax.set_xlabel("Slice nr.", fontsize=12)
        
    sns.despine()
    fig.savefig(f_out)
    plt.close()


if __name__ == '__main__':

    dwi_dir = '../derivatives/dwipreproc'
    sub_dirs = sorted(glob(op.join(dwi_dir, 'sub-*')))

    for sub_dir in tqdm(sub_dirs):
        sub_base = op.basename(sub_dir)
        d_out = op.join(sub_dir, 'figures')
        if not op.isdir(d_out):
            os.makedirs(d_out)

        fa = op.join(sub_dir, 'dwi', f'{sub_base}_model-DTI_desc-WLS_FA.nii.gz')
        evecs = op.join(sub_dir, 'dwi', f'{sub_base}_model-DTI_desc-WLS_EVECS.nii.gz')

        f_out = op.join(d_out, f'{sub_base}_desc-FA+EVECS_DTI.png')    
        plot_DEC(evecs, fa, f_out=f_out)

        eddy_qc = op.join(sub_dir, 'dwi', eddy_qc)
        f_out = op.join(d_out, f'{sub_base}_desc-eddy_qcparams.png')
        plot_eddy_qc(eddy_qc, f_out)
