import os
import shutil
import pandas as pd
import os.path as op
from nilearn import image
from glob import glob
from nipype.interfaces.fsl import MultipleRegressDesign

demogr = pd.read_csv('../participants.tsv', sep='\t')
demogr = demogr.dropna(how='any', axis=0, subset=['sex'])
dm = pd.get_dummies(demogr, columns=['sex'])
dm = dm.loc[:, ['participant_id', 'sex_M', 'sex_F']].set_index('participant_id')

vbm_files = sorted(glob('../derivatives/vbm/sub*/*.nii.gz'))
vbm_subs = [op.basename(f).split('_')[0] for f in vbm_files]
vbm = pd.DataFrame(vbm_files, columns=['file'], index=vbm_subs)

complete_subs = dm.index.intersection(vbm.index)
print(f"Found {len(complete_subs)} complete subjects for VBM!")

dm_vbm = dm.loc[complete_subs, :]
vbm = vbm.loc[complete_subs, :]

model = MultipleRegressDesign()
model.inputs.regressors = dm_vbm.to_dict(orient='list')
m_gt_f = ('male > female', 'T', ['sex_M', 'sex_F'], [1., -1.])
f_gt_m = ('female > male', 'T', ['sex_M', 'sex_F'], [-.1, 1.])
model.inputs.contrasts = [
    m_gt_f,
    f_gt_m,
    ('f_sex', 'F', [m_gt_f])
]
out = model.run()
for attr in ['design_con', 'design_mat', 'design_fts', 'design_grp']:
    f = getattr(out.outputs, attr)
    shutil.move(f, f'../derivatives/vbm/randomise/{attr}')

if not op.isdir('../derivatives/vbm/randomise'):
    os.makedirs('../derivatives/vbm/randomise')

dm_vbm.to_csv('../derivatives/vbm/randomise/design.tsv', sep='\t', index=False)
#vbm_4d = image.concat_imgs(vbm.file)
#vbm_4d.to_filename('../derivatives/vbm/randomise/vbm_4d.nii.gz')

fa_files = sorted(glob('../derivatives/dti_fa/sub*/*space-FSL*_FA.nii.gz'))
fa_subs = [op.basename(f).split('_')[0] for f in fa_files]
fa = pd.DataFrame(fa_files, columns=['file'], index=fa_subs)

complete_subs = dm.index.intersection(fa.index)
print(f"Found {len(complete_subs)} complete subjects for FA!")

dm_fa = dm.loc[complete_subs, :]
fa = fa.loc[complete_subs, :]

if not op.isdir('../derivatives/dti_fa/randomise'):
    os.makedirs('../derivatives/dti_fa/randomise')

dm_fa.to_csv('../derivatives/dti_fa/randomise/design.tsv', sep='\t', index=False)
#fa_4d = image.concat_imgs(fa.file)
#fa_4d.to_filename('../derivatives/dti_fa/randomise/fa_4d.nii.gz')