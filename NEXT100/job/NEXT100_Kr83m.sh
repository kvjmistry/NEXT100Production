#!/bin/bash

echo "Starting Job" 

JOBID=$1
echo "The JOBID number is: ${JOBID}" 

JOBNAME=$2
echo "The JOBNAME number is: ${JOBNAME}" 

echo "JOBID $1 running on `whoami`@`hostname`"

start=`date +%s`

# Setup nexus
echo "Setting Up Software" 
source /software/nexus/setup_nexus.sh
source /software/IC/setup_IC.sh

echo "untaring files"
tar -xvf files.tar
rm files.tar

# Set the configurable variables
N_EVENTS=1000
CONFIG=${JOBNAME}.config.mac
INIT=${JOBNAME}.init.mac


echo "N_EVENTS: ${N_EVENTS}"

SEED=$((${N_EVENTS}*${JOBID} + ${N_EVENTS}))
echo "The seed number is: ${SEED}" 

# Change the config in the files
sed -i "s#.*random_seed.*#/nexus/random_seed ${SEED}#" ${CONFIG}
sed -i "s#.*start_id.*#/nexus/persistency/start_id ${SEED}#" ${CONFIG}

# Print out the config and init files
cat ${INIT}
cat ${CONFIG}

# Generation + Reco
echo "Running NEXUS and IC" 
nexus -n $N_EVENTS ${INIT}
python compress_nexus.py NEXT100_Kr83m.h5 NEXT100_Kr83m_nexus_${JOBID}.h5
city detsim   detsimTemplate.conf   -i NEXT100_Kr83m_nexus_${JOBID}.h5    -o NEXT100_Kr83m_detsim_${JOBID}.h5
city hypathia hypathiaTemplate.conf -i NEXT100_Kr83m_detsim_${JOBID}.h5   -o NEXT100_Kr83m_hypathia_${JOBID}.h5
city dorothea dorotheaTemplate.conf -i NEXT100_Kr83m_hypathia_${JOBID}.h5 -o NEXT100_Kr83m_dorothea_${JOBID}.h5

rm NEXT100_Kr83m.h5
rm *LT*
rm *PSF*

ls -ltrh

echo "Taring the h5 files"
tar -cvf NEXT100_Kr83m.tar *.h5

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