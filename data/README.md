# Tethys input data

This directory holds the input files that the Tethys runs in this metarepo consume. The full dataset is published on **MSD-Live** as the *IM3 Tethys CONUS input dataset* (DOI / link TBD); fetch it once and unpack into this directory.

The `data/` tree itself is gitignored — only this README is tracked. The producer/consumer artifact `usgs-runoff-share-2009-2020.nc` lives next to its scripts at `scripts/2_postprocess/adjust_runoff_shares/`, not here.

## Layout

```
data/
├── README.md                  # this file
├── maps/                      # CONUS region masks (1/8°)
├── livestock/                 # Huang et al. 2018 GLW3 livestock density
└── historical/                # historical-scenario inputs (climate, GCAM DB, LULC, plants, population)
    ├── Tavg_HDD_CDD_Historical_*.nc
    ├── output_wo_harvforest_demeter_CONUS_harmonized_im3_demeter_*.nc
    ├── 5_*_2010_Da.tif        # livestock duplicates of livestock/
    ├── ssp3_{2010,2020}.tif
    ├── DomesticR.nc
    ├── irrigation_weight_rcp45cooler.nc
    ├── historical_gppd_im3_tethys_plants.nc
    └── database_rcp45cooler_ssp3/   # GCAM-USA BaseX database
```

## File inventory

| File / pattern | Source | Provenance |
|---|---|---|
| `maps/USA.tif`, `USAbasins.tif`, `states.tif`, `statebasins.tif` | CONUS region masks at 1/8° used by Tethys (`map_files` in `test_config.yml`) | External reference rasters |
| `livestock/5_*_2010_Da.tif` (Bf, Ch, Ct, Dk, Gt, Pg, Sh) | GLW 3 (Gridded Livestock of the World v3) | Harvard Dataverse `dataverse/glw_3` — Gilbert et al., *Sci. Data* 2018, https://doi.org/10.1038/sdata.2018.227 |
| `historical/5_*_2010_Da.tif` | duplicate of `livestock/` to satisfy the per-scenario directory layout Tethys expects | as above |
| `historical/Tavg_HDD_CDD_Historical_*.nc` | Mean temperature + heating/cooling degree days, decadal NetCDFs 1980–2019 | Produced from TGW-WRF forcing by `scripts/0_preprocessing/gsi_nersc/Tavg_HDD_CDD.py` (Eldardiry, NERSC) |
| `historical/output_wo_harvforest_demeter_*.nc` | Per-year (2005–2020) Demeter LULC, irrigated-area shares per crop | IMMM-SFA Demeter; harmonized IM3 run, scenario `rcp45cooler_ssp3` |
| `historical/ssp3_{2010,2020}.tif` | SSP-consistent gridded population at 1/8° | Built by `scripts/0_preprocessing/population_to_tethys/` from Zoraghein & O'Neill 2020 (Zenodo 3756179) + Jones & O'Neill 2020 (NASA SEDAC) |
| `historical/DomesticR.nc` | Per-cell domestic-water *R* parameter (heat sensitivity) | Tethys input — see `tethys-code/tethys/tdmethods/domestic.py` |
| `historical/irrigation_weight_rcp45cooler.nc` | Monthly irrigation weight (`pirrww`) for the historical period | Pipeline-produced — `scripts/0_preprocessing/compute_monthly_weights.py`; not part of the published dataset, regenerate locally |
| `historical/historical_gppd_im3_tethys_plants.nc` | Per-technology power-plant capacity at 1/8° | Built by `scripts/0_preprocessing/im3_power_plants_to_tethys.ipynb` from GPPD v1.3 + IM3 CONUS plant inventory |
| `historical/database_rcp45cooler_ssp3/*.basex` | GCAM-USA BaseX database (queried by Tethys for sectoral demand) | Upstream GCAM-USA IM3 run (`20240606_to_be_validated`) |
| `historical/USA*.tif`, `states.tif`, `statebasins.tif` | duplicates of `maps/` for the per-scenario layout | as above |

Files marked **pipeline-produced** (`irrigation_weight_*.nc` and the `Tavg_HDD_CDD_*.nc` decade files) are *not* published on MSD-Live — regenerate them with the stage-0 scripts. Everything else in the table is fetched from MSD-Live.

## Fetching

Once the MSD-Live record is live:

```bash
# from the repo root
msdlive-cli download <dataset-id> -o data/
```

Or download the archive manually and unpack so the layout matches the tree above.

## Adding new files

If you add a new input here, append a row to the inventory table with: source / generating script, scenario(s) it applies to, and whether it should be published on MSD-Live or treated as pipeline-produced.
