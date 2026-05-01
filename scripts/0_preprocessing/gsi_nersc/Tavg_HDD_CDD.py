# -*- coding: utf-8 -*-
"""
Created on Sun May  7 15:06:47 2023

@author: elda639
"""

# %% Importing Packages
import numpy as np
import os
import pandas as pd
import datetime
import xarray as xr
    
# %% Define Working Directory
print('Define Working Directory')
cwd = os.getcwd()
os.chdir(r'/global/cfs/projectdirs/m2702/dardiry/Tethys_Demand/')
wd = os.getcwd()
scenario='rcp45cooler_2060_2099'
start_year=1980
end_year=2020
# metDir='/global/cfs/projectdirs/m2702/dardiry/Tethys_Demand/Outputs/TGW/Future/%s/daily/met_variables/'%(scenario)
# outputDir='/global/cfs/projectdirs/m2702/dardiry/Tethys_Demand/Outputs/TGW/Future/%s/daily/HDD_CDD/'%(scenario)

metDir='/global/cfs/projectdirs/m2702/dardiry/Tethys_Demand/Outputs/TGW/Historical/daily/met_variables/'
outputDir='/global/cfs/projectdirs/m2702/dardiry/Tethys_Demand/Outputs/TGW/Historical/daily/HDD_CDD/'

# %%
#read tgw-mosart latlon elevation file
df_latlon=pd.read_csv(wd+'/Scripts/MOSART_TGW_LATLON_ELEV.csv')


for year in range(start_year,end_year+1):
    print(year-start_year,'processing TGW variables for year %d'%year)
    os.chdir(metDir)
    tethys_wrf_daily=xr.open_dataset('wrf_variables_tethys_demand_%d.nc'%year)
    
    # convert netCDF to pandas dataframe
    df_tethys_wrf_daily = tethys_wrf_daily.to_dataframe()
    #flatten dataframe to expand indices (lon, lat, time)
    df_tethys_wrf_daily = df_tethys_wrf_daily.reset_index()
    nn=len(df_tethys_wrf_daily)


    df_met_var=df_tethys_wrf_daily[['time','lat','lon','Tavg']]
    df_latlon = df_latlon.astype('float32')  # needed for merging the same type of columns
    df_met_var_all=df_latlon.merge(df_met_var, how='left',
                            right_on=['lat','lon'],
                            left_on=['lat_tgw','lon_tgw'])
    
    df_met_var_all.drop(['lat','lon'],inplace=True,axis=1)
    # number of rows should be equal to N(mosart grids) x N (time steps)=
    Ngrid=len(df_latlon)
    Ntime=len(np.unique(df_tethys_wrf_daily.time.values))
    
    
    # filter dates
    start_date=datetime.datetime(year,1,1)
    end_date=datetime.datetime(year,12,31)
    df_met_var_all=df_met_var_all[(df_met_var_all['time'] >= start_date) & (df_met_var_all['time'] <= end_date)]
    # df_met_var_all=df_met_var_all[(df_met_var_all['time'] >= start_date)]    
    
    # calculate HDD-CDD for all grids for one year
    
    t1=df_met_var_all[df_met_var_all['Tavg']<=18].index
    t2=df_met_var_all[df_met_var_all['Tavg']>18].index
    
    
    df_met_var_all['HDD']=18-df_met_var_all['Tavg']
    df_met_var_all.loc[t2,'HDD']=np.nan
    df_met_var_all['CDD']=df_met_var_all['Tavg']-18
    df_met_var_all.loc[t1,'CDD']=np.nan



    df_met_var_all['month'] = df_met_var_all['time'].dt.month
    df_met_var_all['year'] = df_met_var_all['time'].dt.year

    cols=['ID', 'year', 'month', 'elevation', 
          'lat_mosart', 'lon_mosart',
           'lat_tgw', 'lon_tgw']
    df_mon_sum=df_met_var_all.groupby(cols).sum().reset_index()
    df_mon_avg=df_met_var_all.groupby(cols).mean().reset_index()


    df_met_mon=df_mon_sum.copy()
    df_met_mon['Tavg']=df_mon_avg['Tavg']

    
    print('----writing output file')
    os.chdir(outputDir)
    df_met_mon.to_csv('Tavg_HDD_CDD_%d.csv'%year,sep = ',',index=False)
  