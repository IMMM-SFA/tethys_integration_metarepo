import xarray as xr
import pandas as pd
from tethys.datareader.maps import load_region_map
from tethys.datareader.regional import load_region_data
import os

bounds = [25.0625, 52.9375, -124.9375, -67.0625]
mapfile = '/pic/projects/im3/tethys/tethys-im3-scenarios/data/maps/{}.tif'

sectors = dict(
  states = ['Domestic', 'Manufacturing', 'Mining', 'electricity/biomass', 'electricity/coal', 'electricity/gas', 'electricity/geothermal', 'electricity/nuclear', 'electricity/refined liquids', 'electricity/solar'],
  USA = ['Beef', 'Dairy', 'Pork', 'Poultry', 'SheepGoat'],
  USAbasins = ['Corn', 'Wheat', 'Rice', 'RootTuber', 'OilCrop', 'SugarCrop', 'OtherGrain', 'FiberCrop', 'FodderGrass', 'FodderHerb', 'biomass', 'MiscCrop', 'PalmFruit']
)

def spatial_comparison(scenario, demand):

  ds = xr.open_mfdataset(f'/pic/projects/im3/tethys/tethys-im3-scenarios/output/{scenario}/*_{demand}.nc')
  
  tethys_df = pd.DataFrame()
  for shape in ['states', 'USA', 'USAbasins']:
    shapemap = load_region_map(mapfile.format(shape), target_resolution=0.125, masks=True, bounds=bounds)
    shapesectors = [i.replace('/', '_') for i in sectors[shape]]
    shapesectors = [i for i in shapesectors if i in ds]
    sums = ds[shapesectors].where(shapemap, 0).sum(dim=('lat', 'lon')).compute()
    df = sums.drop('spatial_ref').to_dataframe()
    df = df.melt(var_name='sector', ignore_index=False).reset_index()
    tethys_df = pd.concat([tethys_df, df])
  
  tethys_df = tethys_df.set_index(['region', 'sector', 'year']).rename(columns=dict(value='value_tethys'))
  
  
  gcam_db = f'/pic/projects/im3/gcamusa/gcam-usa-im3/output/database_{scenario}'
  if scenario in ['rcp85cooler_ssp3', 'rcp85hotter_ssp3']:
    gcam_db += '_rcp85gdp'
  
  gcam_df = load_region_data(gcam_db, sectors=[i for j in sectors.values() for i in j], demand_type=demand)
  gcam_df.sector = gcam_df.sector.str.replace('/', '_')
  gcam_df = gcam_df.set_index(['region', 'sector', 'year']).rename(columns=dict(value='value_GCAM'))
  
  return tethys_df.join(gcam_df, how='left')
  
if __name__ == '__main__':
  SSPs = ['ssp3', 'ssp5']
  RCPs = ['rcp45', 'rcp85']
  TEMPs = ['cooler', 'hotter']
  DEMANDs = ['withdrawals', 'consumption']

  for SSP in SSPs:
    for RCP in RCPs:
      for TEMP in TEMPs:
        for DEMAND in DEMANDs:
          df = spatial_comparison(f'{RCP}{TEMP}_{SSP}', DEMAND)
          df.to_csv(os.path.join('/pic/projects/im3/tethys/tethys-im3-scenarios/analysis/', f'{RCP}{TEMP}_{SSP}_{DEMAND}.csv'))