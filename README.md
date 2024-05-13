# tethys_integration_metarepo
Meta-repository for data and code associated with all Tethys integration components for IM3


## Input data

##### Population

TODO

##### Power Plants

Tethys ingests global power plant data for reason [TODO... cooling water withdrawal?]. The format is a NetCDF with plant capacities in MegaWatts (MW) aggregated (summed) onto an 1/8 degree grid by generic technology/fuel type.

For IM3, the [Global Power Plant Database](https://datasets.wri.org/dataset/globalpowerplantdatabase) is used as the starting point [TODO which version?]. Grid cells in the lower 48 states and the Distric of Columbia are then updated with using the capacities from the IM3 power plant inventory provided by the Experiment B team. 

For the historical scenario (2015 plant inventory), this file can be found on PIC at `/rcfs/projects/im3/exp_b/exp_b_multi_model_coupling_west/models/cerf/data/power_plant_data/power_plant_locations_csv/power_plant_locations.csv`

Other scenarios are still TODO.

The notebook [im3_power_plants_to_tethys.ipynb](./im3_power_plants_to_tethys.ipynb) walks through this process for the historical scenario.

##### TODO

other inputs TODO

