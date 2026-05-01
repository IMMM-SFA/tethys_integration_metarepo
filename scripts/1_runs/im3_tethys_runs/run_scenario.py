import yaml
import tethys
import sys
import numpy as np
from pathlib import Path

scenarios = [
    'rcp45cooler_ssp3', 'rcp45cooler_ssp5',
    'rcp45hotter_ssp3', 'rcp45hotter_ssp5',
    'rcp85cooler_ssp3', 'rcp85cooler_ssp5',
    'rcp85hotter_ssp3', 'rcp85hotter_ssp5',
]

def run_scenario(scenario):

    five_yearly = np.arange(2020, 2060, 5).tolist()
    ten_yearly  = np.arange(2020, 2070, 10).tolist()
    

    scenario_path = f'../../../output/{scenario}'
    Path(scenario_path).mkdir(parents=True, exist_ok=True)

    for demand_type in ['withdrawals', 'consumption']:
        
        scenario_config = {
            'years': five_yearly,
            'resolution': 0.125,
            'bounds': [25.0625, 52.9375, -124.9375, -67.0625],  # [lat_min, lat_max, lon_min, lon_max] # CONUS
            'demand_type': demand_type,
            'output_dir': f'{scenario_path}/',
            'gcam_db':  f'../../../data/gcam/database_{scenario}',
            'source_disaggregation': demand_type=='withdrawals',
            'map_files': [
                '../../../data/maps/states.tif',
                '../../../data/maps/statebasins.tif',
                '../../../data/maps/USA.tif',
                '../../../data/maps/USAbasins.tif',
            ],
            'proxy_files': {
                f'../../0_preprocessing/population_to_tethys/{scenario[-4:]}_{{year}}.tif': {
                    'variables': 'Population',
                    'years': ten_yearly,
                },
                f'../../../data/demeter/demeter_78_PFT_output/output_wo_harvforest_demeter_CONUS_harmonized_im3_demeter_{scenario}_{{year}}.nc': {
                    'variables': [
                        'c3_crop_irr', 'Corn_irr', 'Wheat_irr', 'Wheat_winter_irr', 'Soy_irr', 'Barley_irr',
                        'Barley_winter_irr', 'Rye_irr', 'Rye_winter_irr', 'Cassava_irr', 'Citrus_irr',
                        'Cocoa_irr', 'Coffee_irr', 'Cotton_irr', 'DatePalm_irr',
                        'Grapes_irr', 'GroundNuts_irr', 'Millet_irr', 'OilPalm_irr', 'Potatoes_irr',
                        'Pulses_irr', 'RapeSeed_irr', 'Rice_irr', 'Sorghum_irr', 'Sugarbeet_irr',
                        'Sugarcane_irr', 'sunflower_irr', 'miscanthus_irr', 'switchgrass_irr',
                        'CornTropical_irr', 'SoyTropical_irr',
                    ],
                    'years': five_yearly,
                    'flags': ['cell_area_share', 'long_name_as_name'],
                },
                '../../../data/livestock/5_{variable}_{year}_Da.tif': {
                    'variables': {
                        'Buffalo': 'Bf',
                        'Cattle': 'Ct',
                        'Sheep': 'Sh',
                        'Goat': 'Gt',
                        'Chicken': 'Ch',
                        'Duck': 'Dk',
                        'Pig': 'Pg',
                    },
                    'years': 2010,
                },
                f'../../../data/powerplants/{scenario}_{{year}}_gppd_im3_tethys_plants.nc': {
                    'variables': [
                        'Biomass', 'Coal', 'Gas', 'Geothermal', 'Nuclear',
                        'Oil', 'Solar', 'NormalizedAggregate',
                    ],
                    'years': five_yearly,
                },
            },
            'downscaling_rules': {
                'Domestic':        'Population',
                'Electricity': {
                    'electricity/biomass':         ['Biomass', 'NormalizedAggregate'],
                    'electricity/coal':            ['Coal', 'NormalizedAggregate'],
                    'electricity/gas':             ['Gas', 'NormalizedAggregate'],
                    'electricity/geothermal':      ['Geothermal', 'NormalizedAggregate'],
                    'electricity/nuclear':         ['Nuclear', 'NormalizedAggregate'],
                    'electricity/refined liquids': ['Oil', 'NormalizedAggregate'],
                    'electricity/solar':           ['Solar', 'NormalizedAggregate'],
                    # excluding electrcity/hydro, which is not cooling water
                },
                'Irrigation': {
                    'Corn':        ['Corn_irr', 'CornTropical_irr'],
                    'Wheat':       ['Wheat_irr', 'Wheat_winter_irr'],
                    'Rice':         'Rice_irr',
                    'RootTuber':   ['Cassava_irr', 'Potatoes_irr'],
                    'OilCrop':     ['Soy_irr', 'GroundNuts_irr', 'RapeSeed_irr', 'sunflower_irr', 'SoyTropical_irr'],
                    'SugarCrop':   ['Sugarbeet_irr', 'Sugarcane_irr'],
                    'OtherGrain':  ['Barley_irr', 'Barley_winter_irr', 'Rye_irr', 'Rye_winter_irr', 'Millet_irr', 'Sorghum_irr'],
                    'FiberCrop':    'Cotton_irr',
                    'FodderHerb':   'c3_crop_irr',
                    'biomass':     ['miscanthus_irr', 'switchgrass_irr'],
                    'MiscCrop':    ['Citrus_irr', 'Cocoa_irr', 'Coffee_irr', 'DatePalm_irr', 'Grapes_irr', 'Pulses_irr'],
                    'PalmFruit':    'OilPalm_irr',
                },
                'Livestock': {
                    'Beef':        ['Buffalo', 'Cattle'],
                    'Dairy':       ['Buffalo', 'Cattle'],
                    'Pork':         'Pig',
                    'Poultry':     ['Chicken', 'Duck'],
                    'SheepGoat':   ['Sheep', 'Goat'],
                },
                'Manufacturing':  'Population',
                'Mining':         'Population',
            },
            'supersector_iterations': 0,
            'irrigation_conveyance_efficiency': 0.829937, # factor between GCAM USA level and state level irrigation withdrawal due to conveyance losses
            'temporal_config': {
                'Domestic': {
                    'method': 'domestic',
                    'kwargs': {
                        'tasfile': f'../../../data/monthly/Tavg_HDD_CDD/Tavg_HDD_CDD_{scenario[:-5]}_*.nc',
                        'tasvar': 'Tavg',
                        'rfile': '../../../data/monthly/DomesticR.nc',
                    },
                },
                'Electricity': {
                    'method': 'electricity',
                    'kwargs': {
                        'hddfile': f'../../../data/monthly/Tavg_HDD_CDD/Tavg_HDD_CDD_{scenario[:-5]}_*.nc',
                        'cddfile': f'../../../data/monthly/Tavg_HDD_CDD/Tavg_HDD_CDD_{scenario[:-5]}_*.nc',
                        'hddvar': 'HDD',
                        'cddvar': 'CDD',
                        'gcam_db': f'../../../data/gcam/database_{scenario}',
                        'regionfile': '../../../data/maps/states.tif',
                    },
                },
                'Irrigation': {
                    'method': 'weights',
                    'kwargs': {
                        'weightfile': f'../../../data/monthly/deficit/updated_irrigation_weight_{scenario[:-5]}.nc',
                        'prenormalized': True,
                    },
                },
            },
        }
    
        with open(f'{scenario_path}/config_{demand_type}.yaml', 'w+') as ff:
            yaml.dump(scenario_config, ff)
    
        model = tethys.Tethys(config_file=f'{scenario_path}/config_{demand_type}.yaml')
        model.run_model()


if __name__ == "__main__":

    if len(sys.argv) != 2:
        scenario = None
    else:
        scenario = sys.argv[1]

    print('')
    
    if scenario in scenarios:
        print(f'Running Tethys scenario {scenario}...')
        run_scenario(scenario)
        print('Done.')
        print('')

    elif scenario is None:
        for scenario in scenarios:
            print(f'Running Tethys scenario {scenario}...')
            run_scenario(scenario)
            print('Done.')
            print('')
    
    else:
        raise Exception(f'Please provide a single argument: a scenario from one of {", ".join(scenarios)}.')
