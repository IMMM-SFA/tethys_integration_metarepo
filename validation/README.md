# Tethys validation pipeline

Numbered pipeline that compares Tethys output against USGS water-use observations and produces the validation and projection figures for the Tethys data paper.

## Layout

| Stage | File | Lang | Purpose |
|---|---|---|---|
| 1 | `1-postprocess-tethys.py` | Python | Spatially weight the Tethys 1/8° grid to HUC polygons (uses `xagg`). |
| 1b | `1b-process-previous-tethys.R` | R | Process the prior-version Tethys output for back-comparison. |
| 1c | `1c-spatial-weight-huc-tethys-grid-gwfrac.py` | Python | Spatial weighting that preserves the GW/SW fraction. |
| 2a | `2a-process-usgs-data.R` | R | Aggregate the USGS county-level water-use data to HUCs. |
| 2b | `2b-process-usgs-gwsw-split.R` | R | USGS groundwater / surface-water split. |
| 3 | `3-combine-usgs-tethys.R` | R | Join Tethys and USGS at the HUC scale. |
| 4a | `4a-compare-tethys-usgs.R` | R | HUC2/4/6/8 comparison figures. |
| 4b | `4b-compare-tethys-usgs-huc12.R` | R | HUC12 comparison figures. |
| 5 | `5-paper-figures.R` | R | Publication figures (Tethys vs USGS, dominant sector, projections). |
| 5b | `5b-demand-sector-by-grid-cell.py` | Python | Per-cell sector demand panels. |
| 5c | `5c-scenarios-timeseries.R` | R | Annual CONUS timeseries by scenario, historical → 2100. |
| 5d | `5d-dominant-sector-map.py` | Python | Dominant-sector map (matplotlib version). |
| — | `compute-table2-metrics.py` | Python | Numbers for paper Table 2. |

Inputs land in `data/` (USGS / Tethys joined at HUC) and shapefiles at `/Volumes/data/shapefiles/HUC{2,4,6,8,12}/`. Stage 5 also reads NetCDF directly from `/Volumes/data/tethys/output_adjusted_usgs_method2/`.

## Outputs

Figures land in `figures/` by default. Stages 5 and 5c also support writing into the paper directory at `~/Dropbox/Apps/Overleaf/TETHYS data paper/` — opt in via either:

```bash
pixi run paper-figures -- --paper             # CLI flag
WRITE_PAPER=true pixi run paper-figures        # env var
pixi run paper-figures                         # default: local only
```

`figures/` is gitignored.

## Environment

`pixi.toml` pins R 4.4+ and the Python deps (`xarray`, `geopandas`, `xagg`, `rioxarray`, `matplotlib`, `netcdf4`) plus the R deps (`tidyverse`, `sf`, `ncdf4`, `scico`, `ggthemes`). One env covers every stage.

```bash
cd validation
pixi install
```

R is invoked directly through `Rscript`; Python through `python`. Both are on `PATH` inside the pixi shell.

## Running

Each stage is a pixi task. Run them in order:

```bash
pixi run postprocess-tethys        # 1
pixi run process-usgs              # 2a
pixi run process-usgs-gwsw         # 2b
pixi run combine-usgs-tethys       # 3
pixi run compare-huc               # 4a
pixi run compare-huc12             # 4b
pixi run paper-figures             # 5  (writes to figures/)
pixi run scenarios-timeseries      # 5c (writes to figures/)
pixi run dominant-sector-map       # 5d (writes paper PNG + CSV)
```

Or invoke a single script directly:

```bash
pixi run Rscript 5-paper-figures.R --paper
pixi run python 1-postprocess-tethys.py
```

Stages 1–4 only need `data/` and the shapefile volume. Stages 5 / 5c / 5d additionally need `/Volumes/data/tethys/output_adjusted_usgs_method2/` mounted.

## Conventions

- HUC scales: 2 / 4 / 6 / 8 / 12. Stage-5 figures default to HUC6.
- Units: Tethys/GCAM in km³/year, USGS in MGD. `km3_per_year_TO_mgd = 264172.05124 / 365`.
- Sectors: Domestic, Electricity, Irrigation, Livestock, Manufacturing, Mining.
- Scenarios: `historical`, `rcp{45,85}{cooler,hotter}_ssp{3,5}`.
- Historical Tethys output runs 1975–2020; futures run 2020–2100. The 5c script joins them at year 2020 so the lines read continuously.
- Dominant-sector palette: Okabe-Ito (Wong 2011), shared between `5-paper-figures.R` and `5d-dominant-sector-map.py`.

## R formatting

Local override at `air.toml` (line-width 120, indent 2). Format with `air format .` from this directory.
