# source activate python2
set -e
fs_dir=$1
if [ ! -d $fs_dir ]; then
    echo "$fs_dir does not exist!"
    exit 1
fi
out_dir=$(dirname $fs_dir)/fs_stats
echo $out_dir
if [ ! -d $out_dir ]; then
    echo "creating $out_dir"
    mkdir $out_dir
fi
export SUBJECTS_DIR=$fs_dir

subs=()
for sub in $(ls -d ${fs_dir}/sub-*); do
    subs+=($(basename ${sub}))
done

for measure in volume mean; do

    for statsfile in aseg.stats wmparc.stats; do
        echo -e "\nRUNNING asegstats2table WITH MEASURE ${measure} AND STATSFILE ${statsfile}!\n"
        asegstats2table --subjects ${subs[@]} \
            --tablefile $out_dir/data-subcortical_type-${statsfile/.stats/}_measure-${measure}_hemi-both.tsv \
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
                --tablefile $out_dir/data-cortical_type-${parc}_measure-${measure}_hemi-${hemi}.tsv \
                --delimiter 'tab'           
        done
    done
done
