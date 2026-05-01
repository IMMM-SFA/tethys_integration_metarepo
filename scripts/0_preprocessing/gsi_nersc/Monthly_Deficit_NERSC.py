# -*- coding: utf-8 -*-
"""
Created on Sun May  7 15:06:47 2023

@author: elda639
"""

# %% Importing Packages
import numpy as np
import os
import pandas as pd
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from os import path
import geopandas as gpd
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import datetime
import xarray as xr
import pandas as pd
import geopandas as gpd
import numpy as np
from glob import glob
import time
import os
import pyet
from eto import ETo
# import pyeto
import geopy.distance
import h3
import math
from pandas import to_numeric, Series
from numpy import tan, cos, pi, sin, arccos, mod, exp, log, nanmax, isnan,where
from pandas import to_numeric, Series
from xarray import DataArray
 
    
# %% Define Working Directory
print('Define Working Directory')
cwd = os.getcwd()
os.chdir(r'/global/project/projectdirs/m2702/dardiry/Tethys_Demand/')
wd = os.getcwd()
# wrf_dir='/global/project/projectdirs/m2702/dardiry/CLM_Forcing/WRF_Climate_Forcing/Historical'

outputDir='/global/project/projectdirs/m2702/dardiry/Tethys_Demand/Outputs/TGW/Historical/daily/GSI/'

outputDir_deficit='/global/project/projectdirs/m2702/dardiry/Tethys_Demand/Outputs/TGW/Historical/monthly/'

# %%
#read tgw-mosart latlon elevation file
df_latlon=pd.read_csv(wd+'/Scripts/MOSART_TGW_LATLON_ELEV.csv')


for year in range(2020,2021):
    print(year-1979,'processing TGW variables for year %d'%year)
    os.chdir(outputDir)
    da_p_et_daily=xr.open_dataset('TGW_PRECIP_ET0_GSI_%d.nc'%year)

    # convert netCDF to pandas dataframe
    df_p_et_daily = da_p_et_daily.to_dataframe()
    #flatten dataframe to expand indices (lon, lat, time)
    # df_p_et_daily = df_p_et_daily.reset_index()
    # nn=len(df_p_et_daily)
    if year<2020:
        da_p_et_daily = da_p_et_daily.drop([np.datetime64('%d-01-01'%(year+1))], dim='time')
    da_p_et_daily = da_p_et_daily.drop(['GSI'])
    da_p_et_daily['precip']=da_p_et_daily['precip']*1000  # convert m to mm
    da_p_et_monthly = da_p_et_daily.resample(time='1MS').sum(dim='time')
    df_p_et_monthly = da_p_et_monthly.to_dataframe()


    x = np.where(df_p_et_monthly['precip']>df_p_et_monthly['PET'], 
                 np.abs(1/(df_p_et_monthly['precip']-df_p_et_monthly['PET'])), 
                        np.abs(df_p_et_monthly['precip']-df_p_et_monthly['PET']))
    df_p_et_monthly['deficit']=x
    df_p_et_monthly.columns=['id','precip','eto','deficit']
    da_p_et_monthly=df_p_et_monthly.to_xarray()

    # water deficit calculation following Moore et al. (2015)
    os.chdir(outputDir_deficit)
    da_p_et_monthly.to_netcdf('Monthly_Deficit_%d.nc'%year)
  
    
