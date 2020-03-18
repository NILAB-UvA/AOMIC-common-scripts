import os.path as op
import pandas as pd
from glob import glob

def main(bids_dir, spaces=None):

    if spaces is None:
        spaces = ('fsaverage5', 'MNI152NLin2009cAsym', 'T1w')

    for mod in ('bold', 'T1w'):
        for ext in ('html', 'tsv'):
            mriqc_f = op.join(bids_dir, 'derivatives', 'mriqc', f'group_{mod}.{ext}')
            if not op.isfile(mriqc_f):
                print(f"WARNING: {mriqc_f} does not exist.")

    sub_dirs_bids = [d for d in sorted(glob(op.join(bids_dir, 'sub-*'))) if op.isdir(d)]
    for sdir in sub_dirs_bids:
        sub_base = op.basename(sdir)

        ##### CHECK ANAT #####
        anat = op.join(sdir, 'anat')
        if not op.isdir(anat):
            print(f"WARNING: {sub_base} doesn't have a T1 file.")

        anat_contents = glob(op.join(anat, '*.nii.gz'))
        if not anat_contents:
            print(f"WARNING: {sub_base} anat directory is empty.")
        else:
            fprep_anat_dir = op.join(bids_dir, 'derivatives', 'fmriprep', sub_base, 'anat')
            if not op.isdir(fprep_anat_dir):
                print(f"WARNING: {sub_base} doesn't have an Fmriprep anat folder.")
            else:
                fs_exts = ('inflated', 'midthickness', 'pial', 'smoothwm')
                for ext in fs_exts:
                    for hemi in ('R', 'L'):
                        f = op.join(fprep_anat_dir, f'{sub_base}_hemi-{hemi}_{ext}.surf.gii')
                        if not op.isfile(f):
                            print(f"WARNING: {op.basename(f)} does not exist.")
                
                for ext in ('desc-aparcaseg_dseg', 'desc-aseg_dseg'):
                    f = op.join(fprep_anat_dir, f'{sub_base}_{ext}.nii.gz')
                    if not op.isfile(f):
                        print(f"WARNING: {op.basename(f)} seems to be missing.")

                for space in [''] + ['space-' + s + '_' for s in spaces]:
                    if 'fsaverage' in space or 'T1w' in space:
                        continue                      
                    
                    exts = [
                        'desc-brain_mask.json', 'desc-brain_mask.nii.gz',
                        'desc-preproc_T1w.json', 'desc-preproc_T1w.nii.gz',
                        'dseg.nii.gz', 'label-CSF_probseg.nii.gz', 'label-GM_probseg.nii.gz',
                        'label-WM_probseg.nii.gz'
                    ]
                    for ext in exts:
                        f = op.join(fprep_anat_dir, f'{sub_base}_{space}{ext}')
                        if not op.isfile(f):
                            print(f"WARNING: {op.basename(f)} does not exist.")

            recon_all_done = op.join(bids_dir, 'derivatives', 'freesurfer', sub_base, 'scripts', 'recon-all.done')
            if not op.isfile(recon_all_done):
                print(f"WARNING: recon-all did not finish for {sub_base}.")
            else:
                pass
                with open(recon_all_done.replace('done', 'log'), 'r') as f_in:
                    ra_log = f_in.read().splitlines()[-1]
                    if not 'without error' in ra_log:
                        print(f"WARNING: something went wrong with Freesurfer for {sub_base}.")

            vbm_dir = op.join(bids_dir, 'derivatives', 'vbm')
            if op.isdir(vbm_dir):
                vbm_dir_sub = op.join(vbm_dir, sub_base)
                if not op.isdir(vbm_dir_sub):
                    print(f"WARNING: {vbm_dir_sub} does not exist.")
                else:
                    f = op.join(vbm_dir_sub, f'{sub_base}_desc-VBM_GMvolume.nii.gz')
                    if not op.isfile(f):
                        print(f"WARNING: {op.basename(f)} does not exist.")

            mriqc_dir = op.join(bids_dir, 'derivatives', 'mriqc')
            if op.isdir(mriqc_dir):
                for t1 in anat_contents:
                    f = op.join(mriqc_dir, op.basename(t1).replace('nii.gz', 'html'))
                    if not op.isfile(f):
                        print(f"WARNING: missing MRIQC file {op.basename(f)}.")

                    f = op.join(mriqc_dir, sub_base, 'anat', op.basename(t1).replace('nii.gz', 'json'))
                    if not op.isfile(f):
                        print(f"WARNING: missing MRIQC file {op.basename(f)}.")

        ##### CHECK DWI #####
        if op.isdir(op.join(sdir, 'dwi')):
            dwi_contents = glob(op.join(sdir, 'dwi'))
            if not dwi_contents:
                print(f"WARNING: {op.join(sdir, 'dwi')} exists, but is empty.")
            else:
                dwis = glob(op.join(sdir, 'dwi', '*.nii.gz'))
                for dwi in dwis:
                    bval = dwi.replace('nii.gz', 'bval')
                    bvec = dwi.replace('nii.gz', 'bvec')
                    for f in (bval, bvec):
                        if not op.isfile(f):
                            print(f"WARNING: {op.basename(dwi)} exists, but {op.basename(f)} doesn't.")

                dti_fa = op.join(bids_dir, 'derivatives', 'dwipreproc', sub_base)    
                if op.isdir(dti_fa):
                    for mod in ('desc-brain_mask', 'model-DTI_desc-WLS_FA', 'model-DTI_desc-WLS_EVECS'):
                        f = op.join(dti_fa, 'dwi', f'{sub_base}_{mod}.nii.gz')
                        if not op.isfile(f):
                            print(f"WARNING: {f} seems to be missing.")

        error_dir = op.join(bids_dir, 'derivatives', 'fmriprep', sub_base, 'log')
        if op.isdir(error_dir):
            print(f"WARNING: {sub_base} has a Fmriprep 'log' dir; something went wrong.")

        ##### CHECK FUNC #####
        func_files = glob(op.join(sdir, 'func', '*.nii.gz'))
        for func in func_files:
            func_base = op.basename(func).split('.nii.gz')[0]
            events = func.replace('bold.nii.gz', 'events.tsv')
            if not op.isfile(events):
                if not 'resting' in func and 'movie' not in func:
                    print(f"WARNING: {op.basename(func)} exists, but {op.basename(events)} doesn't.")

            mriqc_dir = op.join(bids_dir, 'derivatives', 'mriqc')
            if op.isdir(mriqc_dir):
                f = op.join(mriqc_dir, func_base + '.html')
                if not op.isfile(f):
                    print(f"WARNING: missing MRIQC file {op.basename(f)}.")

                f = op.join(mriqc_dir, sub_base, 'func', func_base + '.json')
                if not op.isfile(f):
                    print(f"WARNING: missing MRIQC file {op.basename(f)}.")

            fprep_dir = op.join(bids_dir, 'derivatives', 'fmriprep')
            if op.isdir(fprep_dir):
                func_base = op.basename(func).split('_bold')[0]
                fprep_html = op.join(fprep_dir, sub_base + '.html')
                if not op.isfile(fprep_html):
                    print(f"WARNING: {sub_base} doesn't have a Fmriprep html file.")
        
                exts = ['desc-confounds_regressors.json', 'desc-confounds_regressors.tsv']
                for ext in exts:
                    f = op.join(fprep_dir, sub_base, 'func', f'{func_base}_{ext}')
                    if not op.isfile(f):
                        print(f"WARNING: {op.basename(f)} does not exist.")

                for space in [s for s in spaces if 'fsaverage' in s]:
                    for ext in ('hemi-L.func.gii', 'hemi-R.func.gii'):
                        f = op.join(fprep_dir, sub_base, 'func', f'{func_base}_space-{space}_{ext}')
                        if not op.isfile(f):
                            print(f"WARNING: {op.basename(f)} does not exist.")

                for space in [s for s in spaces if 'fsaverage' not in s]:
                    exts = (
                        'boldref.nii.gz',
                        'desc-aparcaseg_dseg.nii.gz',
                        'desc-aseg_dseg.nii.gz',
                        'desc-brain_mask.json',
                        'desc-brain_mask.nii.gz',
                        'desc-preproc_bold.json',
                        'desc-preproc_bold.nii.gz'
                    )
                    for ext in exts:
                        f = op.join(fprep_dir, sub_base, 'func', f'{func_base}_space-{space}_{ext}')
                        if not op.isfile(f):
                            print(f"WARNING: {op.basename(f)} does not exist.")

        ##### CHECK PHYSIO #####
        physio_files = glob(op.join(sdir, 'func', '*.tsv.gz'))
        for phys in physio_files:
            func = phys.replace('recording-respcardiac_physio.tsv.gz', 'bold.nii.gz')
            if not op.isfile(func):
                print(f"WARNING: {op.basename(phys)} exists, but {op.basename(func)} doesn't.")

            phys_json = phys.replace('tsv.gz', 'json')
            if not op.isfile(phys_json):
                print(f"WARNING: {op.basename(phys)} exists, but {op.basename(phys_json)} doesn't.")

            phys_deriv_dir = op.join(bids_dir, 'derivatives', 'physiology')
            if op.isdir(phys_deriv_dir):
                ricor = op.join(
                    phys_deriv_dir, sub_base, 'physio',
                    op.basename(phys).replace('physio.tsv.gz', 'desc-retroicor_regressors.tsv')
                )
                if not op.isfile(ricor):
                    pass
                    #print(f"WARNING: {op.basename(phys)} exists, but {op.basename(ricor)} doesn't.")
                else:
                    df = pd.read_csv(ricor, sep='\t')
                    if not (
                        'cardiac_cos_00' in df.columns and 
                        'resp_cos_00' in df.columns and 
                        'interaction_add_cos_00' in df.columns and
                        'hrv' in df.columns and 'rvt' in df.columns
                        ):
                        print(f"WARNING: somthing wrong with columns of {op.basename(ricor)}.")

    #### CHECK WHETHER DATA EXISTS IN DERIVATIVES THAT DOES NOT EXIST IN BIDS ####
    for deriv in ('freesurfer', 'fmriprep', 'physiology', 'vbm', 'dti_fa', 'mriqc', 'dwipreproc'):
        deriv_dirs = sorted(glob(op.join(bids_dir, 'derivatives', deriv, 'sub-*')))
        deriv_subs = [d for d in deriv_dirs if op.isdir(d)]
        for sub in deriv_subs:
            sub_base = op.basename(sub)
            if not op.isdir(op.join(bids_dir, op.basename(sub))):
                print(f"WARNING: {deriv} dir {sub_base} exists, but BIDS dir {sub_base} does not exist.")
            else:
                if deriv == 'fmriprep':
                    files = [op.basename(s).split('_desc')[0] for s in glob(op.join(sub, 'func', '*_desc-confounds_regressors.tsv'))]
                    for f in files:
                        bids_f = op.join(bids_dir, sub_base, 'func', f + '_bold.nii.gz')
                        if not op.isfile(bids_f):
                            print(f"WARNING: {f} exists in Fmriprep, but not in BIDS, {bids_f}.")
                elif deriv == 'physiology':
                    files = [op.basename(s).split('_desc')[0] for s in glob(op.join(sub, 'physio', '*_desc-retroicor_regressors.tsv'))]
                    for f in files:
                        bids_f = op.join(bids_dir, sub_base, 'func', f + '_physio.tsv.gz')
                        if not op.isfile(bids_f):
                            print(f"WARNING: {f} exists in Physio deriv, but not in BIDS, {bids_f}.")
                elif deriv == 'dwipreproc':
                    files = [op.basename(s).split('_')[0] for s in glob(op.join(sub, 'dwi', '*_FA.nii.gz'))]
                    for f in files:
                        bids_f = op.join(bids_dir, sub_base, 'dwi', f'{f}_dwi.nii.gz')
                        if not op.isfile(bids_f):
                            print(f"WARNING: {f} exists in dwipreproc, but not in BIDS, {bids_f}.")

                elif deriv == 'mriqc':
                    files = [op.basename(s).split('_bold.html')[0] for s in glob(sub + '*_bold.html')]
                    for f in files:
                        bids_f = op.join(bids_dir, sub_base, 'func', f + '_bold.nii.gz')
                        if not op.isfile(bids_f):
                            print(f"WARNING: {f} exists in MRIQC, but not in BIDS, {bids_f}.")
                
                                   

if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser(description='Check completeness')
    parser.add_argument('dir', type=str, help='Input')
    args = parser.parse_args()
    main(op.abspath(args.dir))
