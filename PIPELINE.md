# Pipeline

End-to-end instructions for producing the IM3 Experiment Group C Tethys
water-demand dataset, from climate forcing through validated NetCDF
outputs.

The pipeline is organised into four numbered stages:

- **0. Preprocessing** — turn raw inputs into the proxies, weights, and
  plant locations that Tethys consumes.
- **1. Runs** — run Tethys for the historical scenario and the 8 future
  scenarios.
- **2. Postprocess** — adjust GCAM basin-level renewable vs non-renewable
  source shares against USGS and split the gridded output by source.
- **3. Config** — shared configuration artifacts (Tethys YAML, reference
  data, and `paths.yml` for environment-specific paths).

Validation scripts (Tethys vs USGS comparison) live in a sibling
`validation/` tree and are run after stage 2.

## Environments and canonical paths

Three environments are supported. Paths are registered in
`scripts/3_config/paths.yml`; scripts still use hard-coded paths but the
YAML is the agreed source of truth going forward.

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

Stage 0 and validation steps need the data volume mounted (local) or
HPC-side access to `/pic/projects/im3/` or `/rcfs/projects/im3/`.

R ≥ 4.5 for the validation scripts, with `tidyverse`, `sf`, `ncdf4`,
`scico`, `ggthemes`.

## Stage 0 — Preprocessing

All scripts live under `scripts/0_preprocessing/`.

### GSI / deficit / monthly irrigation weights (Eldardiry, NERSC)

`scripts/0_preprocessing/gsi_nersc/` bundles the scripts that take
TGW-WRF climate forcing and produce per-cell monthly inputs for both
irrigation temporal downscaling and electricity HDD/CDD:

1. `TGW_PET_GSI_NERSC.py` — daily potential evapotranspiration and
   growing-season index (GSI) from hourly TGW-WRF.
2. `Monthly_Deficit_NERSC.py` — monthly P − PET deficit.
3. `Tavg_HDD_CDD.py` — mean temperature and heating/cooling degree days.
4. `daylength.py` — helper for solar declination and daylength used in
   GSI.
5. `Tethys_Irrigation_Demand_WRF_{Historical,Future}_Forcing_CONUS.py`
   — scenario-specific drivers that knit these together into the
   per-cell irrigation demand weights that Tethys reads as `pirrww`.

These scripts run on NERSC against `/global/cfs/projectdirs/m2702/`;
outputs are copied into the metarepo flow via
`scripts/0_preprocessing/{compute_gsi,compute_deficit,compute_monthly_weights}.py`.

### Aggregation to monthly weights

```bash
# On PIC, after GSI/deficit NetCDFs are in place
sbatch scripts/0_preprocessing/compute_gsi.sh
sbatch scripts/0_preprocessing/compute_deficit.sh
python scripts/0_preprocessing/compute_monthly_weights.py
```

The output is one `irrigation_weight_{scenario}.nc` per scenario, which
Tethys's `tdmethods/weights.py` loads as the monthly distribution.

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

All run drivers consume `scripts/3_config/test_config.yml` as the
canonical Tethys configuration, with scenario-specific overrides built
in-script.

## Stage 2 — Postprocess: runoff-share adjustment

GCAM-USA reports per-basin renewable vs non-renewable withdrawals for
aggregate demand but does not split by sector. We therefore adjust the
basin-level shares against USGS observations and apply them to each
sector (except electricity, which we constrain to surface water only).

Canonical script (matches output path naming
`/Volumes/data/tethys/output_adjusted_usgs_method2/`):

```bash
python scripts/2_postprocess/adjust_runoff_shares/adjust_runoff_shares_method2_kazi.py
```

The alternative historical-only variant (`adjust_runoff_shares_hist.py`)
is kept for comparison. The companion notebooks in
`scripts/2_postprocess/adjust_runoff_shares/notebooks/` document the
derivation and show diagnostic plots.

Output: `gridded_runoff_shares.nc` per scenario, shipped alongside the
per-sector demand files in the published MSD-Live dataset.

## Stage 3 — Config

`scripts/3_config/` holds the Tethys YAML config, environment path
registry, and reference data that is loaded by multiple scripts:

- `test_config.yml` — canonical Tethys config; contains relative paths
  that assume CWD = repo root at run time.
- `paths.yml` — environment-keyed base paths (NERSC / PIC / RCFS /
  local). Adopted going forward as the source of truth; legacy scripts
  still hard-code paths.
- `reference_data/counties.tif`, `county_names.csv` — CONUS county map,
  used for county-level diagnostic aggregation.
- `reference_data/usco2015v2.0.csv` — USGS 2015 county water-use data
  (also mirrored under `validation/data/`).

## Validation

After a scenario completes, run the numbered validation pipeline from
`validation/`:

```bash
cd validation
python 1-postprocess-tethys.py       # aggregate 1/8° to HUCs with xagg
Rscript 2a-process-usgs-data.R
Rscript 2b-process-usgs-gwsw-split.R
Rscript 3-combine-usgs-tethys.R
Rscript 4a-compare-tethys-usgs.R      # HUC6 comparison
Rscript 4b-compare-tethys-usgs-huc12.R # HUC12 comparison
Rscript 5-paper-figures.R             # writes to tethys-data-paper/ (Overleaf)
```

Validation scripts need `/Volumes/data/tethys/` (local) or equivalent
mounted.

## Outputs

The published dataset on MSD-Live contains, per scenario:

- `{sector}_{withdrawals,consumption}.nc` — annual data.
- `{sector}_{withdrawals,consumption}_monthly.nc` — monthly.
- `gridded_runoff_shares.nc` — per-cell GW/SW split.
- `config_{withdrawals,consumption}.yaml` — exact Tethys run config,
  for reproducibility.

Sectors: Domestic, Electricity, Irrigation, Livestock, Manufacturing,
Mining.

## Units and conventions

- Tethys / GCAM: km³/year.
- USGS: MGD (million gallons per day).
- `km3_per_year_TO_mgd = 264172.05124 / 365`.
- `km3_in_one_million_gallons = 3.785412e-06` (reciprocal form; both
  appear in the codebase).
- Water-use types: **withdrawals** and **consumption**.
- HUC aggregation levels used: HUC2, HUC4, HUC6, HUC8, HUC12.
