import pandas as pd
import geopandas as gpd
import xarray as xr
import rioxarray
import numpy as np
from pyproj import Transformer
import cartopy as ct
from glob import glob

def cerf_to_tethys():
    
    # CERF data CRS to WGS84 CRS
    cerf_crs = 'ESRI:102003'
    to_crs = 'EPSG:4326'
    transformer = Transformer.from_crs(cerf_crs, to_crs)
    def crs_transform(row):
        lat, lon = transformer.transform(row['xcoord'], row['ycoord'])
        row['lat'] = lat
        row['lon'] = lon
        return row

    # translate CERF tech names into GPPD/Tethys tech categories
    tech_mapping = {
        'hydro': 'Hydro',
        'gas (steam)': 'Gas',
        'gridcerf_gas_cc_no-ccs_recirculating': 'Gas',
        'gridcerf_gas_turbine_no-ccs_no-cooling': 'Gas',
        'gridcerf_gas_cc_no-ccs_dry': 'Gas',
        'gridcerf_gas_cc_no-ccs_pond': 'Gas',
        'gridcerf_gas_cc_ccs_recirculating': 'Gas',
        'gridcerf_gas_cc_ccs_dry': 'Gas',
        'coal (conv pulv) (pre_1970)': 'Coal',
        'coal (conv pulv) (1970s)': 'Coal',
        'gridcerf_coal_igcc_ccs_recirculating': 'Coal',
        'gridcerf_coal_conventional_ccs_recirculating': 'Coal',
        'gridcerf_coal_igcc_ccs_dry': 'Coal',
        'gas (CC)': 'Gas',
        'gas (CT)': 'Gas',
        'refined liquids (CT)': 'Oil',
        'Gen_II_LWR': 'Nuclear',
        'gridcerf_nuclear_gen3_ap1000_pond': 'Nuclear',
        'gridcerf_nuclear_gen3_ap1000_recirculating': 'Nuclear',
        'coal (conv pulv) (1980s)': 'Coal',
        'coal (conv pulv) (2010s)': 'Coal',
        'solar_PV': 'Solar',
        'coal (conv pulv) (1990s)': 'Coal',
        'coal (conv pulv) (2000s)': 'Coal',
        'geothermal': 'Geothermal',
        'biomass (conv)': 'Biomass',
        'gridcerf_biomass_conventional_ccs_recirculating': 'Biomass',
        'gridcerf_biomass_conventional_ccs_dry': 'Biomass',
        'coal (conv pulv)': 'Coal',
        'refined liquids (steam)': 'Oil',
        'coal (IGCC) (2010s)': 'Coal',
        'refined liquids (CC)': 'Oil',
        'coal (IGCC) (1990s)': 'Coal',
        'solar_CSP': 'Solar',
        'gridcerf_solar_pv_centralized_no-cooling': 'Solar',
        'wind_onshore': 'Wind',
        'gridcerf_wind_onshore_hubheight80_no-cooling': 'Wind',
        'gridcerf_wind_onshore_hubheight100_no-cooling': 'Wind',
        'gridcerf_wind_onshore_hubheight120_no-cooling': 'Wind',
        'gridcerf_wind_offshore_hubheight140_no-cooling': 'Wind',
        'gridcerf_wind_onshore_hubheight140_no-cooling': 'Wind',
        'gridcerf_wind_offshore_hubheight160_no-cooling': 'Wind',
    }
    
    # Global Power Plants Database v1.3
    # https://datasets.wri.org/dataset/globalpowerplantdatabase
    file_gppd_plants = '../../data/powerplants/global_power_plant_database_v_1_3/global_power_plant_database.csv'
    # load Global Power Plant Database
    gppd_plants = pd.read_csv(file_gppd_plants)

    # create the Tethys grid
    tethys_points = np.meshgrid(
        np.arange(-179.9375, 180, 0.125),
        np.arange(89.9375, -90, -0.125)
    )
    tethys_points = pd.DataFrame({
        'lon': tethys_points[0].flatten(),
        'lat': tethys_points[1].flatten(),
    })
    tethys_points = gpd.GeoDataFrame(
        tethys_points,
        geometry=gpd.points_from_xy(tethys_points.lon, tethys_points.lat), crs="EPSG:4326"
    )

    # CERF scenarios
    scenarios = [
        'rcp45cooler_ssp3',
        'rcp45hotter_ssp3',
        'rcp45cooler_ssp5',
        'rcp45hotter_ssp5',
        'rcp85cooler_ssp3',
        'rcp85hotter_ssp3',
        'rcp85cooler_ssp5',
        'rcp85hotter_ssp5',
    ]

    for i in np.arange(len(scenarios)):
        
        file_im3_plants = f'../../data/powerplants/62fpt-0jr75/cerf_im3_western_us_plant_data/power_plant_data/{scenarios[i]}/power_plant_data_{scenarios[i]}.csv'
    
        # load IM3 west plants
        # map tech names
        im3_plants = pd.read_csv(
            file_im3_plants
        ).apply(
            crs_transform,
            axis=1
        )[[
            'region_name', 'unit_size_mw', 'tech_name', 'sited_year', 'retirement_year', 'lat', 'lon'
        ]]
        im3_plants['tech_name'] = im3_plants.tech_name.map(tech_mapping)
        im3_geo = gpd.GeoDataFrame(
            im3_plants,
            geometry=gpd.points_from_xy(im3_plants.lon, im3_plants.lat), crs="EPSG:4326"
        )

        # load IM3 east plants by year
        # (to prevent getting duplicate plants)
        for year in np.arange(2020, 2060, 5):
            im3_plants = pd.read_csv(
                f'../../data/powerplants/zero_lmp_cerf_conus_plants/sitings_{scenarios[i]}_{year}PI.csv'
            )
            if year == 2020:
                im3_plants = im3_plants[
                    (im3_plants.sited_year <= 2020) |
                    (im3_plants.sited_year > 2055)
                ]
                im3_plants['sited_year'] = 2020
            else:
                im3_plants = im3_plants[im3_plants.sited_year == year]
            im3_plants = im3_plants.apply(
                crs_transform,
                axis=1
            )[[
                'region_name', 'unit_size_mw', 'tech_name', 'sited_year', 'retirement_year', 'lat', 'lon'
            ]]
            im3_plants['tech_name'] = im3_plants.tech_name.map(tech_mapping)
            im3_plants = gpd.GeoDataFrame(
                im3_plants,
                geometry=gpd.points_from_xy(im3_plants.lon, im3_plants.lat), crs="EPSG:4326"
            )
            im3_geo = pd.concat([im3_geo, im3_plants], ignore_index=True)

        # if historic scenario
        # create geodataframe from GPPD data
        if scenarios[i] == 'historical':
            gppd_geo = gppd_plants[['country', 'capacity_mw', 'latitude', 'longitude', 'primary_fuel']]
            gppd_geo = gpd.GeoDataFrame(
                gppd_geo,
                geometry=gpd.points_from_xy(gppd_geo.longitude, gppd_geo.latitude), crs="EPSG:4326"
            )
            # exclude the CONUS plants (keeping Alaska and Hawaii)
            min_lat = im3_plants.lat.min()
            max_lat = im3_plants.lat.max()
            min_lon = im3_plants.lon.min()
            max_lon = im3_plants.lon.max()
            gppd_geo = gppd_geo[
                (gppd_geo.country != 'USA') |
                (((gppd_geo.latitude <= min_lat) |
                (gppd_geo.latitude >= max_lat)) |
                ((gppd_geo.longitude <= min_lon) |
                (gppd_geo.longitude >= max_lon)))
            ]

        # confirm all techs have been mapped
        if len(im3_geo[im3_geo.tech_name.isna()]) > 0:
            raise Exception(f'''
            
            Missing technology mapping:
            
            {im3_geo[im3_geo.tech_name.isna()]}
            
            ''')

        for year in np.arange(2020, 2060, 5):

            # select plants active in this year
            im3_plants_this_year = im3_geo[
                (im3_geo.sited_year <= year) &
                (im3_geo.retirement_year > year)
            ]

            # if historical scenario
            # combine the IM3 CONUS plants with the rest of the world GPPD plants
            if scenarios[i] == 'historical':
                combined_plants = pd.concat([
                    im3_plants_this_year,
                    gppd_geo.rename(columns={
                        'country': 'region_name',
                        'capacity_mw': 'unit_size_mw',
                        'latitude': 'lat',
                        'longitude': 'lon',
                        'primary_fuel': 'tech_name',
                    }),
                ], ignore_index=True)
            else:
                combined_plants = im3_plants_this_year

            # spatial join plants to the tethys grid
            # aggregate plant capacity by tech to tethys grid cells
            # pivot table on tech_name and create an xarray dataset in the form expected by Tethys
            aggregated_plants = combined_plants.sjoin_nearest(
                tethys_points.rename(columns={'lat': 'tethys_lat', 'lon': 'tethys_lon'}),
                how='left',
                max_distance=1,
            ).groupby([
                'tech_name', 'tethys_lat', 'tethys_lon'
            ]).unit_size_mw.sum().reset_index().rename(columns={
                'tethys_lat': 'lat',
                'tethys_lon': 'lon',
            })
            aggregated_plants = xr.Dataset.from_dataframe(
                aggregated_plants.merge(
                    tethys_points,
                    on=['lat', 'lon'],
                    how='right'
                ).pivot(index=['lat', 'lon'], columns='tech_name', values='unit_size_mw').drop(columns=[np.nan])
            ).rio.set_crs(to_crs).expand_dims(year=[year])

            for v in list(aggregated_plants.data_vars):
                aggregated_plants[v].attrs['units'] = 'aggregated MW capacity'

            # write to file
            aggregated_plants.to_netcdf(f'../../data/powerplants/{scenarios[i]}_{year}_gppd_im3_tethys_plants.nc')

if __name__ == "__main__":
    cerf_to_tethys()
