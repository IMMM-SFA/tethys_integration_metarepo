# Tethys validation pipeline

Numbered pipeline that compares Tethys output against USGS water-use observations and produces the validation and projection figures for the Tethys data paper.

## Layout

| Stage | File | Lang | Purpose |
|---|---|---|---|
| 1a | `1a-postprocess-tethys.py` | Python | Spatially weight the Tethys 1/8° grid to HUC polygons (uses `xagg`). |
| 1b | `1b-process-previous-tethys.R` | R | Process the prior-version Tethys output for back-comparison. |
| 1c | `1c-spatial-weight-huc-tethys-grid-gwfrac.py` | Python | Spatial weighting that preserves the GW/SW fraction. |
| 2a | `2a-process-usgs-data.R` | R | Aggregate the USGS county-level water-use data to HUCs. |
| 3 | `3-combine-usgs-tethys.R` | R | Join Tethys and USGS at the HUC scale. |
| 4a | `4a-compare-tethys-usgs.R` | R | HUC2/4/6/8 comparison figures. |
| 4b | `4b-compare-tethys-usgs-huc12.R` | R | HUC12 comparison figures. |
| 5a | `5a-paper-figures.R` | R | Publication figures (Tethys vs USGS, dominant sector, projections). |
| 5d | `5d-dominant-sector-map.py` | Python | Dominant-sector map (matplotlib version) for the paper. |
| 6 | `6-compute-table2-metrics.py` | Python | Per-sector metrics for paper Table 2. |

The USGS groundwater / surface-water split now lives next to its consumer at `../scripts/2_postprocess/adjust_runoff_shares/2b-process-usgs-gwsw-split.R` and is no longer part of this pipeline.

Earlier stages kept for reference (now under `old/`):
- `old/5b-demand-sector-by-grid-cell.py` -- per-cell sector demand panels.
- `old/5c-scenarios-timeseries.R` -- annual CONUS timeseries by scenario.

## Configuration

Every input path used by the active stages is centralised in **`paths.yml`** — a flat key→path map. Scripts read it directly with `yaml.safe_load` (Python) or `yaml::read_yaml` (R) and index by key, e.g. `P["huc6_shapefile"]` / `P$huc6_shapefile`. To retarget a path on a new machine you edit `paths.yml`, not seven scripts.

Keys in `paths.yml`:
- `tethys_output_canonical`, `tethys_output_raw` — Tethys output roots. `canonical` is `/Volumes/data/tethys/output_adjusted_usgs_method2`; `raw` is `/Volumes/data/tethys/output`.
- `tethys_validation_csv_pattern` — per-HUC Tethys CSV pattern used by 4b. Format with `{sector}`, `{demand_type}`, `{huc_level}`.
- `usgs_public_supply_cu`, `usgs_public_supply_wd`, `usgs_irrigation_cu`, `usgs_irrigation_wd`, `usgs_thermoelectric` — 2009–2020 USGS monthly water-use CSVs consumed by 2a.
- `huc{2,4,6,8,12}_shapefile` — per-level shapefile mapping. `huc6_shapefile` points at `../data/shapefiles/HUC6/HUC6.shp` (bundled with the metarepo); the others are still on `/Volumes/data/shapefiles/`. Override any level without touching scripts.
- `data_dir`, `figures_dir`, `paper_figures_dir` — per-script CSV cache and figure output dirs.

Relative values should be interpreted relative to `validation/` (the script's CWD when run via the pixi tasks). The scripts run from there, so `../data/...` and `data` resolve correctly without extra logic.

Stage 5a / 5d additionally need the `tethys_output_canonical` root mounted; stage 1a / 1c read from `tethys_output_raw`. Other stages only need `data/` and the shapefile mapping.

## Outputs

Figures land in `figures/` by default. Stage 5a additionally writes into the paper figures directory at `../paper/figures/` -- controlled via either:

```bash
pixi run paper-figures -- --paper      # CLI flag (also the default)
pixi run paper-figures -- --no-paper   # local only
WRITE_PAPER=false pixi run paper-figures
```

`WRITE_PAPER` defaults to `TRUE`, so paper writes are on unless explicitly disabled. Stage 5d writes its PNG and CSV directly to `../../tethys-data-paper/` (no toggle). `figures/` is gitignored.

## Environment

`pixi.toml` pins R 4.4+ and the Python deps (`xarray`, `geopandas`, `xagg`, `rioxarray`, `matplotlib`, `netcdf4`) plus the R deps (`tidyverse`, `sf`, `ncdf4`, `scico`, `ggthemes`). One env covers every stage.

```bash
cd validation
pixi install
```

R is invoked through `Rscript`; Python through `python`. Both are on `PATH` inside the pixi shell.

## Running

Each stage is a pixi task. Run them in order:

```bash
pixi run postprocess-tethys        # 1a
pixi run process-usgs              # 2a
pixi run combine-usgs-tethys       # 3
pixi run compare-huc               # 4a
pixi run compare-huc12             # 4b
pixi run paper-figures             # 5a (writes to figures/ and ../paper/figures/)
pixi run dominant-sector-map       # 5d (writes paper PNG + CSV)
```

Or invoke a single script directly:

```bash
pixi run Rscript 5a-paper-figures.R --no-paper
pixi run python 1a-postprocess-tethys.py
pixi run python 6-compute-table2-metrics.py
```


## Conventions

- HUC scales: 2 / 4 / 6 / 8 / 12. Stage-5 figures default to HUC6.
- Units: Tethys/GCAM in km³/year, USGS in MGD. `km3_per_year_TO_mgd = 264172.05124 / 365`.
- Sectors: Domestic, Electricity, Irrigation, Livestock, Manufacturing, Mining.
- Scenarios: `historical`, `rcp{45,85}{cooler,hotter}_ssp{3,5}`.
- Historical Tethys output runs 1975–2020; futures run 2020–2100. Scenario timeseries plots join them at year 2020 so the lines read continuously.
- Dominant-sector palette: Okabe-Ito (Wong 2011), shared between `5a-paper-figures.R` and `5d-dominant-sector-map.py`.

## R formatting

Local override at `air.toml` (line-width 120, indent 2). Format with `air format .` from this directory.
