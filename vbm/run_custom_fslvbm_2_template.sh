#!/bin/sh

#   fslvbm_2_template - FSLVBM template creation
#
#   Gwenaelle Douaud & Stephen Smith, FMRIB Image Analysis Group
#
#   Copyright (C) 2007-2008 University of Oxford
#
#   Part of FSL - FMRIB's Software Library
#   http://www.fmrib.ox.ac.uk/fsl
#   fsl@fmrib.ox.ac.uk
#   
#   Developed at FMRIB (Oxford Centre for Functional Magnetic Resonance
#   Imaging of the Brain), Department of Clinical Neurology, Oxford
#   University, Oxford, UK
#   
#   
#   LICENCE
#   
#   FMRIB Software Library, Release 5.0 (c) 2012, The University of
#   Oxford (the "Software")
#   
#   The Software remains the property of the University of Oxford ("the
#   University").
#   
#   The Software is distributed "AS IS" under this Licence solely for
#   non-commercial use in the hope that it will be useful, but in order
#   that the University as a charitable foundation protects its assets for
#   the benefit of its educational and research purposes, the University
#   makes clear that no condition is made or to be implied, nor is any
#   warranty given or to be implied, as to the accuracy of the Software,
#   or that it will be suitable for any particular purpose or for use
#   under any specific conditions. Furthermore, the University disclaims
#   all responsibility for the use which is made of the Software. It
#   further disclaims any liability for the outcomes arising from using
#   the Software.
#   
#   The Licensee agrees to indemnify the University and hold the
#   University harmless from and against any and all claims, damages and
#   liabilities asserted by third parties (including claims for
#   negligence) which arise directly or indirectly from the use of the
#   Software or the sale of any products based on the Software.
#   
#   No part of the Software may be reproduced, modified, transmitted or
#   transferred in any form or by any means, electronic or mechanical,
#   without the express permission of the University. The permission of
#   the University is not required if the said reproduction, modification,
#   transmission or transference is done without financial return, the
#   conditions of this Licence are imposed upon the receiver of the
#   product, and all original and amended source code is included in any
#   transmitted product. You may be held legally responsible for any
#   copyright infringement that is caused or encouraged by your failure to
#   abide by these terms and conditions.
#   
#   You are not permitted under this Licence to use this Software
#   commercially. Use for which any financial return is received shall be
#   defined as commercial use, and includes (1) integration of all or part
#   of the source code or the Software into a product for sale or license
#   by or on behalf of Licensee to third parties or (2) use of the
#   Software or any derivative of it for research with the final aim of
#   developing software products for sale or license to a third party or
#   (3) use of the Software or any derivative of it for research with the
#   final aim of developing non-software products for sale or license to a
#   third party, or (4) use of the Software to provide any service to an
#   external organisation for which payment is received. If you are
#   interested in using the Software commercially, please contact Isis
#   Innovation Limited ("Isis"), the technology transfer company of the
#   University, to negotiate a licence. Contact details are:
#   innovation@isis.ox.ac.uk quoting reference DE/9564.

export LC_ALL=C

Usage() {
    echo ""
    echo "Usage: fslvbm_2_template [options]"
    echo ""
    echo "-n  : nonlinear registration (recommended)"
    echo "-a  : affine registration (discouraged)"
    echo ""
    exit 1
}

[ "$1" = "" ] && Usage

echo [`date`] [`hostname`] [`uname -a`] [`pwd`] [$0 $@] >> .fslvbmlog

HOWLONG=30
if [ $1 = -a ] ; then
    REG="-a"
    HOWLONG=5
fi

if [ -z "$2" ] ; then
    N_CORES=1
else
    N_CORES=$2
fi

echo "Running with ${N_CORES} cores"

if [ -z "$3" ]; then
    fmriprep_dir=../derivatives/fmriprep
else
    fmriprep_dir=$3
fi

echo "FMRIPREP dir = ${fmriprep_dir}"

if [ -z "$4" ]; then
    out_dir=$(dirname ${fmriprep_dir})/vbm
else
    out_dir=$4
fi

echo "Output dir = ${out_dir}"
struc_dir=${out_dir}/struc
if [ ! -d ${struc_dir} ]; then
    echo "Creating dir ${struc_dir} ... "
    mkdir -p ${struc_dir}
fi

gms=$(ls ${fmriprep_dir}/sub*/anat/sub-????_label-GM_probseg.nii.gz)
for gm in ${gms}; do
    if [ ! -f ${struc_dir}/$(basename ${gm}) ]; then
      cp ${gm} ${struc_dir}/
    fi
done

cd ${struc_dir}
T=${FSLDIR}/data/standard/tissuepriors/avg152T1_gray

### segmentation
#/bin/rm -f fslvbm2a
#for g in `$FSLDIR/bin/imglob *_struc.*` ; do
#    echo $g
#    echo "$FSLDIR/bin/fast -R 0.3 -H 0.1 ${g}_brain ; \
#          $FSLDIR/bin/immv ${g}_brain_pve_1 ${g}_GM" >> fslvbm2a
#done
#chmod a+x fslvbm2a
#fslvbm2a_id=`$FSLDIR/bin/fsl_sub -T 30 -N fslvbm2a -t ./fslvbm2a`
#echo Running segmentation: ID=$fslvbm2a_id

### Estimation of the registration parameters of GM to grey matter standard template
/bin/rm -f fslvbm2b
idx=1
for g in `$FSLDIR/bin/imglob *_probseg.*` ; do
  echo "echo \"Processing ${g}\"" >> fslvbm2b
  echo "${FSLDIR}/bin/fsl_reg ${g} $T ${g}_to_T -a &" >> fslvbm2b
  if [ $(($idx % $N_CORES)) = 0 ] ; then
    echo "wait" >> fslvbm2b
  fi
  idx=$(($idx + 1))
done

echo "wait" >> fslvbm2b
chmod a+x fslvbm2b
#fslvbm2b_id=`$FSLDIR/bin/fsl_sub -T $HOWLONG -N fslvbm2b -t ./fslvbm2b`
echo Running initial registration #: ID=$fslvbm2b_id
./fslvbm2b
wait $!

echo "Done initial reg"

### Creation of the GM template by averaging all (or following the template_list for) the GM_nl_0 and GM_xflipped_nl_0 images
#cat <<stage_tpl3 > fslvbm2c
##!/bin/sh
#if [ -f ../template_list ] ; then
#    template_list=\`cat ../template_list\`
#    template_list=\`\$FSLDIR/bin/remove_ext \$template_list\`
#else
#    template_list=\`echo *_struc.* | sed 's/_struc\./\./g'\`
#    template_list=\`\$FSLDIR/bin/remove_ext \$template_list | sort -u\`
#    echo "WARNING - study-specific template will be created from ALL input data - may not be group-size matched!!!"
#fi
#for g in \$template_list ; do
#    mergelist="\$mergelist \${g}_struc_GM_to_T"
#done
#\$FSLDIR/bin/fslmerge -t template_4D_GM \$mergelist
#\$FSLDIR/bin/fslmaths template_4D_GM -Tmean template_GM
#\$FSLDIR/bin/fslswapdim template_GM -x y z template_GM_flipped
#\$FSLDIR/bin/fslmaths template_GM -add template_GM_flipped -div 2 template_GM_init

#stage_tpl3
#chmod +x fslvbm2c
#fslvbm2c_id=`fsl_sub -j $fslvbm2b_id -T 15 -N fslvbm2c ./fslvbm2c`
#echo Creating first-pass template: ID=$fslvbm2c_id

$FSLDIR/bin/fslmerge -t template_4D_GM `ls -d1 *to_T.nii.gz`
$FSLDIR/bin/fslmaths template_4D_GM -Tmean template_GM
$FSLDIR/bin/fslswapdim template_GM -x y z template_GM_flipped
$FSLDIR/bin/fslmaths template_GM -add template_GM_flipped -div 2 template_GM_init

### Estimation of the registration parameters of GM to grey matter standard template
/bin/rm -f fslvbm2d
T=template_GM_init
idx=1
for g in `$FSLDIR/bin/imglob *_probseg.*` ; do
  echo "echo \"Processing ${g}\"" >> fslvbm2d
  echo "${FSLDIR}/bin/fsl_reg ${g} $T ${g}_to_T_init $REG -fnirt \"--config=GM_2_MNI152GM_2mm.cnf\" &" >> fslvbm2d
  if [ $(($idx % $N_CORES)) = 0 ] ; then
    echo "wait" >> fslvbm2d
  fi
  idx=$(($idx+1))
done
echo "wait" >> fslvbm2d
chmod a+x fslvbm2d
#fslvbm2d_id=`$FSLDIR/bin/fsl_sub -j $fslvbm2b_id -T $HOWLONG -N fslvbm2d -t ./fslvbm2d`
echo "Running registration to first-pass template #: ID=$fslvbm2d_id"
./fslvbm2d
wait $!

### Creation of the GM template by averaging all (or following the template_list for) the GM_nl_0 and GM_xflipped_nl_0 images
#cat <<stage_tpl4 > fslvbm2e
##!/bin/sh
#if [ -f ../template_list ] ; then
#    template_list=\`cat ../template_list\`
#    template_list=\`\$FSLDIR/bin/remove_ext \$template_list\`
#else
#    template_list=\`echo *_struc.* | sed 's/_struc\./\./g'\`
#    template_list=\`\$FSLDIR/bin/remove_ext \$template_list | sort -u\`
#    echo "WARNING - study-specific template will be created from ALL input data - may not be group-size matched!!!"
#fi
#for g in \$template_list ; do
#    mergelist="\$mergelist \${g}_struc_GM_to_T_init"
#done
#\$FSLDIR/bin/fslmerge -t template_4D_GM \$mergelist
#\$FSLDIR/bin/fslmaths template_4D_GM -Tmean template_GM
#\$FSLDIR/bin/fslswapdim template_GM -x y z template_GM_flipped
#\$FSLDIR/bin/fslmaths template_GM -add template_GM_flipped -div 2 template_GM
#stage_tpl4
#chmod +x fslvbm2e
#fslvbm2e_id=`fsl_sub -j $fslvbm2d_id -T 15 -N fslvbm2e ./fslvbm2e`
#echo Creating second-pass template: ID=$fslvbm2e_id

$FSLDIR/bin/fslmerge -t template_4D_GM `ls -d1 *_to_T_init.nii.gz`
$FSLDIR/bin/fslmaths template_4D_GM -Tmean template_GM
$FSLDIR/bin/fslswapdim template_GM -x y z template_GM_flipped
$FSLDIR/bin/fslmaths template_GM -add template_GM_flipped -div 2 template_GM

echo "Study-specific template will be created, when complete, check results with:"
echo "fslview struc/template_4D_GM"
echo "and turn on the movie loop to check all subjects, then run:"
echo "fslview " ${FSLDIR}/data/standard/tissuepriors/avg152T1_gray " struc/template_GM"
echo "to check general alignment of mean GM template vs. original standard space template."
