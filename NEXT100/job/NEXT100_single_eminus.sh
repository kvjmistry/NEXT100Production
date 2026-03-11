#!/bin/bash

echo "Starting Job" 

JOBID=$1
# SHIFT=10001
# JOBID=$((JOBID + SHIFT))
echo "The JOBID number is: ${JOBID}" 

JOBNAME=$2
echo "The JOBNAME number is: ${JOBNAME}" 

PRESSURE=$3
echo "The pressure is: ${PRESSURE}" 


echo "JOBID ${JOBID} running on `whoami`@`hostname`"

start=`date +%s`

# Setup nexus
echo "Setting Up Software" 
source /software/nexus/setup_nexus.sh
source /software/IC/setup_IC.sh

echo "untaring files"
tar -xvf files_${PRESSURE}.tar
rm files_${PRESSURE}.tar

N_EVENTS=200

# Use same template for full energy range and DEP events
CONFIG=NEXT100_single_eminus.config.mac
INIT=NEXT100_single_eminus.init.mac

# Make sure output file name is consistent
sed -i "s#.*output_file.*#/nexus/persistency/output_file ${JOBNAME}#" ${CONFIG}

echo "N_EVENTS: ${N_EVENTS}"

EID=$((${N_EVENTS}*${JOBID} + ${N_EVENTS}))
SEED=$((${JOBID} + 1))
echo "The seed number is: ${SEED}" 
echo "The EID number is: ${EID}" 

# Change the config in the files
sed -i "s#.*random_seed.*#/nexus/random_seed ${SEED}#" ${CONFIG}
sed -i "s#.*start_id.*#/nexus/persistency/start_id ${EID}#" ${CONFIG}

# Print out the config and init files
cat ${INIT}
cat ${CONFIG}

# Generation + Reco
echo "Running NEXUS and IC" 
nexus -n $N_EVENTS ${INIT}
python compress_nexus.py ${JOBNAME}.h5 ${JOBNAME}_nexus_${JOBID}.h5
city detsim    detsimTemplate.conf    -i ${JOBNAME}_nexus_${JOBID}.h5    -o ${JOBNAME}_detsim_${JOBID}.h5
city hypathia  hypathiaTemplate.conf  -i ${JOBNAME}_detsim_${JOBID}.h5   -o ${JOBNAME}_hypathia_${JOBID}.h5
city sophronia sophroniaTemplate.conf -i ${JOBNAME}_hypathia_${JOBID}.h5 -o ${JOBNAME}_sophronia_${JOBID}.h5

rm ${JOBNAME}.h5
rm *LT*
rm *PSF*
rm *map*

# Only keep first 1000 files for validation purposes
if (( JOBID > 1000 )); then
    rm ${JOBNAME}_detsim_${JOBID}.h5
    rm ${JOBNAME}_hypathia_${JOBID}.h5
fi

ls -ltrh

echo "Taring the h5 files"
tar -cvf ${JOBNAME}.tar *.h5

# Cleanup
rm *.h5
rm *.mac
rm *.conf
rm *.py

echo "FINISHED....EXITING" 

end=`date +%s`
let deltatime=end-start
let hours=deltatime/3600
let minutes=(deltatime/60)%60
let seconds=deltatime%60
printf "Time spent: %d:%02d:%02d\n" $hours $minutes $seconds 