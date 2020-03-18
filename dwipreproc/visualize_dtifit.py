import os
import os.path as op
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
plt.style.use('dark_background')

def plot(f, coords=(32, 45, 24), f_out=None):
    dat = nib.load(f).get_fdata()
    # trim off zero slices
    dat = dat[dat.sum(axis=(1, 2, 3)) != 0, :, :, :]
    dat = dat[:, dat.sum(axis=(0, 2, 3)) != 0, :, :]
    dat = dat[:, :, dat.sum(axis=(0, 1, 3)) != 0, :]
    
    dat = np.abs(dat)
    dat = (dat - dat.min()) / (dat.max() - dat.min()) * 255
    dat = dat.astype(int)
    
    fig, axes = plt.subplots(ncols=3, figsize=(12, 5))
    for i, ax in enumerate(axes):
        slc = np.take(dat, coords[i], axis=i)
        slc = slc.transpose(1, 0, 2)
        ax.imshow(slc, origin='lower')
        ax.axis('off')
        ax.set_title(['X', 'Y', 'Z'][i] + ' = ' + str(coords[i]))
    
    axes[0].text(s=op.basename(f), x=0, y=80, fontsize=15)
    
    if f_out is None:
        f_out = f.replace('.nii.gz', '.png')
    
    print(f"Saving to {f_out}")
    fig.savefig(f_out, dpi=100)
    plt.close()


if __name__ == '__main__':
    from glob import glob
    coords = [(78, 122, 77), (32, 45, 24)]
    for i, space in enumerate(['FSLHCP1065', 'native']):
        files = sorted(glob(f'../../derivatives/dti_fa/sub*/*{space}_V1.nii.gz'))    
        out_dir = f'../../derivatives/dti_fa/visual_qc/{space}'
        
        if not op.isdir(out_dir):
            os.makedirs(out_dir)
        
        for f in files:
            f_out = op.join(out_dir, op.basename(f).replace('.nii.gz', '.png'))
            plot(f, coords=coords[i], f_out=f_out)