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
# %% Functions for ET 
def atm_pressure(altitude):
    """
    Estimate atmospheric pressure from altitude.
    Calculated using a simplification of the ideal gas law, assuming 20 degrees
    Celsius for a standard atmosphere. Based on equation 7, page 62 in Allen
    et al (1998).
    :param altitude: Elevation/altitude above sea level [m]
    :return: atmospheric pressure [kPa]
    :rtype: float
    """
    tmp = (293.0 - (0.0065 * altitude)) / 293.0
    return np.power(tmp, 5.26) * 101.3


def delta_svp(t):
    """
    Estimate the slope of the saturation vapour pressure curve at a given
    temperature.
    Based on equation 13 in Allen et al (1998). If using in the Penman-Monteith
    *t* should be the mean air temperature.
    :param t: Air temperature [deg C]. Use mean air temperature for use in
        Penman-Monteith.
    :return: Saturation vapour pressure [kPa degC-1]
    :rtype: float
    """
    tmp = 4098 * (0.6108 * np.exp((17.27 * t) / (t + 237.3)))
    return tmp / np.power((t + 237.3), 2)

def psy_const(atmos_pres):
    """
    Calculate the psychrometric constant.
    This method assumes that the air is saturated with water vapour at the
    minimum daily temperature. This assumption may not hold in arid areas.
    Based on equation 8, page 95 in Allen et al (1998).
    :param atmos_pres: Atmospheric pressure [kPa]. Can be estimated using
        ``atm_pressure()``.
    :return: Psychrometric constant [kPa degC-1].
    :rtype: float
    """
    return 0.000665 * atmos_pres

def rh_from_avp_svp(avp, svp):
    """
    Calculate relative humidity as the ratio of actual vapour pressure
    to saturation vapour pressure at the same temperature.
    See Allen et al (1998), page 67 for details.
    :param avp: Actual vapour pressure [units do not matter so long as they
        are the same as for *svp*]. Can be estimated using functions whose
        name begins with 'avp_from'.
    :param svp: Saturated vapour pressure [units do not matter so long as they
        are the same as for *avp*]. Can be estimated using ``svp_from_t()``.
    :return: Relative humidity [%].
    :rtype: float
    """
    return 100.0 * avp / svp

def fao56_penman_monteith(net_rad, t, ws, svp, avp, delta_svp, psy, shf=0.0):
    """
    Estimate reference evapotranspiration (ETo) from a hypothetical
    short grass reference surface using the FAO-56 Penman-Monteith equation.
    Based on equation 6 in Allen et al (1998).
    :param net_rad: Net radiation at crop surface [MJ m-2 day-1]. If
        necessary this can be estimated using ``net_rad()``.
    :param t: Air temperature at 2 m height [deg Kelvin].
    :param ws: Wind speed at 2 m height [m s-1]. If not measured at 2m,
        convert using ``wind_speed_at_2m()``.
    :param svp: Saturation vapour pressure [kPa]. Can be estimated using
        ``svp_from_t()''.
    :param avp: Actual vapour pressure [kPa]. Can be estimated using a range
        of functions with names beginning with 'avp_from'.
    :param delta_svp: Slope of saturation vapour pressure curve [kPa degC-1].
        Can be estimated using ``delta_svp()``.
    :param psy: Psychrometric constant [kPa deg C]. Can be estimatred using
        ``psy_const_of_psychrometer()`` or ``psy_const()``.
    :param shf: Soil heat flux (G) [MJ m-2 day-1] (default is 0.0, which is
        reasonable for a daily or 10-day time steps). For monthly time steps
        *shf* can be estimated using ``monthly_soil_heat_flux()`` or
        ``monthly_soil_heat_flux2()``.
    :return: Reference evapotranspiration (ETo) from a hypothetical
        grass reference surface [mm day-1].
    :rtype: float
    """
    a1 = (0.408 * (net_rad - shf) * delta_svp /
          (delta_svp + (psy * (1 + 0.34 * ws))))
    a2 = (900 * ws / (t+273) * (svp - avp) * psy /
          (delta_svp + (psy * (1 + 0.34 * ws))))
    return a1 + a2

def wind_speed_2m(ws, z):
    """
    Convert wind speed measured at different heights above the soil
    surface to wind speed at 2 m above the surface, assuming a short grass
    surface.
    Based on FAO equation 47 in Allen et al (1998).
    :param ws: Measured wind speed [m s-1]
    :param z: Height of wind measurement above ground surface [m]
    :return: Wind speed at 2 m above the surface [m s-1]
    :rtype: float
    """
    return ws * (4.87 / np.log((67.8 * z) - 5.42))
# %% Define function for daylight hours

def day_of_year(tindex):
    """Day of the year (1-365) based on pandas.Index
    Parameters
    ----------
    tindex: pandas.DatetimeIndex
    Returns
    -------
    pandas.Series with ints specifying day of year.
    """
    return Series(to_numeric(tindex.dt.dayofyear), dtype=int)

def sunset_angle(sol_dec, lat):
    """Sunset hour angle from latitude and solar declination - daily [rad].
    Parameters
    ----------
    sol_dec: float/pandas.Series/xarray.DataArray
        solar declination [rad]
    lat: float/xarray.DataArray
        the site latitude [rad]
    Returns
    -------
    pandas.Series/xarray.DataArray containing the calculated sunset hour
    angle - daily [rad]
    Notes
    -----
    Based on equations 25 in :cite:t:`allen_crop_1998`.
    """
    if isinstance(lat, DataArray):
        lat = lat.expand_dims(dim={"time": sol_dec.index}, axis=0)
        return arccos(-tan(sol_dec.values) * tan(lat).T).T
    else:
        return arccos(-tan(sol_dec) * tan(lat))

def solar_declination(j):
    """Solar declination from day of year [rad].
    Parameters
    ----------
    j: pandas.Series
        day of the year (1-365)
    Returns
    -------
    pandas.Series of solar declination [rad].
    Notes
    -------
    Based on equations 24 in :cite:t:`allen_crop_1998`.
    """
    return 0.409 * sin(2. * pi / 365. * j - 1.39)

    
def daylight_hours(tindex, lat):
    """Daylight hours [hour].

    Parameters
    ----------
    tindex: pandas.DatetimeIndex
    lat: float/xarray.DataArray
        the site latitude [rad]

    Returns
    -------
    pandas.Series or xarray.DataArray containing the calculated
    daylight hours [hour]

    Notes
    -----
    Based on equation 34 in :cite:t:`allen_crop_1998`.

    """
    j = day_of_year(tindex)
    sol_dec = solar_declination(j)
    sangle = sunset_angle(sol_dec, lat)
    # Account for subpolar belt which returns NaN values
    dl = 24 / pi * sangle
    if isinstance(lat, DataArray):
        sol_dec = ((dl / dl).T * sol_dec.values).T
    dl = where((sol_dec > 0) & (isnan(dl)), nanmax(dl), dl)
    dl = where((sol_dec < 0) & (isnan(dl)), 0, dl)
    return dl
# %% GSI Indicators
def calc_iTmin(tmin,tmin_min=-2,tmin_max=5):
    if tmin<=tmin_min:
        return 0
    elif tmin>=tmin_max:
        return 1
    elif  math.isnan(tmin):
        return -9999
    else:
        return (tmin-tmin_min)/(tmin_max-tmin_min)  

def calc_iVPD(vpd,vpd_min=900,vpd_max=4100):
    if vpd<=vpd_min:
        return 0
    elif vpd>=vpd_max:
        return 1
    elif  math.isnan(vpd):
        return -9999
    else:
        return (vpd-vpd_min)/(vpd_max-vpd_min)  

def calc_iPhoto(photo,photo_min=10,photo_max=11):
    if photo<=photo_min:
        return 0
    elif photo>=photo_max:
        return 1
    elif  math.isnan(photo):
        return -9999
    else:
        return (photo-photo_min)/(photo_max-photo_min)  
    
# %% Define Working Directory
print('Define Working Directory')
cwd = os.getcwd()
os.chdir(r'/global/cfs/projectdirs/m2702/dardiry/Tethys_Demand/')
wd = os.getcwd()
scenario='rcp85hotter_2020_2059'
start_year=2040
end_year=2059
# wrf_dir='/global/project/projectdirs/m2702/dardiry/CLM_Forcing/WRF_Climate_Forcing/Historical'
metDir='/global/cfs/projectdirs/m2702/dardiry/Tethys_Demand/Outputs/TGW/Future/%s/daily/met_variables/'%(scenario)
outputDir='/global/cfs/projectdirs/m2702/dardiry/Tethys_Demand/Outputs/TGW/Future/%s/daily/GSI/'%(scenario)


# %%
#read tgw-mosart latlon elevation file
df_latlon=pd.read_csv(wd+'/Scripts/MOSART_TGW_LATLON_ELEV.csv')


for year in range(start_year,end_year+1):
    print(year-start_year,'processing TGW variables for year %d'%year)
    os.chdir(metDir)
    tethys_wrf_daily=xr.open_dataset('wrf_variables_tethys_demand_%d.nc'%year)
    tethys_wrf_daily['wind'] = tethys_wrf_daily['Wind']
    tethys_wrf_daily = tethys_wrf_daily.drop(['Wind'])
    tethys_wrf_daily['precip'] = tethys_wrf_daily['Prec']
    tethys_wrf_daily = tethys_wrf_daily.drop(['Prec'])
    tethys_wrf_daily['rn']=(tethys_wrf_daily['LW']-tethys_wrf_daily['SW'])*86400/1000000  # convert units w/m2 to Mj/m2/day
    tethys_wrf_daily['lat_rad']=pyet.deg_to_rad(tethys_wrf_daily['lat'])
    
    # convert netCDF to pandas dataframe
    df_tethys_wrf_daily = tethys_wrf_daily.to_dataframe()
    #flatten dataframe to expand indices (lon, lat, time)
    df_tethys_wrf_daily = df_tethys_wrf_daily.reset_index()
    nn=len(df_tethys_wrf_daily)


    df_met_var=df_tethys_wrf_daily[['time','lat','lon','lat_rad','Tmax','Tmin','Tavg','precip','wind','ea','es','VPD','rn']]
    df_latlon = df_latlon.astype('float32')  # needed for merging the same type of columns
    df_met_var_all=df_latlon.merge(df_met_var, how='left',
                            right_on=['lat','lon'],
                            left_on=['lat_tgw','lon_tgw'])
    
    df_met_var_all.drop(['lat','lon'],inplace=True,axis=1)
    # number of rows should be equal to N(mosart grids) x N (time steps)=
    Ngrid=len(df_latlon)
    Ntime=len(np.unique(df_tethys_wrf_daily.time.values))
    
    # print('checking size of dataframe')
    # if len(df_met_var_all)==Ngrid*Ntime:
    #     print('meteorological dataframe size is correct!')
    # else:
    #     print('meteorological dataframe size is incorrect. Please check')
    
    # filter dates
    start_date=datetime.datetime(year,1,1)
    end_date=datetime.datetime(year+1,1,1)
    # df_met_var_all=df_met_var_all[(df_met_var_all['time'] >= start_date) & (df_met_var_all['time'] <= end_date)]
    # df_met_var_all=df_met_var_all[(df_met_var_all['time'] >= start_date)]    
    
    # calculate PET for all grids for one year
    print('----calculate ET0')
    elev=df_met_var_all['elevation'].values
    atmos_pres=atm_pressure(elev)
    psy=psy_const(atmos_pres)
    t=df_met_var_all['Tavg'].values
    delta=delta_svp(t)
    wind=df_met_var_all['wind'].values   # wind at 10m
    ws=wind_speed_2m(wind,z=10)   #wind at 2m
    net_rad=df_met_var_all['rn'].values
    avp=df_met_var_all['ea'].values*100/1000   # from millibar to pascal to kPa
    svp=df_met_var_all['es'].values*100/1000   # from millibar to pascal to kPa
    shf=0    # soil heat flux 
    
    et0=fao56_penman_monteith(net_rad,t, ws, svp, avp, delta, psy, shf=0.0)
    df_met_var_all['et0']=et0
    
    
    
    # Calculate GSI indicators
    print('----calculate GSI')
    tmin=df_met_var_all.Tmin.values
    calc_iTmin_func = np.vectorize(calc_iTmin)
    iTmin=calc_iTmin_func(tmin)

    vpd=df_met_var_all.VPD.values*100  # convert millibar to pascal
    calc_ivpd_func = np.vectorize(calc_iVPD)
    iVPD=calc_ivpd_func(vpd)



    photo=daylight_hours(df_met_var_all[['time']].time,df_met_var_all['lat_rad'])
    calc_photo_func = np.vectorize(calc_iPhoto)
    iPhoto=calc_photo_func(photo)


    GSI=iTmin*iVPD*iPhoto
    df_met_var_all['GSI']=GSI
    
    
    print('----writing output file')
    df_precip_et0_gsi=df_met_var_all[['ID','time','lat_mosart','lon_mosart','precip','et0','GSI']]
    df_precip_et0_gsi.columns=['ID','time','lat','lon','precip','PET','GSI']
    os.chdir(outputDir)
    df_precip_et0_gsi=df_precip_et0_gsi.set_index(['time','lat','lon'])
    ds_precip_et0_gsi=df_precip_et0_gsi.to_xarray()
    ds_precip_et0_gsi.to_netcdf('TGW_PRECIP_ET0_GSI_%d.nc'%year)
  
    # precipitation in meters
    # ETo in mm/day
