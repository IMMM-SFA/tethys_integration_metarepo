# tethys_integration_metarepo
Meta-repository for data and code associated with all Tethys integration components for IM3

## Tasks

 - [ ] Issue with regridding in Tethys https://github.com/JGCRI/tethys/issues/71. Assignee: Chris
 - [ ] Get Hassan running on Tethy (importlib issue). Assignee: Travis, Hassan
 - [ ] Decide how to disaggregate renewable vs fossil water, see below. Assignee: Hassan and all.
 - [ ] Pilot disaggregation code within Tethys. Assignee: Hassan.
 - [ ] Consider if there is a data driven strategy for renewable/fossil disaggregation. Low priority, but keep an eye out for data. Assignee Cameron.
 - [ ] Check with Kanishka about the historical LULC data layer. Assignee: Travis.
 - [ ] Run Tethys for the historical period with current tethys but updated GCAM. Assignee: Travis and Hassan.
 - [ ] Investigate the latest USGS water usage data and compare with historical Tethys output. Assignee: Cameron.
 - [x] Provide updated population data. What about historical population? Assignee: Chris. [PR #1](https://github.com/IMMM-SFA/tethys_integration_metarepo/pull/1)
 - [ ] Implement GO-CERF-GO temporal electricity sector downscaling. Assignee: Hassan.
 - [ ] Read the Isaac paper draft and decide how to move it forward. Assignee: Cameron.
 - [ ] Update Tethys in support of these decisions. Assignee: Hassan, Travis.
 - [ ] Connect with the USGS to see if there are other datasets we could leverage (within the IHTM network for instance). TBD once we are farther along.
 - [ ] ADD ALL CODE AND WORKFLOW TO THIS METAREPO. Assignee: all.

## Discussion Topics

What data/years to use for "historical" scenario? There is no official historical GCAM-USA run, and the 1975-2015 data within GCAM-USA outputs is not necessarily trustworthy.

How does Tethys handle missing years? I think it just linearly interpolates, is that okay? In particular for the historical run this is relevant since GCAM-USA only provides [1975, 1990, 2005, 2010, 2015, 2020], and 2020 is technically simulated under the future scenario settings.

GCAM-USA, Tethys, mosartwmpy, USGC potentially have different strategies of reporting water usage regarding the location of withdrawal vs the location of delivery/consumption. What problems does this cause and how do we deal with them?

Which population and land use should we use for the historical scenario?

What units does Tethys/GCAM-USA report in? I think it's km^3.

#### Renewable vs Fossil Water Disaggregation

GCAM-USA reports renewable vs fossil water usage at the basin level but does not disaggregate by sector.

Hassan proposes to apply the basin level shares to all cells within the basin,
excepting that electricity sector will only use renewable water.

However, we would still want to restrict fossil water usage to grid cells that could conceivably access it.
Ideas include using data from Superwell or Jim Yoon or other to obtain binary gridded fossil water availability maps.

Such strategies would then need to be implemented into Tethys.

In depth proposal document: https://pnnl-my.sharepoint.com/:w:/g/personal/hassan_niazi_pnnl_gov/EYcftCLewBpDgnc8mHZp2vcB5SE8A7jN4zT-R9-9PHEDzA?e=5JiX8E


## Input data

#### Maps

GCAM-USA reports some water use at basin level, some at state level, and some at country level.
These 1/12 degree resolution maps are used to translate the GCAM-USA regions onto grid cells.


#### Population

Population is used as a proxy to weight the spatial distribution of domestic water usage.

Chris is working on fitting the official IM3 populations (SSP3 and SSP5) from decadal to annual by state.

TODO is historical population part of this? If not what do we use?


#### Heating/Cooling Degree Days

HDD/CDD are used to temporally weight electricity sector water usage.

If we stick with this method, we should syncronize with the values used in Helios.

Hisham has independantly calculate HDD/CDD from the TGW data for all scenarios (scripts & files on Perlmutter),
by nearest neighbor with mosartwmpy grid, but may not have used the same method as the latest Helios.

NOTE that Jennie recommends using GO hourly generation profiles instead of HDD/CDD. This will require some effort.


#### Mean Temperature

Mean temperature is used to temporally weight domestic water usage. Hisham included this in the HDD/CDD files.


#### Power Plants

Tethys ingests global power plant data for reason [TODO... cooling water withdrawal?]. The format is a NetCDF with plant capacities in MegaWatts (MW) aggregated (summed) onto a global 1/8 degree grid by generic technology/fuel type.

For IM3, the [Global Power Plant Database v1.3](https://datasets.wri.org/dataset/globalpowerplantdatabase) is used as the starting point. Grid cells in the lower 48 states and the Distric of Columbia are then updated using the capacities from the IM3 power plant inventory provided by the Experiment B team.

The notebook [im3_power_plants_to_tethys.ipynb](./im3_power_plants_to_tethys.ipynb) walks through the process of combining this data for the historical scenario. Other scenarios are still TODO

| scenario      | global plants | CONUS plants | Output |
|:-------------:|:-------------:|:------------:|:------:|
| historical    | [GPPD v1.3](https://datasets.wri.org/dataset/globalpowerplantdatabase) | IM3 initial powerplants (/rcfs/projects/im3/exp_b/exp_b_multi_model_coupling_west/models/cerf/data/power_plant_data/power_plant_locations_csv/power_plant_locations.csv) | ./data/powerplants/historical_gppd_im3_tethys_plants.nc |

NOTE that since Tethys can now run within a bounding box, the global plants are probably not needed anymore.


#### Livestock

Livestock data from Huang et al 2018 is used to spatially distribute livestock water usage.

NOTE that livestock water usage is not currently temporally distributed.


#### Land Use / Land Cover

LULC data from Demeter is used to spatially distribute irrigation water usage.

GSI (Growing Season Index) weights are used to temporally distribute irrigation water usage.

Hisham calculated these. Scripts included.

TODO Which land use data should we use for the historical scenario?


## Running Tethys

See [run_tethys.ipynb](./run_tethys.ipynb). Work in progress.

