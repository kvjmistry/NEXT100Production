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


# Reco
echo "Running IC" 
city buffy      buffy.conf          -i $INFILE                                 -o NEXT100_Kr83m_Full_buffy_${JOBID}.h5
city hypathia   hypathiaIrene.conf  -i NEXT100_Kr83m_Full_buffy_${JOBID}.h5    -o NEXT100_Kr83m_Full_hypathia_${JOBID}.h5
city dorothea   dorothea.conf       -i NEXT100_Kr83m_Full_hypathia_${JOBID}.h5 -o NEXT100_Kr83m_Full_dorothea_${JOBID}.h5

rm *LT*
rm *map*
rm $INFILE
rm NEXT100_Kr83m_Full_buffy_${JOBID}.h5
rm NEXT100_Kr83m_Full_hypathia_${JOBID}.h5

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