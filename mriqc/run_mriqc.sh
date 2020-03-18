bids_dir=$1
if [ ! -d ${bids_dir} ]; then
    echo "${bids_dir} does not exist!"
    exit 1
fi

bids_dir=$(realpath ${bids_dir})
out_dir=$bids_dir/derivatives/mriqc

subs=$(ls -d1 $bids_dir/sub-0*)
# Run subjects one at the time as to avoid memory issues
for sub in $subs; do
    # NOT PARALLELIZED!
    base_sub=`basename $sub`
    label=${base_sub//sub-/}
    if [ -d ../derivatives/mriqc/${base_sub} ]; then
        echo "${base_sub} already done!"
        continue
    fi
    echo "Processing ${base_sub}!"
    docker run -it --rm -v $bids_dir:/data:ro -v $out_dir:/out poldracklab/mriqc:0.15.0 /data /out participant \
        --participant_label $label \
        --nprocs 5 \
        --float32 \
        --fft-spikes-detector \
        --ants-nthreads 2 \
        --deoblique \
    	--no-sub \
        --despike
done
