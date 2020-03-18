# source activate python2
set -e
export SUBJECTS_DIR=../derivatives/freesurfer

subs=()
for sub in $(ls -d ../sub-????); do
    subs+=($(basename ${sub}))
done

for measure in volume mean; do

    for statsfile in aseg.stats wmparc.stats; do
        echo -e "\nRUNNING asegstats2table WITH MEASURE ${measure} AND STATSFILE ${statsfile}!\n"
        asegstats2table --subjects ${subs[@]} \
            --tablefile ../derivatives/fs_stats/data-subcortical_type-${statsfile/.stats/}_measure-${measure}_hemi-both.tsv \
            --meas ${measure} \
            --statsfile ${statsfile} \
            --delimiter 'tab'
    done
done

for measure in volume thickness area meancurv; do

    for parc in aparc aparc.a2009s; do
        for hemi in lh rh; do
            echo -e "\nRUNNING aparcstats2table WITH MEASURE ${measure} AND PARC ${parc} FOR HEMI ${hemi}!\n"
            aparcstats2table --subjects ${subs[@]} \
                --hemi ${hemi} \
                --parc ${parc} \
                --measure ${measure} \
                --tablefile ../derivatives/fs_stats/data-cortical_type-${parc}_measure-${measure}_hemi-${hemi}.tsv \
                --delimiter 'tab'           
        done
    done
done