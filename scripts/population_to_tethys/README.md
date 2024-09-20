## Imprint US population onto the global grid

### Data sources
#### US gridded population data
> Zoraghein, H., & O'Neill, B. (2020). Data Supplement: U.S. state-level projections of the spatial distribution of population consistent with Shared Socioeconomic Pathways. (v0.1.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.3756179

#### Global gridded population data from Tethys
> Jones, B., and B. C. O'Neill. 2020. Global One-Eighth Degree Population Base Year and Projection Grids Based on the Shared Socioeconomic Pathways, Revision 01. Palisades, NY: NASA Socioeconomic Data and Applications Center (SEDAC). https://doi.org/10.7927/m30p-j498.

But accessed from:  `/rcfs/projects/im3/dardiry/Water_Demand/tethys-im3-scenarios/data/population`

### Setting up your environment
Python version used: 3.11.7
Requirements:
 - numpy==1.26.4
 - rasterio==1.3.9
 - geopandas==0.14.3

### Run the code

```bash
python population_to_tethys.py \
     --global_dir <original Tethys population data directory> \
     --local_dir <root directory holding the gridded population data> \
     --mosaic_dir <directory to save mosaic outputs to> \
     --output_dir <directory to write the modified new outputs to> \
     --percent_area_file percent_grid.zip \
     --ssp_list SSP3 SSP5 \
     --year_list 2020 2030 2040 2050 2060 2070 2080 2090 2100
```
