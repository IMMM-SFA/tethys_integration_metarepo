#!/bin/sh

#SBATCH -n 1
#SBATCH -t 10000
#SBATCH -A IHESD
#SBATCH -J tethys

source  /etc/profile.d/modules.sh
module load python/miniconda3.9 gcc/7.3.0 netcdf/4.3.2 gdal/3.4.3

source /pic/projects/im3/tethys/tethys-im3-scenarios/venv/bin/activate

date
python /pic/projects/im3/tethys/tethys-im3-scenarios/data/monthly/deficit/compute_deficit.py
date
echo 'completed'
