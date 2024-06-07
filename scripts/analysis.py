import os
import pandas as pd
import xarray as xr
from tethys.datareader.maps import load_region_map

bounds = [25.0625, 52.9375, -124.9375, -67.0625]

county_mapfile = '/pic/projects/im3/tethys/tethys-im3-scenarios/analysis/counties.tif'
county_namefile = '/pic/projects/im3/tethys/tethys-im3-scenarios/analysis/county_names.csv'

counties = load_region_map(county_mapfile, target_resolution=0.125, masks=True, namefile=county_namefile, bounds=bounds)


# select scenario/year for comparison

demand = 'withdrawals'  # 'consumption' or 'withdrawals'
year = 2015
scenario = 'Historical'
output_dir = os.path.join('/pic/projects/im3/tethys/tethys-im3-scenarios/output', scenario)

km3_per_year_TO_Mgal_per_day = 2.642e+5 / 365

sectors = ['Domestic', 'Electricity', 'Manufacturing', 'Mining', 'Livestock', 'Irrigation']

ds = xr.Dataset()
for sector in sectors:
  filename = os.path.join(output_dir, f'{sector}_{demand}.nc')
  ds[sector] = xr.open_dataset(filename).sel(year=year).to_array().sum(dim='variable')

county_sums = ds.where(counties, 0).sum(dim=('lat', 'lon')).compute()


tethys_df = county_sums.drop(('year', 'spatial_ref')).to_dataframe()
tethys_df *= km3_per_year_TO_Mgal_per_day  # convert units to match usgs dataset


# process usgs dataset

usgs_file = '/pic/projects/im3/tethys/tethys-im3-scenarios/analysis/usco2015v2.0.csv'
usgs_all = pd.read_csv(usgs_file, skiprows=1)

usgs_df = usgs_all[['FIPS', 'STATE', 'COUNTY']].copy()
usgs_df['Domestic_USGS'] = usgs_all['PS-WFrTo'] + usgs_all['DO-WFrTo']
usgs_df['Irrigation_USGS'] = usgs_all['IR-WFrTo'] - usgs_all['IG-WFrTo'].str.replace('--', '0').astype(float)
usgs_df['Electricity_USGS'] = usgs_all['PT-WFrTo']  # fresh only
usgs_df['Manufacturing_USGS'] = usgs_all['IN-WFrTo']
usgs_df['Mining_USGS'] = usgs_all['MI-WFrTo']
usgs_df['Livestock_USGS'] = usgs_all['LI-WFrTo']

# merge

comparer = usgs_df.set_index('FIPS').join(tethys_df, how='right')
comparer = comparer.reindex(columns=['STATE', 'COUNTY'] + sorted(i for i in comparer.columns if i not in ['STATE', 'COUNTY']))

comparer['Total'] = comparer[sectors].sum(axis=1)
comparer['Total_USGS'] = comparer[[f'{sector}_USGS' for sector in sectors]].sum(axis=1)

