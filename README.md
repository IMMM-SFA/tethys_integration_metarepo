# tethys_integration_metarepo

Meta-repository for the code, inputs, and validation that produce the IM3 Experiment Group C multi-sector water-demand dataset for the contiguous United States (CONUS) at 1/8° resolution, monthly, 1980–2100. The dataset is the gridded output of [Tethys](https://github.com/JGCRI/tethys) downscaling driven by GCAM-USA scenarios, and it is consumed downstream by [mosartwmpy](https://github.com/IMMM-SFA/mosartwmpy) for river routing and water management.

This README is the canonical entry point and bundles four sections:

1. [Repository layout](#repository-layout)
2. [Pipeline](#pipeline) — end-to-end run instructions, stage 0 → 3 plus validation
3. [Reproducing the figures and tables of the data paper](#reproducing-the-figures-and-tables-of-the-data-paper)
4. [Tasks and open discussion](#tasks-and-open-discussion)

The `paper/` submodule (Overleaf manuscript) is updated separately. See `validation/README.md` for the pixi-driven validation pipeline; see `data/README.md` for input-data provenance and the MSD-Live dataset.

## Repository layout

```
tethys_integration_metarepo/
├── README.md                         # this file
├── requirements.txt                  # Python deps for Tethys runs
├── pixi.toml / pixi.lock             # MSD-Live publishing env
├── docs/
│   └── CLEANUP.md                    # 2026 reorganization rationale
├── data/
│   └── README.md                     # MSD-Live dataset inventory; rest gitignored
├── scripts/
│   ├── 0_preprocessing/              # climate forcing → proxies & weights
│   │   ├── gsi_nersc/                # Eldardiry's TGW-WRF → PET/GSI pipeline
│   │   ├── cerf_to_tethys/
│   │   ├── population_to_tethys/
│   │   ├── compute_gsi.{py,sh}
│   │   ├── compute_deficit.{py,sh}
│   │   ├── compute_monthly_weights.py
│   │   └── im3_power_plants_to_tethys.ipynb
│   ├── 1_runs/                       # Tethys scenario drivers
│   │   ├── run_tethys.ipynb
│   │   └── im3_tethys_runs/
│   ├── 2_postprocess/
│   │   └── adjust_runoff_shares/     # GCAM→USGS source-share adjustment
│   │       ├── adjust_runoff_shares_method2_kazi.py   # canonical
│   │       ├── adjust_runoff_shares_hist.py           # historical-only variant
│   │       ├── 2b-process-usgs-gwsw-split.R           # builds usgs-runoff-share-2009-2020.nc
│   │       ├── usgs-runoff-share-2009-2020.nc         # tracked, repo-owned input
│   │       └── notebooks/
│   └── 3_config/
│       ├── test_config.yml           # canonical Tethys config
│       ├── paths.yml                 # NERSC / PIC / RCFS / local base paths
│       └── reference_data/
├── sensitivity/                      # Eq. 5 HDD/CDD threshold sensitivity
└── validation/                       # numbered Tethys vs USGS comparison
    ├── 1a-postprocess-tethys.py
    ├── 1b-process-previous-tethys.R          # Khan 2023 prior-version compare
    ├── 1c-spatial-weight-huc-tethys-grid-gwfrac.py
    ├── 2a-process-usgs-data.R
    ├── 3-combine-usgs-tethys.R
    ├── 4a-compare-tethys-usgs.R              # HUC6
    ├── 4b-compare-tethys-usgs-huc12.R
    ├── 5a-paper-figures.R
    ├── 5d-dominant-sector-map.py
    ├── 6-compute-table2-metrics.py
    └── README.md                             # pixi tasks + stage detail
```

Two pixi environments live here: the top-level (`pixi.toml`, Python 3.12, `msdlive-cli`, `awscli` for dataset publishing) and `validation/pixi.toml` (R 4.4+, xarray, geopandas, xagg, tidyverse, sf — covers every numbered validation stage).

`paper/` is a git submodule pointing to `git@github.com:cameronbracken/TETHYS-data-paper.git`. Run `git submodule update --init` after a fresh clone.

`data/`, `output/`, `figures/`, and `validation/data/` are gitignored. The pipeline regenerates `validation/data/`; the rest of `data/` is fetched from MSD-Live (see `data/README.md`).

## Related repos

- [JGCRI/tethys](https://github.com/JGCRI/tethys) — upstream Tethys package (`pip install tethys-downscale`).
- [IMMM-SFA/mosartwmpy](https://github.com/IMMM-SFA/mosartwmpy) — river routing and water management, downstream of Tethys.
- [IMMM-SFA/demeter](https://github.com/IMMM-SFA/demeter) — land-use downscaling that supplies irrigation proxies.
- [IMMM-SFA/cerf](https://github.com/IMMM-SFA/cerf) — power-plant siting that supplies electricity proxies.

## Scenarios

- `historical` (1980–2019)
- `rcp{45,85}{cooler,hotter}_ssp{3,5}` — 8 future scenarios, 2020–2099

CONUS bounding box: `[25.0625, 52.9375, -124.9375, -67.0625]` at 1/8° (0.125°).

---

# Pipeline

End-to-end instructions for producing the IM3 Experiment Group C Tethys water-demand dataset, from climate forcing through validated NetCDF outputs.

The pipeline is organised into four numbered stages:

- **0. Preprocessing** — turn raw inputs into the proxies, weights, and plant locations that Tethys consumes.
- **1. Runs** — run Tethys for the historical scenario and the 8 future scenarios.
- **2. Postprocess** — adjust GCAM basin-level renewable vs non-renewable source shares against USGS and split the gridded output by source.
- **3. Config** — shared configuration artifacts (Tethys YAML, reference data, and `paths.yml` for environment-specific paths).

Validation scripts (Tethys vs USGS comparison) live in a sibling `validation/` tree and are run after stage 2.

## Environments and canonical paths

Three environments are supported. Paths are registered in `scripts/3_config/paths.yml`; scripts still use hard-coded paths but the YAML is the agreed source of truth going forward.

| Environment | Base path | Notes |
|---|---|---|
| Local (macOS) | `/Volumes/data/tethys/` | Mount the external volume. Canonical output in `output_adjusted_usgs_method2/`. |
| PNNL PIC | `/pic/projects/im3/tethys/tethys-im3-scenarios/` | Legacy; most hard-coded paths in `compute_gsi.py` / `compute_deficit.py` still point here. |
| PNNL RCFS / deception | `/rcfs/projects/im3/tethys/` | Current HPC target. `venv/` for default OS, `venv_rocky/` for the Rocky test OS. |
| NERSC | `/global/cfs/projectdirs/m2702/dardiry/Tethys_Demand/` | Used only for the gsi_nersc stage. |

## Prerequisites

Python ≥ 3.10. Install deps:

```bash
pip install -r requirements.txt
pip install tethys-downscale  # or `pip install -e ../tethys-code` from source
```

Stage 0 and validation steps need the data volume mounted (local) or HPC-side access to `/pic/projects/im3/` or `/rcfs/projects/im3/`. Tethys input files (livestock, maps, GCAM database, climate, LULC, power plants, population) are published on MSD-Live — see `data/README.md`.

R ≥ 4.5 for the validation scripts, with `tidyverse`, `sf`, `ncdf4`, `scico`, `ggthemes`.

## Stage 0 — Preprocessing

All scripts live under `scripts/0_preprocessing/`.

### GSI / deficit / monthly irrigation weights (Eldardiry, NERSC)

`scripts/0_preprocessing/gsi_nersc/` bundles the scripts that take TGW-WRF climate forcing and produce per-cell monthly inputs for both irrigation temporal downscaling and electricity HDD/CDD:

1. `TGW_PET_GSI_NERSC.py` — daily potential evapotranspiration and growing-season index (GSI) from hourly TGW-WRF.
2. `Monthly_Deficit_NERSC.py` — monthly P − PET deficit.
3. `Tavg_HDD_CDD.py` — mean temperature and heating/cooling degree days.
4. `daylength.py` — helper for solar declination and daylength used in GSI.
5. `Tethys_Irrigation_Demand_WRF_{Historical,Future}_Forcing_CONUS.py` — scenario-specific drivers that knit these together into the per-cell irrigation demand weights that Tethys reads as `pirrww`.

These scripts run on NERSC against `/global/cfs/projectdirs/m2702/`; outputs are copied into the metarepo flow via `scripts/0_preprocessing/{compute_gsi,compute_deficit,compute_monthly_weights}.py`.

### Aggregation to monthly weights

```bash
# On PIC, after GSI/deficit NetCDFs are in place
sbatch scripts/0_preprocessing/compute_gsi.sh
sbatch scripts/0_preprocessing/compute_deficit.sh
python scripts/0_preprocessing/compute_monthly_weights.py
```

The output is one `irrigation_weight_{scenario}.nc` per scenario, which Tethys's `tdmethods/weights.py` loads as the monthly distribution.

### Proxies

- **Population (SSP-consistent)** — `scripts/0_preprocessing/population_to_tethys/`. See its `README.md` for the decadal→annual-by-state fit that Chris maintains.
- **CERF power plants** — `scripts/0_preprocessing/cerf_to_tethys/cerf_to_tethys.py` turns CERF siting output into Tethys electricity proxies at 1/8° resolution, per technology.
- **Historical global + IM3 CONUS plants** — `scripts/0_preprocessing/im3_power_plants_to_tethys.ipynb` merges GPPD v1.3 (global) with the IM3 CONUS inventory to build the historical `*_gppd_im3_tethys_plants.nc`.

### Livestock, LULC

- **Livestock** (Huang et al. 2018) — used as-is for spatial distribution. Not temporally downscaled.
- **LULC (Demeter)** — `data/demeter/...` supplies per-crop irrigated-area maps referenced by `test_config.yml` and `run_scenario.py`.

## Stage 1 — Runs

Local (one scenario):

```bash
cd scripts/1_runs/im3_tethys_runs
python run_scenario.py rcp45cooler_ssp3
```

On deception (HPC):

```bash
source /rcfs/projects/im3/tethys/venv_rocky/bin/activate
cd scripts/1_runs/im3_tethys_runs
python run_scenario_decep.py rcp45cooler_ssp3
# or via slurm:
sbatch tethys_run.sh
```

Notebook-driven run (for development / iteration):

```bash
jupyter lab scripts/1_runs/run_tethys.ipynb
```

All run drivers consume `scripts/3_config/test_config.yml` as the canonical Tethys configuration, with scenario-specific overrides built in-script. `test_config.yml` uses relative paths that assume `CWD = repo root` — run from the repo root, or `cd` to it inside any wrapper.

## Stage 2 — Postprocess: runoff-share adjustment

GCAM-USA reports per-basin renewable vs non-renewable withdrawals for aggregate demand but does not split by sector. We therefore adjust the basin-level shares against USGS observations and apply them to each sector (except electricity, which we constrain to surface water only).

Canonical script (matches output path naming `/Volumes/data/tethys/output_adjusted_usgs_method2/`):

```bash
python scripts/2_postprocess/adjust_runoff_shares/adjust_runoff_shares_method2_kazi.py
```

The historical-only variant (`adjust_runoff_shares_hist.py`) is kept for comparison. It consumes `usgs-runoff-share-2009-2020.nc` (3D — `lat × lon × Z1=year`) and takes the temporal mean internally; the file is built by:

```bash
cd scripts/2_postprocess/adjust_runoff_shares
Rscript 2b-process-usgs-gwsw-split.R    # writes usgs-runoff-share-2009-2020.nc
python adjust_runoff_shares_hist.py      # consumes it (default --usgs-file)
```

The companion notebooks in `scripts/2_postprocess/adjust_runoff_shares/notebooks/` document the derivation and show diagnostic plots.

Output: `gridded_runoff_shares.nc` per scenario, shipped alongside the per-sector demand files in the published MSD-Live dataset.

## Stage 3 — Config

`scripts/3_config/` holds the Tethys YAML config, environment path registry, and reference data that is loaded by multiple scripts:

- `test_config.yml` — canonical Tethys config; contains relative paths that assume CWD = repo root at run time.
- `paths.yml` — environment-keyed base paths (NERSC / PIC / RCFS / local). Adopted going forward as the source of truth; legacy scripts still hard-code paths.
- `reference_data/counties.tif`, `county_names.csv` — CONUS county map, used for county-level diagnostic aggregation.
- `reference_data/usco2015v2.0.csv` — USGS 2015 county water-use data (also mirrored under `validation/data/`).

## Validation

After a scenario completes, run the numbered validation pipeline from `validation/`:

```bash
cd validation
python 1-postprocess-tethys.py        # aggregate 1/8° to HUCs with xagg
Rscript 2a-process-usgs-data.R
Rscript 3-combine-usgs-tethys.R
Rscript 4a-compare-tethys-usgs.R      # HUC6 comparison
Rscript 4b-compare-tethys-usgs-huc12.R # HUC12 comparison
Rscript 5a-paper-figures.R            # writes to paper/ submodule
```

Validation scripts need `/Volumes/data/tethys/` (local) or equivalent mounted. See `validation/README.md` for the pixi-task wrappers around each step.

## Outputs

The published dataset on MSD-Live contains, per scenario:

- `{sector}_{withdrawals,consumption}.nc` — annual data.
- `{sector}_{withdrawals,consumption}_monthly.nc` — monthly.
- `gridded_runoff_shares.nc` — per-cell GW/SW split.
- `config_{withdrawals,consumption}.yaml` — exact Tethys run config, for reproducibility.

Sectors: Domestic, Electricity, Irrigation, Livestock, Manufacturing, Mining.

## Units and conventions

- Tethys / GCAM: km³/year.
- USGS: MGD (million gallons per day).
- `km3_per_year_TO_mgd = 264172.05124 / 365`.
- `km3_in_one_million_gallons = 3.785412e-06` (reciprocal form; both appear in the codebase).
- Water-use types: **withdrawals** and **consumption**.
- HUC aggregation levels used: HUC2, HUC4, HUC6, HUC8, HUC12.

---

# Reproducing the figures and tables of the data paper

This section describes how to regenerate every figure and table in the Tethys CONUS multi-sector water-demand data descriptor (`main_v4.tex` in the `paper/` submodule) from the canonical Tethys output.

## Prerequisites

### Data

All scripts read from the canonical recent output:

```
/Volumes/data/tethys/output_adjusted_usgs_method2/
├── historical/
├── rcp45cooler_ssp3/
├── rcp45cooler_ssp5/
├── rcp45hotter_ssp3/
├── rcp45hotter_ssp5/
├── rcp85cooler_ssp3/
├── rcp85cooler_ssp5/
├── rcp85hotter_ssp3/
└── rcp85hotter_ssp5/
```

The HDD/CDD-derived sensitivity test additionally reads `/Volumes/data/m5-backup/projects/im3/water-scarcity/tethys_integration_metarepo/data/historical/Tavg_HDD_CDD_Historical_*.nc`.

If those volumes are not mounted, edit the path constants at the top of each script.

### Python environment

The Python figure scripts require numpy, pandas, xarray, matplotlib, and geopandas (only for the optional HUC overlay). On the corresponding author's machine, the conda env `tethys` satisfies all dependencies:

```bash
/opt/homebrew/Caskroom/mambaforge/base/envs/tethys/bin/python <script>
```

For a fresh environment:

```bash
mamba create -n tethys-paper -c conda-forge \
    python=3.12 numpy pandas xarray matplotlib geopandas xagg netCDF4 \
    pyarrow rioxarray
```

### R environment

The R figure scripts use tidyverse, ncdf4, scico, ggthemes, sf. R 4.5.x is sufficient; install via `install.packages(c("tidyverse", "ncdf4", "scico", "ggthemes", "sf"))`.

The R formatter `air` (line-width 100, declared in `air.toml`) is configured for the meta-repository; running it is optional.

## Figure-by-figure reproduction

### Figure 1 — Dominant water-use sector across CONUS

**Output file:** `paper/usage1-dominant-sector-tethys-grid.png`
**Script:** `validation/5d-dominant-sector-map.py`

```bash
cd validation
python 5d-dominant-sector-map.py
```

The script reads the per-sector `*_consumption.nc` files from `historical/`, takes the cell-wise argmax across sectors, and renders the labelled grid. Output also includes a CSV of the labelled grid at `paper/figures/dominant-sector-tethys-grid.csv`.

The previous version of the figure is preserved at `paper/usage1-dominant-sector-tethys-grid_v3rollback.png`.

### Figure 2 — Workflow schematic

**Source:** `paper/flow-chart.tex` (standalone TikZ).
**Output:** `paper/flow-chart.pdf`, included by `main_v4.tex` via `\includegraphics[width=\textwidth]{flow-chart.pdf}`.

```bash
cd paper
pdflatex flow-chart.tex
```

The standalone class crops the PDF to the figure's bounding box, so the include scales cleanly to text width. Edit colors/positions in `flow-chart.tex` and recompile; no rebuild of the main manuscript is needed if only the figure changed (Overleaf will pick up the new PDF). The legacy bitmap source `flow-chart2.pdf` remains in the project directory in case of rollback but is no longer referenced from `main_v4.tex`.

### Figures 3–7 — Validation against USGS at HUC6

**Output files:**

| Figure | File |
|---|---|
| Figure 3 (CONUS annual totals)              | `val1-huc06-usgs-tethys-annual-total.png` |
| Figure 4 (CONUS annual % difference boxplot) | `val2-huc06-usgs-tethys-annual-total-pdiff.png` |
| Figure 5 (HUC6 % difference map)            | `val3-huc06-pdiff-usgs-tethys.png` |
| Figure 6 (HUC6 scatter, USGS vs Tethys)     | `val4-huc06-scatter-usgs-tethys.png` |
| Figure 7 (mean monthly cycle)               | `val5-huc06-usgs-tethys-monthly-total.png` |

**Pipeline:** Run in numbered order from `validation/`:

```bash
cd validation

# 1. Spatial-weight Tethys grid to HUC polygons (requires xagg)
python 1-postprocess-tethys.py

# 2. Process USGS reference data (R)
Rscript 2a-process-usgs-data.R

# 3. Combine USGS and Tethys at HUC scale
Rscript 3-combine-usgs-tethys.R

# 4. Generate the comparison figures
Rscript 4a-compare-tethys-usgs.R
```

`4a-compare-tethys-usgs.R` writes the val1–val5 PNGs into the `paper/` submodule. The script applies a 1.12× scaling to USGS Domestic to align with the public-supply-only definition introduced after 2015.

### Figure 8 — Inter-scenario consistency (CONUS annual demand)

**Output file:** `paper/val6-scenarios-annual-conus-timeseries.png`
**Script:** `validation/5c-scenarios-timeseries.R`

```bash
cd validation
Rscript 5c-scenarios-timeseries.R
```

The script reads `<scenario>/<Sector>_withdrawals.nc` for each of the nine scenarios, sums to CONUS-annual totals, and plots one line per scenario per sector. The historical line runs through 2019; each future scenario is joined to the historical line at 2019 so the visual hand-off is continuous. The previous version is preserved as `val6-scenarios-annual-conus-timeseries_v3rollback.png`.

### Figure 9 — Eq. 5 HDD/CDD threshold sensitivity

**Output files:**

* `paper/eq5-hdd-cdd-sensitivity.png` (figure)
* `paper/figures/eq5-hdd-cdd-sensitivity-summary.csv`
* `paper/figures/eq5-hdd-cdd-sensitivity-monthly-profile.csv`

**Script:** `sensitivity/eq5-hdd-cdd-thresholds.py`

```bash
cd sensitivity
python eq5-hdd-cdd-thresholds.py
```

The script reads `Tavg_HDD_CDD_Historical_2010_2019.nc` from `/Volumes/data/m5-backup/.../tethys_integration_metarepo/data/historical/`, classifies each cell-year into one of the four cases of Eq. 5 under three threshold pairs ((325, 225), default (650, 450), (975, 675)), and plots the resulting CONUS-mean monthly Electricity weight profile under illustrative GCAM-USA shares (p_heat = 0.20, p_cool = 0.40, p_other = 0.40). Edit the `SCENARIOS` and `P_HEAT/P_COOL/P_OTHER` blocks to test other perturbations.

## Table-by-table reproduction

### Table 2 — Validation metrics for withdrawals at HUC6

**Output file:** `paper/figures/validation-metrics.csv`
**Script:** `validation/compute-table2-metrics.py`

```bash
cd validation
python compute-table2-metrics.py
```

The script consumes the per-HUC6 USGS/Tethys CSVs that `1-postprocess-tethys.py` produces in `validation/data/`, sums to annual per HUC6, averages across the USGS reporting years, and computes Pearson r, Spearman ρ, NSE, KGE (with α/β/r decomposition), MBE, NRMSE, and MedAPE per sector. Domestic USGS is scaled by 1.12 to match the public-supply-only definition (consistent with `4a-compare-tethys-usgs.R`).

The values written to the manuscript Table 2 are the rounded `pearson_r`, `spearman_rho`, `nse`, `mbe_pct`, `nrmse_pct`, and `medape_pct` columns for each sector.

### Tables 1, 3, 4

Inline LaTeX `tabular` in `main_v4.tex`; no script.

## Backup files for rollback

If a regenerated figure looks wrong, the previous version is preserved:

| Backup file | Purpose |
|---|---|
| `usage1-dominant-sector-tethys-grid_v3rollback.png` | Pre-v4 dominant-sector map |
| `val6-scenarios-annual-conus-timeseries_v3rollback.png` | Pre-v4 inter-scenario plot (with 2015–2020 visual gap) |
| `flow-chart2.pdf` | Pre-v4 bitmap flow chart (replaced by inline TikZ) |

## End-to-end one-liner (optional)

The full pipeline from raw Tethys output to all figures and tables can be chained:

```bash
# data preparation
cd validation
python 1-postprocess-tethys.py
Rscript 2a-process-usgs-data.R
Rscript 3-combine-usgs-tethys.R

# manuscript figures
Rscript 4a-compare-tethys-usgs.R               # val1..val5
Rscript 5c-scenarios-timeseries.R              # val6
python 5d-dominant-sector-map.py               # Figure 1
python compute-table2-metrics.py               # Table 2 csv
cd ../sensitivity
python eq5-hdd-cdd-thresholds.py               # Figure 9
```

## Troubleshooting

* **`xarray.open_mfdataset` complaining about coordinates:** make sure the HDD/CDD per-decade NetCDFs really have matching `lat`/`lon`/`year` axes. The decade glob in the sensitivity script is intentionally narrowed to `*2010_2019*.nc`.
* **R script path rot:** `4a-compare-tethys-usgs.R` reads `/Volumes/data/shapefiles/HUC<n>/HUC<n>.shp`. If your shapefile path differs, edit the `huc_shape` block.
* **`figures/` directory missing:** Each script `mkdir -p`s its output directory; if you change the output root, change the path constants in the script and in `main_v4.tex` `\includegraphics{...}` calls.

---

# Tasks and open discussion

Running task tracker and domain-level discussion log. See `docs/CLEANUP.md` for the recent `scripts/` reorganization rationale.

## Tasks

 - [ ] Issue with regridding in Tethys https://github.com/JGCRI/tethys/issues/71. Assignee: Chris
 - [ ] Get Hassan running on Tethys (importlib issue). Assignee: Travis, Hassan
 - [ ] Decide how to disaggregate renewable vs fossil water, see below. Assignee: Hassan and all.
 - [ ] Pilot disaggregation code within Tethys. Assignee: Hassan.
 - [ ] Consider if there is a data-driven strategy for renewable/fossil disaggregation. Low priority, but keep an eye out for data. Assignee: Cameron.
 - [ ] Check with Kanishka about the historical LULC data layer. Assignee: Travis.
 - [ ] Run Tethys for the historical period with current tethys but updated GCAM. Assignee: Travis and Hassan.
 - [ ] Investigate the latest USGS water usage data and compare with historical Tethys output. Assignee: Cameron.
 - [x] Provide updated population data. What about historical population? Assignee: Chris. [PR #1](https://github.com/IMMM-SFA/tethys_integration_metarepo/pull/1)
 - [ ] Implement GO-CERF-GO temporal electricity sector downscaling. Assignee: Hassan.
 - [ ] Read the Isaac paper draft and decide how to move it forward. Assignee: Cameron.
 - [ ] Update Tethys in support of these decisions. Assignee: Hassan, Travis.
 - [ ] Connect with the USGS to see if there are other datasets we could leverage (within the IHTM network for instance). TBD once we are farther along.
 - [ ] ADD ALL CODE AND WORKFLOW TO THIS METAREPO. Assignee: all.

## Discussion topics

What data/years to use for "historical" scenario? There is no official historical GCAM-USA run, and the 1975-2015 data within GCAM-USA outputs is not necessarily trustworthy.

How does Tethys handle missing years? I think it just linearly interpolates, is that okay? In particular for the historical run this is relevant since GCAM-USA only provides [1975, 1990, 2005, 2010, 2015, 2020], and 2020 is technically simulated under the future scenario settings.

GCAM-USA, Tethys, mosartwmpy, USGS potentially have different strategies of reporting water usage regarding the location of withdrawal vs the location of delivery/consumption. What problems does this cause and how do we deal with them?

Which population and land use should we use for the historical scenario?

What units does Tethys/GCAM-USA report in? I think it's km^3.

### Renewable vs fossil water disaggregation

GCAM-USA reports renewable vs fossil water usage at the basin level but does not disaggregate by sector.

Hassan proposes to apply the basin-level shares to all cells within the basin, excepting that electricity sector will only use renewable water.

However, we would still want to restrict fossil water usage to grid cells that could conceivably access it. Ideas include using data from Superwell or Jim Yoon or other sources to obtain binary gridded fossil water availability maps.

Such strategies would then need to be implemented into Tethys.

In-depth proposal document: https://pnnl-my.sharepoint.com/:w:/g/personal/hassan_niazi_pnnl_gov/EYcftCLewBpDgnc8mHZp2vcB5SE8A7jN4zT-R9-9PHEDzA?e=5JiX8E
