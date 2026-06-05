# IM3 Tethys CONUS multi-sector water-demand dataset

A gridded (1/8°), monthly, multi-sector water-demand dataset for the contiguous United States covering 1980–2100, downscaled with [Tethys](https://github.com/JGCRI/tethys) from a GCAM-USA scenario ensemble. The dataset is the input forcing for downstream river-routing and water-management runs with [mosartwmpy](https://github.com/IMMM-SFA/mosartwmpy), and is described in the accompanying data descriptor (Bracken et al., in prep).

Code, configuration, and validation scripts that produce these files live in the [`tethys_integration_metarepo`](https://github.com/IMMM-SFA/tethys_integration_metarepo) repository. See `CITATION.cff` for citation metadata.

## Contributors

| Author | ORCID | Affiliation | Role (CRediT + project) |
|---|---|---|---|
| Cameron Bracken (corresponding) | [0000-0003-1917-402X](https://orcid.org/0000-0003-1917-402X) | Pacific Northwest National Laboratory, Richland, WA, USA | Project administration, Validation, Visualization, Writing – original draft. Coordinated the downscaling runs, conducted the HUC-scale validation, drafted the current manuscript. |
| Hassan Niazi (corresponding) | [0000-0001-6556-2854](https://orcid.org/0000-0001-6556-2854) | Joint Global Change Research Institute, Pacific Northwest National Laboratory, College Park, MD, USA | Software, Methodology, Investigation. Developed and maintained the Tethys model, conducted runs, helped interpret GCAM-USA and Tethys outputs. |
| Travis Thurber | [0000-0002-4370-9971](https://orcid.org/0000-0002-4370-9971) | Pacific Northwest National Laboratory, Richland, WA, USA | Software, Investigation. Extended Tethys to consume GCAM-USA inputs, built the first version of the Tethys metarepo, carried out the initial scenario runs. |
| Isaac Thompson | [0000-0001-9594-0043](https://orcid.org/0000-0001-9594-0043) | Joint Global Change Research Institute, Pacific Northwest National Laboratory, College Park, MD, USA | Writing – original draft, Methodology, Software. Wrote the initial draft of the manuscript and contributed to the CERF–Tethys integration and power-plant proxy construction. |
| Kazi Tamaddun | [0000-0001-6704-3767](https://orcid.org/0000-0001-6704-3767) | Pacific Northwest National Laboratory, Richland, WA, USA | Methodology, Investigation. Developed the USGS-anchored source-share attribution applied as a Tethys postprocess and conducted runs. |
| Hisham Eldardiry | [0000-0002-2932-7459](https://orcid.org/0000-0002-2932-7459) | University of Washington, Seattle, WA, USA | Methodology, Data curation. Produced the TGW-WRF preprocessing pipeline for PET, HDD/CDD, and GSI. |
| Kendall Mongird | [0000-0003-2807-7088](https://orcid.org/0000-0003-2807-7088) | Pacific Northwest National Laboratory, Richland, WA, USA | Methodology, Software. Developed the CERF–Tethys integration and power-plant proxy construction. |
| Nathalie Voisin | [0000-0002-6848-449X](https://orcid.org/0000-0002-6848-449X) | Pacific Northwest National Laboratory, Richland, WA, USA; University of Washington, Seattle, WA, USA | Conceptualization, Supervision, Writing – review & editing. Contributed to scenario design and interpretation. |
| Ning Sun | [0000-0002-4094-4482](https://orcid.org/0000-0002-4094-4482) | Pacific Northwest National Laboratory, Richland, WA, USA | Project administration, Conceptualization. Project management, scenario design, and interpretation. |
| Jennie Rice | [0000-0002-7833-9456](https://orcid.org/0000-0002-7833-9456) | Pacific Northwest National Laboratory, Richland, WA, USA | Supervision, Funding acquisition, Writing – review & editing. Provided overall project guidance and scientific review. |

## Directory layout

```
tethys-dataset-msdlive/
├── README.md
├── CITATION.cff
├── historical/                       # 1975–2020, observed/reanalysis-driven baseline
├── rcp45cooler_ssp3/                 # 2020–2100, future scenario
├── rcp45cooler_ssp5/
├── rcp45hotter_ssp3/
├── rcp45hotter_ssp5/
├── rcp85cooler_ssp3/
├── rcp85cooler_ssp5/
├── rcp85hotter_ssp3/
└── rcp85hotter_ssp5/
```

The eight `rcp{45,85}{cooler,hotter}_ssp{3,5}` directories are the future scenario combinations of (radiative forcing × climate-model warming bin × shared socioeconomic pathway). All scenario directories share the same file structure described below.

## Scenarios

| Directory | RCP | Warming bin | SSP | Years |
|---|---|---|---|---|
| `historical` | – | – | – | 1975–2020 |
| `rcp45cooler_ssp3` | 4.5 | cooler | 3 | 2020–2100 |
| `rcp45cooler_ssp5` | 4.5 | cooler | 5 | 2020–2100 |
| `rcp45hotter_ssp3` | 4.5 | hotter | 3 | 2020–2100 |
| `rcp45hotter_ssp5` | 4.5 | hotter | 5 | 2020–2100 |
| `rcp85cooler_ssp3` | 8.5 | cooler | 3 | 2020–2100 |
| `rcp85cooler_ssp5` | 8.5 | cooler | 5 | 2020–2100 |
| `rcp85hotter_ssp3` | 8.5 | hotter | 3 | 2020–2100 |
| `rcp85hotter_ssp5` | 8.5 | hotter | 5 | 2020–2100 |

The `cooler`/`hotter` labels are the IM3 Thermodynamic Global Warming (TGW) climate bins. Annual outputs are reported on the GCAM 5-year time step; monthly outputs are reported every year.

## File contents per scenario directory

Each scenario directory contains these files:

### Per-sector demand files

For each sector in {Domestic, Electricity, Irrigation, Livestock, Manufacturing, Mining}, two demand types {withdrawals, consumption}, and two temporal resolutions {annual, monthly}:

| File pattern | Variable structure | Time axis |
|---|---|---|
| `{Sector}_withdrawals.nc` | one or more 3D variables with dims `(year, lat, lon)` | annual (5-year GCAM steps) |
| `{Sector}_consumption.nc` | same | annual |
| `{Sector}_withdrawals_monthly.nc` | one or more 4D variables with dims `(year, lat, lon, month)` | annual × month |
| `{Sector}_consumption_monthly.nc` | same | annual × month |

The set of *variables inside each file* depends on the sector:

| Sector | Variables in NetCDF | Notes |
|---|---|---|
| Domestic | `Domestic` | single field |
| Electricity | `electricity_biomass`, `electricity_coal`, `electricity_gas`, `electricity_geothermal`, `electricity_nuclear`, `electricity_refined liquids`, `electricity_solar` | per generation technology; sum to total electricity-sector water |
| Irrigation | `Corn`, `FiberCrop`, `FodderHerb`, `MiscCrop`, `OilCrop`, `OtherGrain`, `Rice`, `RootTuber`, `SugarCrop`, `Wheat`, `biomass` | per GCAM-USA crop class |
| Livestock | `Beef`, `Dairy`, `Pork`, `Poultry`, `SheepGoat` | per livestock class |
| Manufacturing | `Manufacturing` | single field |
| Mining | `Mining` | single field |

The historical scenario also carries Irrigation files with a `_with_losses` suffix (`Irrigation_withdrawals_with_losses.nc`, etc.). These mirror the same crop variables but include conveyance and on-farm losses; the unsuffixed files are net of losses. Future scenarios contain only the unsuffixed (net) variants.

### Source-share file

| File | Dimensions | Variable | Description |
|---|---|---|---|
| `gridded_runoff_shares.nc` | `(year, lat, lon)` | `share` | Per-cell renewable (surface-water + shallow groundwater) share of total water source, derived by adjusting GCAM-USA basin-level shares to USGS 2010–2020 observations. The non-renewable (deep groundwater / fossil) share is `1 - share`. Multiply the per-sector demand variables above by `share` to get the renewable component (the Electricity sector is constrained to renewable-only by construction). |

### Configuration files

| File | Description |
|---|---|
| `config_withdrawals.yaml` | Tethys configuration that produced the withdrawals NetCDFs in this directory. Records bounds, downscaling rules, proxy files, temporal-downscaling kwargs, and the GCAM-USA database used. |
| `config_consumption.yaml` | Same for the consumption NetCDFs. |

These configs are kept verbatim alongside the data so a run can be reproduced or a variable definition can be checked without consulting the metarepo.

### Diagnostic figure

| File | Description |
|---|---|
| `usgs_adjustment_diagnostic.png` | Per-HUC scatter and bias plots from the GCAM→USGS source-share adjustment step. Reference only; not a data product. |

## Coordinate system and grid

| Property | Value |
|---|---|
| Resolution | 0.125° (1/8°) |
| Lat range | 25.0625° to 52.9375° (south to north, but stored north-to-south in the files) |
| Lon range | -124.9375° to -67.0625° |
| Grid shape | `lat = 224`, `lon = 464` |
| CRS | EPSG:4326 (WGS 84). Each file carries a `spatial_ref` scalar variable for georeferencing. |

The geographic extent covers the contiguous United States. Cells outside CONUS land are NaN.

## Units

All demand variables (annual and monthly, withdrawals and consumption) are in **km³ per year** at the cell, the standard GCAM/Tethys unit. The monthly files are *not* converted to month-rate; each `(year, month)` slice is the per-year-equivalent demand for that calendar month, so summing the 12 months for a given year and dividing by 12 gives the annual mean of the monthly profile, while summing the 12 monthly slices and dividing by 12 reproduces the corresponding annual file (within rounding).

`gridded_runoff_shares.nc` `share` is dimensionless on `[0, 1]`.

## How to read

Python (xarray):

```python
import xarray as xr
ds = xr.open_dataset("historical/Irrigation_withdrawals.nc")
ds["Corn"].sel(year=2015).plot()           # 2015 corn-irrigation withdrawals (km³/yr) per cell
total_irr = ds.to_array().sum("variable")  # sum across crops
```

R (ncdf4 / terra):

```r
library(ncdf4)
nc = nc_open("historical/Domestic_withdrawals.nc")
dom = ncvar_get(nc, "Domestic")            # array [lon, lat, year]
years = ncvar_get(nc, "year")
nc_close(nc)
```

CLI:

```bash
ncdump -h historical/Domestic_withdrawals.nc
```

## Provenance

Each file was produced by the canonical Tethys postprocessing run `output_adjusted_usgs_method2` (March 2026). The exact Tethys configuration is stored alongside the NetCDFs as `config_withdrawals.yaml` / `config_consumption.yaml`. The full pipeline — climate-forcing preprocessing, GCAM-USA database, Tethys downscaling, USGS-anchored source-share adjustment, and validation against USGS 2010–2020 — is documented in the [`tethys_integration_metarepo`](https://github.com/IMMM-SFA/tethys_integration_metarepo) `README.md` and `data/README.md`.

## License

CC BY 4.0.

## Citing

See `CITATION.cff`. To cite the data descriptor and dataset together:

> Bracken, C., Niazi, H., Thurber, T., Thompson, I., Tamaddun, K., Eldardiry, H., Mongird, K., Voisin, N., Sun, N., Rice, J. (in prep). A multi-sector water-demand dataset for CONUS at 1/8° resolution, 1980–2100. *Scientific Data*. Dataset: MSD-Live.

## Acknowledgements

This research was supported by the U.S. Department of Energy, Office of Science, as part of research in the MultiSector Dynamics, Earth and Environmental System Modeling Program through the Integrated, Multisector, Multiscale Modeling (IM3) Scientific Focus Area.
