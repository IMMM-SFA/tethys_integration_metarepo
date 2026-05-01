# -*- coding: utf-8 -*-
"""
Created on Thu Feb 10 10:37:09 2022

@author: elda639
"""

# this was needed to prevent errors in the geospatial methods on NERSC...
# %env PROJ_LIB=/global/homes/t/thurber/.conda/pkgs/proj-8.2.1-h277dcde_0/share/proj/
print('Loading Python Packages')
import xarray as xr
import salem
import pandas as pd
import geopandas as gpd
import numpy as np
from glob import glob
import time
import os

# %% Define Working Directory
print('Define Working Directory')
cwd = os.getcwd()
os.chdir(r'/global/cfs/projectdirs/m2702/dardiry/Tethys_Demand/')
wd = os.getcwd()
# wrf_dir='/global/project/projectdirs/m2702/dardiry/CLM_Forcing/WRF_Climate_Forcing/Historical'

# %% 
rcp='45'
climate='cooler'
start_year=2060
end_year=2099
scenario='rcp%s%s_%d_%d'%(rcp,climate,start_year,end_year)

# path prefix to the WRF data; will append the year in the code below
wrf_path = '/global/cfs/projectdirs/m2702/gsharing/tgw-wrf-conus/%s/hourly/tgw_wrf_rcp%s%s_hourly_'%(scenario,rcp,climate)

outputDir='/global/cfs/projectdirs/m2702/dardiry/Tethys_Demand/Outputs/TGW/Future/%s/daily/met_variables'%(scenario)


loop_start=2093
loop_end=2099
for year in range(loop_start,loop_end+1):
    
    start_time = time.time()
    print('Processing WRF Forcing for %s (%d)'%(scenario,year))
    # select the WRF files corresponding to this year
    # we need to get the previous file too, in order to accurately know the accumulated precipitation on the first day
    wrf_files = sorted(glob(f'{wrf_path}{year-1}*') + glob(f'{wrf_path}{year}*'))
    if year!=start_year: 
        wrf_files = wrf_files[[idx for idx, s in enumerate(wrf_files) if f'{year}-' in s][0]-1:]
    
    
    # use salem (a version of xarray enhanced to read WRF files) to open all the WRF files at once
    # this can take a couple minutes
    wrf_data = salem.open_mf_wrf_dataset(wrf_files)

    tethys_wrf_data=wrf_data

       
    print('Extract Forcing Variables for Tethys Model')

    # deaccumulate the total precipitation
    tethys_wrf_data['Prec'] = tethys_wrf_data['RAINC'] + tethys_wrf_data['RAINSH'] + tethys_wrf_data['RAINNC']
    tethys_wrf_data['Prec'].values = np.diff(tethys_wrf_data['Prec'].values, axis=0, prepend=np.array([tethys_wrf_data['Prec'][0].values]))
    tethys_wrf_data['Prec']=tethys_wrf_data['Prec']/1000   # precipitation in meters
    # calculate wind speed at 10m
    tethys_wrf_data['Wind'] = (tethys_wrf_data['U10']**2 + tethys_wrf_data['V10']**2) ** (1/2)

    # calculate specific humidity
    tethys_wrf_data['SH'] = (tethys_wrf_data['Q2'] / (1 + tethys_wrf_data['Q2'])).clip(0)

    # calculate relative humidity
    tethys_wrf_data['RH'] = (
        0.263 * tethys_wrf_data['SH'] * tethys_wrf_data['PSFC'] / np.exp(17.67 * (tethys_wrf_data['T2'] - 273.16) / (tethys_wrf_data['T2'] - 29.65))
    ).clip(0, 100)

    # convert temperature from kelvin to celsius
    tethys_wrf_data['Temp'] = tethys_wrf_data['T2'] - 273.15
    
    # vapor pressure in millibar=100 pascal
    tethys_wrf_data['es'] = (6.1078*xr.ufuncs.exp((17.269*tethys_wrf_data['Temp'])/(237.3+tethys_wrf_data['Temp'])))  
    tethys_wrf_data['ea'] = (6.1078*xr.ufuncs.exp((17.269*tethys_wrf_data['Temp'])/(237.3+tethys_wrf_data['Temp'])))*(tethys_wrf_data['RH']*0.01)
    tethys_wrf_data['VPD'] = (6.1078*xr.ufuncs.exp((17.269*tethys_wrf_data['Temp'])/(237.3+tethys_wrf_data['Temp'])))*(1-tethys_wrf_data['RH']*0.01)

    # rename radiation variables
    tethys_wrf_data = tethys_wrf_data.rename({'GLW': 'LW', 'SWDOWN': 'SW'})

    variables = ['Prec','Temp','es','ea','VPD','LW','SW','Wind','PSFC']
    tethys_wrf_data[variables]

    tethys_var_daily=tethys_wrf_data[['es','ea','VPD','LW','SW','Wind','PSFC']].resample(time='1D').mean()
    tethys_prec_daily=tethys_wrf_data['Prec'].resample(time='1D').sum().rename('Prec')
    tethys_tmax_daily=tethys_wrf_data['Temp'].resample(time='1D').max().rename('Tmax')
    tethys_tmin_daily=tethys_wrf_data['Temp'].resample(time='1D').min().rename('Tmin')
    tethys_tavg_daily=tethys_wrf_data['Temp'].resample(time='1D').mean().rename('Tavg')

    tethys_wrf_daily=xr.merge([tethys_var_daily, tethys_prec_daily,
              tethys_tavg_daily, tethys_tmax_daily,tethys_tmin_daily])

    ###### Save data in netcdf file
    print('Writing NETCDF file......')

    os.chdir(outputDir)
    tethys_wrf_daily.to_netcdf('wrf_variables_tethys_demand_%d.nc'%year)

    
    
    
    


