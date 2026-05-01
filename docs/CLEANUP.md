# Metarepo cleanup — inventory & classification

Generated 2026-04-30 as part of the water-scarcity Tethys data paper v2 effort. This is a **proposal**, not a done deal. Nothing moves or gets deleted until the author (Cameron) signs off on each row and pings Hassan/Travis about the changes that affect the shared repo.

## Inventory & proposed classification

Legend:
- **KEEP** — stays where it is.
- **MOVE → path** — relocated under the new numbered `scripts/` layout.
- **DELETE** — remove from repo. Justification noted inline.
- **GITIGNORE** — stays on disk but is excluded from git.
- **PROMOTE** — lift up from a hidden/sub location into a more visible one.

### Top-level files

| File | Proposal | Reason |
|---|---|---|
| `README.md` | **RENAME → `TASKS.md`** | Current README is a task-list and discussion log; keep that content under a name that reflects it. New `README.md` is the canonical entry point (proposal below). |
| `requirements.txt` | KEEP | Pinning for Python deps — Tethys runs use this. |
| `test_config.yml` | **MOVE → `scripts/3_config/test_config.yml`** | This is a canonical Tethys config, not a test; keep next to the run scripts and the new `paths.yml`. |
| `run_tethys.ipynb` | **MOVE → `scripts/1_runs/run_tethys.ipynb`** | Belongs with the other run drivers in `im3_tethys_runs/`. Still uncommitted — include in snapshot commit before move. |
| `im3_power_plants_to_tethys.ipynb` | **MOVE → `scripts/0_preprocessing/im3_power_plants_to_tethys.ipynb`** | CERF-IM3 power-plant merge → Tethys input. Belongs in stage 0. Still uncommitted. |
| `im3_tethys_historical_inputs.zip` | **GITIGNORE + DELETE from workdir once confirmed archived** | Large binary, currently untracked. Flagged in git status. Move to `/Volumes/data/tethys/` or `/rcfs/projects/im3/` if not already there, then remove. |
| `.gitignore` | KEEP + append `validation/tethys-prev-version-compare.pdf`, `figures/`, `*.zip` if appropriate | Already covers `data/` (inc. `validation/data/` — verified via `git check-ignore`). Small tightening only. |
| `.DS_Store` | **DELETE** (one-off) + stays gitignored | macOS cruft, already gitignored. |

### `preprocessing_scripts_gsi_nersc/` (all untracked)

Authored by Hisham Eldardiry (elda639) on NERSC, 2022–2023. Referenced in paper Methods.

| File | Proposal | Reason |
|---|---|---|
| `TGW_PET_GSI_NERSC.py` | **MOVE → `scripts/0_preprocessing/gsi_nersc/TGW_PET_GSI_NERSC.py`** | Computes PET from TGW-WRF forcing. Stage-0 input to Tethys. |
| `Monthly_Deficit_NERSC.py` | **MOVE → `scripts/0_preprocessing/gsi_nersc/`** | Monthly PET − P deficit. Feeds `compute_deficit.py`'s downstream step. |
| `Tavg_HDD_CDD.py` | **MOVE → `scripts/0_preprocessing/gsi_nersc/`** | HDD/CDD from TGW-WRF; used by electricity downscaling. |
| `daylength.py` | **MOVE → `scripts/0_preprocessing/gsi_nersc/`** | Solar declination / daylength helper for GSI. |
| `Tethys_Irrigation_Demand_WRF_Historical_Forcing_CONUS.py` | **MOVE → `scripts/0_preprocessing/gsi_nersc/`** | Historical irrigation weight prep from WRF forcing. |
| `Tethys_Irrigation_Demand_WRF_Historical_Forcing_CONUS_test.py` | **DELETE after confirming with Hisham** | `_test.py` suffix suggests WIP variant; verify it's been superseded by the non-`_test` version. |
| `Tethys_Irrigation_Demand_WRF_Future_Forcing_CONUS.py` | **MOVE → `scripts/0_preprocessing/gsi_nersc/`** | Future scenarios variant of the above. |
| `land.nc`, `mosart.nc`, `MOSART_TGW_LATLON_ELEV.csv`, `wrf_variables_tethys_demand_2020.nc` | **MOVE → `scripts/0_preprocessing/gsi_nersc/inputs/`** | Bundled small reference datasets for these scripts. Check sizes; if any >5 MB, gitignore and document where to fetch. |

**Note for paper Methods section:** these scripts produce the monthly irrigation weights (`pirrww`) that `tethys-code/tethys/tdmethods/irrigation.py` consumes via `load_file(irrfile, ...)`. The chain is: TGW-WRF daily → PET+P → monthly deficit + GSI → `compute_monthly_weights.py` multiplies them → `irrigation_weight_{scenario}.nc` → Tethys reads as the irrigation weight file.

### `scripts/` (existing tracked files)

| File | Caller(s) | Proposal | Reason |
|---|---|---|---|
| `scripts/compute_gsi.py` | `compute_gsi.sh` | **MOVE → `scripts/0_preprocessing/compute_gsi.py`** | Downstream of `TGW_PET_GSI_NERSC.py`; aggregates GSI to monthly. |
| `scripts/compute_gsi.sh` | — | **MOVE → `scripts/0_preprocessing/`** | slurm-ish wrapper; update paths inside. |
| `scripts/compute_deficit.py` | `compute_deficit.sh` | **MOVE → `scripts/0_preprocessing/`** | Computes monthly P−PET deficit. |
| `scripts/compute_deficit.sh` | — | **MOVE → `scripts/0_preprocessing/`** | Wrapper. |
| `scripts/compute_monthly_weights.py` | `run_scenario.py`, `run_scenario_decep.py`, `test_config.yml` | **MOVE → `scripts/0_preprocessing/`** | Produces `irrigation_weight_{scenario}.nc` from deficit × GSI. **Active — do not delete.** |
| `scripts/cerf_to_tethys/cerf_to_tethys.py` | — (standalone) | **MOVE → `scripts/0_preprocessing/cerf_to_tethys/`** | Converts CERF output to Tethys electricity proxy. |
| `scripts/population_to_tethys/*` | — (standalone) | **MOVE → `scripts/0_preprocessing/population_to_tethys/`** | SSP population downscaling to Tethys grid. Has its own README — preserve it. |
| `scripts/adjust_runoff_shares/adjust_runoff_shares_hist.py` | (review) | **MOVE → `scripts/2_postprocess/adjust_runoff_shares/`** | Adjusts GCAM runoff shares using USGS. Produces `gridded_runoff_shares.nc` that becomes part of the published dataset. |
| `scripts/adjust_runoff_shares/adjust_runoff_shares_method2_kazi.py` | (review) | **MOVE → `scripts/2_postprocess/adjust_runoff_shares/`** | Alternative method — ask Kazi/Hassan if this is the canonical one (output path `output_adjusted_usgs_method2/` suggests yes). |
| `scripts/adjust_runoff_shares/*.ipynb` | — | **MOVE → `scripts/2_postprocess/adjust_runoff_shares/notebooks/`** | Exploratory; keep separate from scripts. |
| `scripts/adjust_runoff_shares/*.nc`, `*.png`, `*.zip` | — | **GITIGNORE** | Derived data; should not be in git. Double-check `gridded_runoff_shares_*.nc` — if these are reference inputs (not derived), keep and document. |
| `scripts/im3_tethys_runs/run_scenario.py` | (top-level entry) | **MOVE → `scripts/1_runs/im3_tethys_runs/`** | Local Tethys run driver for one scenario. |
| `scripts/im3_tethys_runs/run_scenario_decep.py` | (top-level entry) | **MOVE → `scripts/1_runs/im3_tethys_runs/`** | Deception HPC variant. |
| `scripts/im3_tethys_runs/tethys_run.sh` | — | **MOVE → `scripts/1_runs/im3_tethys_runs/`** | Shell wrapper. |
| `scripts/im3_tethys_runs/im3_tethys_output.ipynb` | — | **MOVE → `scripts/1_runs/im3_tethys_runs/`** | Output inspection notebook. |
| `scripts/analysis.py` | — (**no callers found**) | **DELETE** | One-off exploration for `year=2015, scenario='Historical'` with hardcoded PNNL-Pic paths. Superseded by the `validation/` pipeline. Git history: single commit (`58952ca`, ~stale). **Confirm with Cameron/Travis before delete.** |
| `scripts/reaggregate.py` | — (**no callers found**) | **DELETE** | Spatial comparison of Tethys output vs input by region. Superseded by `validation/4a-compare-tethys-usgs.R`. Hardcoded Pic paths. **Confirm before delete.** |
| `scripts/counties.tif`, `scripts/county_names.csv` | Used only by the dead `analysis.py` (and stage-0 if kept elsewhere) | **DELETE if `analysis.py` goes; else MOVE → `scripts/3_config/reference_maps/`** | Small reference rasters. If regenerable from USGS shapefiles, delete; if not, keep and cite source. |
| `scripts/usco2015v2.0.csv` | Referenced only by `analysis.py` | **DELETE** if `analysis.py` goes | USGS 2015 county-level water use. Supersedes `USGS_water_2010.csv`. Validation uses `validation/data/usco2015v2.0.csv` (separate copy). |
| `scripts/USGS_water_2010.csv` | — (**no callers**) | **DELETE** | 2010 USGS data, superseded by 2015. |

### `validation/`

| File | Proposal | Reason |
|---|---|---|
| `1-postprocess-tethys.py`, `2a-*.R`, `2b-*.R`, `3-*.R`, `4a-*.R`, `5-paper-figures.R`, `5b-*.py`, `air.toml` | KEEP | Active numbered pipeline. |
| `1b-process-previous-tethys.R` and `1b-spatial-weight-huc-tethys-grid-gwfrac.py` | **KEEP both; rename one** | They do different things (prior-version comparison vs GW-fraction weighting). Propose rename `1b` → `1c` for the gwfrac one so the numbering is non-ambiguous. Alternatively, add a docstring header to each clearly stating its role. |
| `4a-compare-tethys-usgs.R` vs `4b-compare-tethys-usgs-huc12.R` | **KEEP both** | 4a is HUC6 comparison, 4b is HUC12. Different aggregation levels, both used. Add one-line docstring header so future readers know. |
| `tethys-prev-version-compare.pdf` | **GITIGNORE + keep on disk** | Large PDF output, untracked currently. Either add to gitignore or delete and regenerate on demand. |

### `validation/data/`

~600 CSV files, **none tracked in git** (confirmed via `git ls-files validation/data/ | wc -l == 0`). These are derived intermediates from the numbered pipeline. Keep them gitignored; make sure the pipeline can regenerate them end-to-end. No cleanup action needed on the repo side.

**However:** these 600 files are on your laptop in the repo working tree. Consider moving the whole `validation/data/` directory to `/Volumes/data/tethys/validation_intermediates/` and symlinking back — frees local disk and keeps the logical location. Optional.

### `data/`, `output/`, `figures/`

All three are under `data/`-style gitignore. Not tracked. Leave alone.

## Aggregate impact

| Action | File count | Risk |
|---|---|---|
| Move (preserve history with `git mv`) | ~25 files | Low — imports/invocations update mechanically |
| Rename | 2 (`README.md` → `TASKS.md`; `1b-*` → `1c-*`) | Low |
| Delete | 4–5 scripts + 1–2 reference CSVs (pending author confirmation) | Medium — need Hassan/Travis sign-off if any cross-team dependency |
| Git-ignore new patterns | ~3 (`*.zip`, `validation/tethys-prev-version-compare.pdf`, etc.) | Low |
| Add new files | 5 (`README.md` replacement, `PIPELINE.md`, `scripts/3_config/paths.yml`, `docs/CLEANUP.md` (this file), `docs/PIPELINE_CHECKLIST.md`) | None |

## Proposed final layout

```
tethys_integration_metarepo/
├── README.md                         # rewritten — one-paragraph overview + pointer to PIPELINE.md
├── TASKS.md                          # old README content moved here
├── PIPELINE.md                       # end-to-end run docs, stage 0 → 3
├── requirements.txt
├── .gitignore
├── docs/
│   ├── CLEANUP.md                    # this file
│   └── PIPELINE_CHECKLIST.md         # smoke-test checklist
├── scripts/
│   ├── 0_preprocessing/
│   │   ├── gsi_nersc/                # moved from preprocessing_scripts_gsi_nersc/
│   │   │   ├── TGW_PET_GSI_NERSC.py
│   │   │   ├── Monthly_Deficit_NERSC.py
│   │   │   ├── Tavg_HDD_CDD.py
│   │   │   ├── daylength.py
│   │   │   ├── Tethys_Irrigation_Demand_WRF_{Historical,Future}_Forcing_CONUS.py
│   │   │   └── inputs/               # land.nc, mosart.nc, MOSART_TGW_LATLON_ELEV.csv
│   │   ├── cerf_to_tethys/
│   │   ├── population_to_tethys/
│   │   ├── im3_power_plants_to_tethys.ipynb
│   │   ├── compute_gsi.{py,sh}
│   │   ├── compute_deficit.{py,sh}
│   │   └── compute_monthly_weights.py
│   ├── 1_runs/
│   │   ├── run_tethys.ipynb
│   │   └── im3_tethys_runs/
│   │       ├── run_scenario.py
│   │       ├── run_scenario_decep.py
│   │       ├── tethys_run.sh
│   │       └── im3_tethys_output.ipynb
│   ├── 2_postprocess/
│   │   └── adjust_runoff_shares/
│   │       ├── adjust_runoff_shares_hist.py
│   │       ├── adjust_runoff_shares_method2_kazi.py  # canonical per output path name
│   │       └── notebooks/
│   └── 3_config/
│       ├── test_config.yml
│       └── paths.yml                 # NEW: centralise NERSC/PIC/Volumes paths
└── validation/                       # unchanged layout, minor rename
    ├── 1-postprocess-tethys.py
    ├── 1b-process-previous-tethys.R
    ├── 1c-spatial-weight-huc-tethys-grid-gwfrac.py   # renamed from 1b
    ├── 2a-process-usgs-data.R
    ├── 2b-process-usgs-gwsw-split.R
    ├── 3-combine-usgs-tethys.R
    ├── 4a-compare-tethys-usgs.R
    ├── 4b-compare-tethys-usgs-huc12.R
    ├── 5-paper-figures.R
    ├── 5b-demand-sector-by-grid-cell.py
    ├── 5c-scenarios-timeseries.R     # NEW: the 4-panel scenario figure
    ├── air.toml
    └── data/                         # gitignored, regenerable
```

## Checkpoints before proceeding

- [ ] Cameron confirms `analysis.py` and `reaggregate.py` can be deleted (both have no callers and hard-coded stale paths).
- [ ] Cameron confirms `USGS_water_2010.csv` can be deleted (no callers).
- [ ] Hassan confirms `adjust_runoff_shares_method2_kazi.py` is the canonical runoff-share method (consistent with `output_adjusted_usgs_method2/` path name).
- [ ] Hisham confirms the non-`_test` variant of `Tethys_Irrigation_Demand_WRF_Historical_Forcing_CONUS.py` is the canonical one.
- [ ] Hassan/Travis heads-up on the metarepo reorganization before any `git mv` commits.
- [ ] `im3_tethys_historical_inputs.zip` is safely archived somewhere that isn't git.
