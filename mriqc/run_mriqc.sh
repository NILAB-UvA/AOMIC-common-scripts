bids_dir=$1
if [ ! -d ${bids_dir} ]; then
    echo "ERROR: ${bids_dir} does not exist."
    exit 1
fi

bids_dir=$(realpath ${bids_dir})
out_dir=$bids_dir/derivatives/mriqc
work_dir=$(realpath ../../mriqc_work)
n_jobs=10

subs=`ls -d1 $bids_dir/sub-????`
# Run subjects one at the time as to avoid memory issues
i=0
for sub in $subs; do
    base_sub=`basename $sub`
    if [ -d ../derivatives/mriqc/${base_sub} ]; then
        echo "${base_sub} already done!"
        continue
    else
	echo "Running ${base_sub}"
    fi

    label=${base_sub//sub-/}
    docker run --rm -v $bids_dir:/data:ro -v $out_dir:/out poldracklab/mriqc:0.15.0 /data /out participant \
        --participant_label $label \
        --nprocs 1 \
        --float32 \
        -w $work_dir \
        --fft-spikes-detector \
        --ants-nthreads 1 \
        --deoblique \
	--no-sub \
        --despike &

    i=$(($i + 1))
    if [ $(($i % $n_jobs)) = 0 ]; then
        wait
    fi 
done
wait
