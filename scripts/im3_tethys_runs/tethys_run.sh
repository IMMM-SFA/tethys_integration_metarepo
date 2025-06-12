#!/bin/bash
#SBATCH -A im3
#SBATCH -t 179
#SBATCH -N 1

# usage: 
# generic: sbatch tethys_run.sh # will run run_scenario_decep.py with all scenarios
# one scenario short: sbatch -p short,slurm tethys_run.sh run_scenario_decep.py rcp45cooler_ssp3

# locate to the directory 
cd /rcfs/projects/im3/tethys/tethys-metarepo/scripts/im3_tethys_runs

# load packages and environment 
module unload python/3.7.0
module load python/miniconda3.9
source /share/apps/python/miniconda3.9/etc/profile.d/conda.sh

# create the environment for the first time:
# conda create -n env-tethys python=3.9
# conda activate /people/niaz981/.conda/envs/env-tethys
conda activate env-tethys 

# install packages for the first time
# cd /rcfs/projects/im3//tethys/tethys-code 
# pip install -e .

# default script name and scenario
SCRIPT_NAME=${1:-run_scenario_decep.py}  # default to run_scenario_decep.py if no script is provided
SCENARIO=${2:-}  # optional scenario argument

# add a line break or vertical space after or before every echo
echo "==================================================="
echo "Starting Tethys run script: $SCRIPT_NAME"
echo "==================================================="

echo ""
echo "Current directory: $(pwd)"
echo "Start time: $(date)"
start=`date +%s.%N` # start timer
echo ""

# run tethys
echo "==================================================="
# Check if a scenario name is provided as an argument
if [ -n "$SCENARIO" ]; then
    echo -e "Running script: $SCRIPT_NAME with scenario: $SCENARIO \n"
    python $SCRIPT_NAME $SCENARIO
else
    echo -e "Running script: $SCRIPT_NAME with all scenarios \n"
    python $SCRIPT_NAME
fi
echo "==================================================="

# check error status and print error message
err=$?

# Define the associative array with exit status codes and error messages
declare -A error_messages=(
    [0]="Success - Tethys ran successfully."
    [1]="Generic Error - Tethys encountered an unspecified error."
    [2]="Misuse of Shell Builtins - Tethys misused a shell builtin."
    [126]="Command Not Executable - Tethys could not be executed."
    [127]="Command Not Found - Tethys was not found in the system's PATH."
    [128]="Invalid Exit Value - Tethys terminated due to an uncaught signal."
    [130]="Command Interrupted - Tethys was interrupted by the user."
    [137]="Command Killed - Tethys was killed, possibly due to resource limitations."
    [255]="Exit Status Out of Range - The exit status was out of the valid range."
)

# Print the error message based on the exit status
if [[ $err -eq 0 || -z ${error_messages[$err]} ]]; then
    echo "Error: Unknown error occurred. Exit Status: $err"
else
    echo "Error: ${error_messages[$err]} (Exit Status: $err)"
fi

end=`date +%s.$N`
runtime=$( echo "($end - $start) / 60" | bc -l )
echo -e "\n Run completed in $runtime minutes \n"

# deactivate the environment
conda deactivate

# exit with the error code
exit $err