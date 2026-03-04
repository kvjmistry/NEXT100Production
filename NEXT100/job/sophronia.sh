#!/bin/bash

echo "Starting Job" 

JOBID=$1
echo "The JOBID number is: ${JOBID}" 

JOBNAME=$2
echo "The JOBNAME number is: ${JOBNAME}" 

PRESSURE=$3
echo "The pressure is: ${PRESSURE}" 

INFILE=$4
echo "The input file is: ${INFILE}" 

echo "JOBID ${JOBID} running on `whoami`@`hostname`"

start=`date +%s`

# Setup nexus
echo "Setting Up Software" 
source /software/nexus/setup_nexus.sh
source /software/IC/setup_IC.sh

echo "untaring files"
tar -xvf files_${PRESSURE}.tar
rm files_${PRESSURE}.tar


# Make sure output file name is consistent
sed -i "s#.*q_thr.*#q_thr = 0 * pes#" sophroniaTemplate.conf

echo "Printing Sophronia file"
cat sophroniaTemplate.conf

# Reco
echo "Running sophronia" 

# update the filename
fileout="${INFILE/hypathia/sophronia}"
fileout="${fileout%.h5}_lowth.h5"

city sophronia sophroniaTemplate.conf -i $INFILE -o ${fileout}

rm *LT*
rm *PSF*
rm *map*
rm GetGammaTables.py
rm *hypathia*

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