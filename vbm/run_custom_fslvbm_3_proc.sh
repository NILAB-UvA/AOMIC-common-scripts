#!/bin/sh

#   fslvbm_3_proc - FSLVBM - the rest of it!!
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

echo [`date`] [`hostname`] [`uname -a`] [`pwd`] [$0 $@] >> .fslvbmlog

if [ -z "$1" ] ; then
    N_CORES=1
else
    N_CORES=$1
fi

if [ -z "$2" ]; then
    vbm_dir=$PWD
else
    vbm_dir=$2
fi

echo "VBM dir: ${vbm_dir}"

if [ ! -d ${vmb_dir} ]; then 
    echo "ERROR : Dir ${vmb_dir} doesn't exist!"
    exit 1
fi
mkdir -p ${vbm_dir}/stats

cd ${vbm_dir}/struc

echo "Now running the preprocessing steps and the pre-analyses"

/bin/rm -f fslvbm3a*
idx=1
for g in `$FSLDIR/bin/imglob *_probseg.*` ; do
  echo "echo \"Processing ${g}\"" >> fslvbm3a1
  echo "echo \"Processing ${g}\"" >> fslvbm3a2
  echo "${FSLDIR}/bin/fsl_reg ${g} template_GM ${g}_to_template_GM -fnirt \"--config=GM_2_MNI152GM_2mm.cnf --jout=${g}_JAC_nl\" &" >> fslvbm3a1
  echo "$FSLDIR/bin/fslmaths ${g}_to_template_GM -mul ${g}_JAC_nl ${g}_to_template_GM_mod -odt float &" >> fslvbm3a2
  if [ $(($idx % $N_CORES)) = 0 ] ; then
    echo "wait" >> fslvbm3a1
    echo "wait" >> fslvbm3a2
  fi
  idx=$(($idx+1))
done

echo "wait" >> fslvbm3a1
echo "wait" >> fslvbm3a2
chmod a+x fslvbm3a1
chmod a+x fslvbm3a2
#fslvbm3a_id=`${FSLDIR}/bin/fsl_sub -T 40 -N fslvbm3a -t ./fslvbm3a`
echo "Doing registrations"
./fslvbm3a1
wait $!

./fslvbm3a2
wait $!
#echo Doing registrations: ID=$fslvbm3a_id

cd ../stats

#cat <<stage_preproc2 > fslvbm3b
##!/bin/sh
$FSLDIR/bin/imcp ../struc/template_GM template_GM
#\$FSLDIR/bin/imcp ../struc/template_GM template_GM

#\$FSLDIR/bin/fslmerge -t GM_merg     \`\${FSLDIR}/bin/imglob ../struc/*_GM_to_template_GM.*\`
$FSLDIR/bin/fslmerge -t GM_merg `${FSLDIR}/bin/imglob ../struc/*_to_template_GM.*`
#\$FSLDIR/bin/fslmerge -t GM_mod_merg \`\${FSLDIR}/bin/imglob ../struc/*_GM_to_template_GM_mod.*\`
$FSLDIR/bin/fslmerge -t GM_mod_merg `${FSLDIR}/bin/imglob ../struc/*_to_template_GM_mod.*`
#\$FSLDIR/bin/fslmaths GM_merg -Tmean -thr 0.01 -bin GM_mask -odt char
$FSLDIR/bin/fslmaths GM_merg -Tmean -thr 0.01 -bin GM_mask -odt char
/bin/cp ../design.* .

for i in GM_mod_merg ; do
  for j in 2 3 4 ; do
    $FSLDIR/bin/fslmaths $i -s $j ${i}_s${j} 
    #$FSLDIR/bin/randomise -i ${i}_s${j} -o \${i}_s${j} -m GM_mask -d design.mat -t design.con -V
  done
done

#stage_preproc2

#chmod a+x fslvbm3b

#fslvbm3b_id=`${FSLDIR}/bin/fsl_sub -T 15 -N fslvbm3b -j $fslvbm3a_id ./fslvbm3b`

#echo Doing subject concatenation and initial randomise: ID=$fslvbm3b_id

echo "Once this has finished, run randomise with 5000 permutations on the 'best' smoothed 4D GM_mod_merg. We recommend using the -T (TFCE) option. For example:"
echo "randomise -i GM_mod_merg_s3 -o GM_mod_merg_s3 -m GM_mask -d design.mat -t design.con -n 5000 -T -V"
