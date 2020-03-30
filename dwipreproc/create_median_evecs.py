import sys
import os.path as op
import numpy as np
import nibabel as nib
from glob import glob
from tqdm import tqdm

dwipreproc_dir = sys.argv[1]

files = sorted(glob(f'{dwipreproc_dir}/FA_template/EVECS/sub*template.nii.gz'))
for i, f in tqdm(enumerate(files)):
    if i == 0:
        img = nib.load(f)
        data = np.zeros(img.shape + (len(files),))
        data[:, :, :, :, i] = img.get_fdata()
    else:
        data[:, :, :, :, i] = nib.load(f).get_fdata()

nib.Nifti1Image(np.median(np.abs(data), axis=-1), affine=img.affine).to_filename(
    op.join(dwipreproc_dir, 'FA_template', 'EVECS_median.nii.gz')
)
