#!/bin/bash

echo "Starting Job" 

JOBID=$1
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
#source /software/IC/setup_IC.sh

echo "untaring files"
tar -xvf files_${PRESSURE}.tar
rm files_${PRESSURE}.tar

# Set the configurable variables
N_EVENTS=300 # will give ~1 event per job. Some jobs 0 events
CONFIG=${JOBNAME}.config.mac
INIT=${JOBNAME}.init.mac


echo "N_EVENTS: ${N_EVENTS}"

EID=$((${N_EVENTS}*${JOBID} + ${N_EVENTS}))
SEED=$((${JOBID} + 1))
echo "The seed number is: ${SEED}" 

# Change the config in the files
sed -i "s#.*random_seed.*#/nexus/random_seed ${SEED}#" ${CONFIG}
sed -i "s#.*start_id.*#/nexus/persistency/start_id ${EID}#" ${CONFIG}

# Print out the config and init files
cat ${INIT}
cat ${CONFIG}

# Generation + Reco
echo "Running NEXUS and IC" 
nexus -n $N_EVENTS ${INIT}
python compress_nexus.py NEXT100_Tl208_Port1a_Full.h5 NEXT100_Tl208_Port1a_Full_nexus_${JOBID}.h5
# city buffy    buffyTemplate.conf    -i NEXT100_Tl208_Port1a_Full_nexus_${JOBID}.h5    -o NEXT100_Tl208_Port1a_Full_buffy_${JOBID}.h5
# city hypathia hypathiaTemplate.conf -i NEXT100_Tl208_Port1a_Full_buffy_${JOBID}.h5    -o NEXT100_Tl208_Port1a_Full_hypathia_${JOBID}.h5
# city dorothea dorotheaTemplate.conf -i NEXT100_Tl208_Port1a_Full_hypathia_${JOBID}.h5 -o NEXT100_Tl208_Port1a_Full_dorothea_${JOBID}.h5

rm NEXT100_Tl208_Port1a_Full.h5
# rm NEXT100_Tl208_Port1a_Full_buffy_${JOBID}.h5
rm *LT*
rm *PSF*
rm *map*

ls -ltrh

echo "Taring the h5 files"
tar -cvf NEXT100_Tl208_Port1a_Full.tar *.h5

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