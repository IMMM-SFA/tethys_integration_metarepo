import numpy as np
import pandas as pd
import xarray as xr
from calendar import monthrange

deficit_file = r'/pic/projects/im3/tethys/tethys-im3-scenarios/data/monthly/deficit/deficit_{scenario}.nc'
gsi_file = r'/pic/projects/im3/tethys/tethys-im3-scenarios/data/monthly/deficit/gsi_{scenario}.nc'

output_file = r'/pic/projects/im3/tethys/tethys-im3-scenarios/data/monthly/deficit/irrigation_weight_{scenario}.nc'

scenarios = ['rcp45cooler', 'rcp45hotter', 'rcp85cooler', 'rcp85hotter'] # + ['Historical']

def main():
  for scenario in scenarios:
    deficit = xr.open_dataarray(deficit_file.format(scenario=scenario), chunks=dict(year=1))
    gsi = xr.open_dataarray(gsi_file.format(scenario=scenario), chunks=dict(year=1))
    ds = deficit * gsi
    ds /= xr.apply_ufunc(np.vectorize(lambda x, y: monthrange(x, y)[1]), ds.year, ds.month).astype(np.float32)
    ds /= ds.sum(dim='month').where(lambda x: x != 0, 1)

    encoding = {'weight': {'zlib': True, 'complevel': 5}}
    writer = ds.to_dataset(name='weight').to_netcdf(output_file.format(scenario=scenario), encoding=encoding, compute=False)
    writer.compute()

if __name__ == '__main__':
  main()
		



