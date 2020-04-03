set -e
bids_dir=$1
if [ ! -d ${bids_dir} ]; then
    echo "ERROR: ${bids_dir} is not a directory."
    exit 1
fi

out=$(dirname ${bids_dir})/bids_backup.tar.gz
echo "Creating ${out} ..."

tar --exclude='${bids_dir}/derivatives/dual_regression_rs' \
    --exclude='${bids_dir}/derivatives/tsnr' \
    --exclude='${bids_dir}/derivatives/task_fmri' \
    --exclude='${bids_dir}/derivatives/physio_fmri' \
    --use-compress-program=pigz \
    -cvf ${out} ${bids_dir}
