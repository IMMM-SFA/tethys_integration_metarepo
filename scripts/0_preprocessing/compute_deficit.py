import numpy as np
import pandas as pd
import xarray as xr


input_file = r'/pic/projects/im3/dardiry/Tethys_Demand/Outputs/TGW/{folder}/daily/GSI/TGW_PRECIP_ET0_GSI_*.nc'
output_file = r'/pic/projects/im3/tethys/tethys-im3-scenarios/data/monthly/deficit/deficit_{scenario}.nc'

scenarios = ['rcp45cooler', 'rcp45hotter', 'rcp85cooler', 'rcp85hotter']

configs = [('Historical', 'Historical')] + [(f'Future/{scenario}_*', scenario) for scenario in scenarios]


def main():
  for folder, scenario in configs:
    ds = xr.open_mfdataset(input_file.format(folder=folder), preprocess=lambda x: x.sel(time=x.time.dt.year==int(x.encoding['source'][-7:-3])))
    ds = ds[['precip', 'PET']]
    ds = ds.astype(np.float32)
    ds = ds.resample(time='1M').sum().chunk(time=1)
    
    ds['deficit'] = ds.PET - ds.precip
    ds = ds[['deficit']]
    
    newtime = pd.MultiIndex.from_arrays([ds.time.dt.year.to_series(), ds.time.dt.month.to_series()])
    ds = ds.assign_coords(time=('time', newtime)).unstack()
    
    encoding = {'deficit': {'zlib': True, 'complevel': 5}}
    writer = ds.to_netcdf(output_file.format(scenario=scenario), encoding=encoding, compute=False)
    writer.compute()

if __name__ == '__main__':
  main()
		



