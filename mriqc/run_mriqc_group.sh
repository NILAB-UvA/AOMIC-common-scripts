bids_dir=$1
if [ ! -d ${bids_dir} ]; then
    echo "${bids_dir} does not exist!"
    exit 1
fi

bids_dir=$(realpath ${bids_dir})
out_dir=$bids_dir/derivatives/mriqc
docker run -it --rm -v $bids_dir:/data:ro -v $out_dir:/out poldracklab/mriqc:0.15.0 /data /out group
