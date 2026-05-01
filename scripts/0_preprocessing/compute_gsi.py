import numpy as np
import pandas as pd
import xarray as xr


def reproject(da):
    return (da
            .drop_vars(('lon', 'lat'))
            .rename(west_east='x', south_north='y')
            .rio.write_crs('ESRI:102003')
            .rio.reproject('EPSG:4326', nodata=np.nan)
            .rename(x='lon', y='lat')
            .reindex(lon=np.arange(-124.9375, -67.0625+0.001, 0.125),
                     lat=np.arange(52.9375, 25.0625-0.001, -0.125), method='nearest')
            )

def daylengths(lats, days):
    radlats = lats * np.pi / 180  # latitude degrees in radians
    declinations = 23.45 * np.pi / 180 * np.cos(2 * np.pi * (days - 172) / 365)  # solar declination by day of year
    a = -0.833 * np.pi / 180  # solar altitude angle
    # compute hour angle of sunrise/sunset
    ha = np.arccos((np.sin(a) - np.sin(radlats) * np.sin(declinations)) / (np.cos(radlats) * np.cos(declinations)))
    return 2 * ha / 15 * 180 / np.pi  # hours of daylight


input_file = r'/pic/projects/im3/dardiry/Tethys_Demand/Outputs/TGW/{folder}/daily/met_variables/wrf_variables_tethys_demand_*.nc'
output_file = r'/pic/projects/im3/tethys/tethys-im3-scenarios/data/monthly/deficit/gsi_{scenario}.nc'

scenarios = ['rcp45cooler', 'rcp45hotter', 'rcp85cooler', 'rcp85hotter']

configs = [(f'Future/{scenario}_*', scenario) for scenario in scenarios]  # + [('Historical', 'Historical')]


def main():
    for folder, scenario in configs:

        ds = xr.open_mfdataset(input_file.format(folder=folder), preprocess=lambda x: x[['Tmin']].sel(time=x.time.dt.year == int(x.encoding['source'][-7:-3])))
        ds = ds.astype(np.float32)

        ds = (ds.clip(-2, 5) + 2) / 7
        ds *= daylengths(ds.lat, ds.time.dt.dayofyear.astype(np.float32).chunk(time=40)).clip(10, 11) - 10
        ds = ds.rename(Tmin='GSI')

        ds = ds.resample(time='1M').mean()

        template = ds.time.astype(np.float32).chunk(time=1) * reproject(ds.isel(time=0)).chunk()
        ds = ds.chunk(time=1).map_blocks(reproject, template=template)

        newtime = pd.MultiIndex.from_arrays([ds.time.dt.year.to_series(), ds.time.dt.month.to_series()])
        ds = ds.assign_coords(time=('time', newtime)).unstack()

        encoding = {'GSI': {'zlib': True, 'complevel': 5}}
        writer = ds.to_netcdf(output_file.format(scenario=scenario), encoding=encoding, compute=False)
        writer.compute()


if __name__ == '__main__':
    main()




