""" Disclaimer: this is possibly the ugliest code I've ever written.
It works, that's it. Please don't use it for your own analyses. 
"""
import os
import json
import os.path as op
import pandas as pd
from glob import glob
from tqdm import tqdm

pd.set_option('display.float_format', lambda x: '%.3f' % x)

fsname2atlas = {
    'cortical': {
        'aparc.a2009s': 'Destrieux2009',
        'aparc': 'DesikanKilliany'
    },
    'subcortical': {
        'aseg': 'FreesurferSubcortSeg',
        'wmparc': 'FreesurferWmParc'
    }
}

hemi2word = {
    'rh': 'Right',
    'lh': 'Left'
}


subs = [op.basename(d) for d in sorted(glob('../derivatives/freesurfer/sub-*'))]

json_file = {
    "cortical": {
        "name": {
            "Description": "Name of brain region (when appropraite, prepended by 'Left' or 'Right', indicating hemisphere)"
        },
        "volume": {
            "Description": "Volume of a given brain area",
            "Units": "mm^3"
        },
        "area": {
            "Description": "Surface area of a given brain area",
            "Units": "mm^2"
        },
        "meancurv": {
            "Description": "Integrated rectified mean curvature of a given brain area",
            "Units": "mm^-1"
        },
        "thickness": {
            "Description": "Thickness of a given brain area",
            "Units": "mm"
        }
    },
    "subcortical": {
        "name": {
            "Description": "Name of brain region (prepended by 'left' or 'right', indicating hemisphere)"
        },
        "volume": {
            "Description": "Volume of a given brain area",
            "Units": "mm^3"
        },
        "intensity-avg": {
            "Description": "Average signal intensity of a given brain area",
            "Units": "A.U."
        }
    }
}

for atlas in fsname2atlas['cortical'].keys():

    for sub in tqdm(subs, desc=atlas):
        dfs = []
        for hemi in ('lh', 'rh'):
            i = 0
            for measure in ['volume', 'thickness', 'area', 'meancurv']:
                f = f'../derivatives/fs_stats/data-cortical_type-{atlas}_measure-{measure}_hemi-{hemi}.tsv'
                df = pd.read_csv(f, sep='\t', index_col=0)
                df.index = df.index.rename('participant_id')
                df = df.reset_index()
                df = df.loc[:, [col for col in df.columns if 'Mean' not in col]]
                df = pd.melt(df, id_vars=['participant_id'], value_name=measure, var_name='name')
                df['name'] = [n.replace(f'_{measure}', '') for n in df['name']]
                df['name'] = [hemi2word[n.split('_')[0]] + '-' + '_'.join(n.split('_')[1:]) if 'rh' in n or 'lh' in n else n
                            for n in df['name']]
                df = df.query("participant_id == @sub")
                dfs.append(df)
                
        df = pd.concat(dfs, axis=1)
        df = df.loc[:, ~df.columns.duplicated()].dropna()        
        d_out = f'../derivatives/fs_stats/{sub}'
        if not op.isdir(d_out):
            os.makedirs(d_out)

        f_out = op.join(d_out, f"{sub}_desc-{fsname2atlas['cortical'][atlas]}_stats.tsv")
        df.drop('participant_id', axis=1).to_csv(f_out, sep='\t', index=False)
        f_out = f_out.replace('tsv', 'json')
        with open(f_out, 'w') as json_out:
            json.dump(json_file['cortical'], json_out, indent=4)


for atlas in fsname2atlas['subcortical'].keys():

    for sub in tqdm(subs, desc=atlas):
        dfs = []
        for hemi in ('lh', 'rh'):
            i = 0
            for measure in ['mean', 'volume']:
                f = f'../derivatives/fs_stats/data-subcortical_type-{atlas}_measure-{measure}_hemi-both.tsv'
                df = pd.read_csv(f, sep='\t', index_col=0)
                df.index = df.index.rename('participant_id')
                df = df.reset_index()
                df = df.loc[:, [col for col in df.columns if 'Mean' not in col]]
                df = pd.melt(df, id_vars=['participant_id'], value_name=measure, var_name='name')
                new_names = []
                for n in df['name']:
                    if '-lh-' in n:
                        new_names.append('Left-' + n.replace('lh-', ''))
                    elif '-rh-' in n:
                        new_names.append('Right-' + n.replace('rh-', ''))
                    else:
                        new_names.append(n)
                df['name'] = new_names
                if measure == 'mean':
                    df = df.rename({measure: 'intensity-avg'}, axis=1)

                df = df.query("participant_id == @sub")
                dfs.append(df)
                
        df = pd.concat(dfs, axis=1)
        df = df.loc[:, ~df.columns.duplicated()].dropna()        
        d_out = f'../derivatives/fs_stats/{sub}'
        if not op.isdir(d_out):
            os.makedirs(d_out)

        f_out = op.join(d_out, f"{sub}_desc-{fsname2atlas['subcortical'][atlas]}_stats.tsv")
        df.drop('participant_id', axis=1).to_csv(f_out, sep='\t', index=False)
        f_out = f_out.replace('tsv', 'json')
        with open(f_out, 'w') as json_out:
            json.dump(json_file['subcortical'], json_out, indent=4)
