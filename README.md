# tethys_integration_metarepo
Meta-repository for data and code associated with all Tethys integration components for IM3


## Input data

#### Heating/Cooling Degree Days

TODO

#### Land Use

TODO

#### Population

TODO

#### Power Plants

Tethys ingests global power plant data for reason [TODO... cooling water withdrawal?]. The format is a NetCDF with plant capacities in MegaWatts (MW) aggregated (summed) onto a global 1/8 degree grid by generic technology/fuel type.

For IM3, the [Global Power Plant Database v1.3](https://datasets.wri.org/dataset/globalpowerplantdatabase) is used as the starting point. Grid cells in the lower 48 states and the Distric of Columbia are then updated using the capacities from the IM3 power plant inventory provided by the Experiment B team.

The notebook [im3_power_plants_to_tethys.ipynb](./im3_power_plants_to_tethys.ipynb) walks through the process of combining this data for the historical scenario. Other scenarios are still TODO

| scenario      | global plants | CONUS plants | Output |
|:-------------:|:-------------:|:------------:|:------:|
| historical    | [GPPD v1.3](https://datasets.wri.org/dataset/globalpowerplantdatabase) | IM3 initial powerplants (rcfs/projects/im3/exp_b/exp_b_multi_model_coupling_west/models/cerf/data/power_plant_data/power_plant_locations_csv/power_plant_locations.csv) | ./data/historical_gppd_im3_tethys_plants.nc |

#### Other Inputs?

TODO

## Running Tethys

TODO

## Output Data

TODO

