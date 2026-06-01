# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## See also

The parent `../CLAUDE.md` (water-scarcity workspace) covers the scenario matrix, CONUS grid, unit conversions, data volumes, and the surrounding subprojects (`tethys-code`, `mosartwmpy/experiment/`, etc.). This file only covers what is specific to the metarepo.

Other docs in this repo (read these before editing the corresponding area):
- `README.md` -- repo layout, full pipeline (stage 0→3 + validation), figure-by-figure paper reproduction, and the open task / discussion log (single bundled doc)
- `data/README.md` -- input-data inventory and MSD-Live dataset provenance
- `docs/CLEANUP.md` -- rationale for the 2026 `scripts/` reorganization
- `validation/README.md` -- pixi tasks and the numbered Tethys-vs-USGS pipeline

## Repo shape

- `tethys-integration-metarepo/` is the inner git repo of the water-scarcity workspace. `paper/` is a git submodule pointing to `git@github.com:cameronbracken/TETHYS-data-paper.git`. Run `git submodule update --init` after a fresh clone.
- Two pixi environments live here: the top-level `pixi.toml` (Python 3.12, `msdlive-cli`, `awscli` for dataset publishing) and `validation/pixi.toml` (R 4.4+, xarray, geopandas, xagg, tidyverse, sf -- covers every numbered validation stage).
- `output/`, `figures/`, and `validation/data/` are gitignored; the pipeline regenerates them. `data/` is also gitignored (only `data/README.md` is tracked) -- input data lives on MSD-Live, see `data/README.md`.

## Scripts/ is staged; numbering matters

Scripts are organized by pipeline stage, not by language or topic:

- `scripts/0_preprocessing/` -- climate forcing → proxies and weights (gsi_nersc/, cerf_to_tethys/, population_to_tethys/, compute_{gsi,deficit,monthly_weights}.py, im3_power_plants_to_tethys.ipynb)
- `scripts/1_runs/im3_tethys_runs/` -- Tethys scenario drivers: `run_scenario.py` (local), `run_scenario_decep.py` (deception HPC), `tethys_run.sh`
- `scripts/2_postprocess/adjust_runoff_shares/` -- GCAM→USGS source-share adjustment. **Canonical script: `adjust_runoff_shares_method2_kazi.py`** (matches `output_adjusted_usgs_method2/`). `adjust_runoff_shares_hist.py` is the historical-only variant. `2b-process-usgs-gwsw-split.R` produces the consumed input `usgs-runoff-share-2009-2020.nc` (3D: `lat × lon × Z1=year`); `adjust_runoff_shares_hist.py` collapses the `Z1` dim internally. Both the R script and the NetCDF are tracked in this directory -- do not regenerate the NetCDF unless you really mean to.
- `scripts/3_config/` -- shared config consumed by all run drivers: `test_config.yml` (canonical Tethys YAML), `paths.yml` (environment-keyed base paths -- adopted as source of truth going forward; legacy scripts still hard-code paths), `reference_data/`.

When adding a new script, place it under the correct numbered stage. Do not add new top-level scripts.

## Validation pipeline

The numbered files in `validation/` are a strict pipeline -- run in order, each consumes the previous stage's output from `validation/data/`:

```
1a (py) → 2a (R) → 3 (R) → 4a (R, HUC6) / 4b (R, HUC12) → 5a (R) / 5d (py) → 6 (py)
```

Use the pixi tasks (`pixi run postprocess-tethys`, `pixi run process-usgs`, …, `pixi run paper-figures`, `pixi run dominant-sector-map`) -- they hold the canonical command for each stage. `1b` and `1c` are siblings of `1a`, not sequential successors: `1b` processes the prior-version Tethys output, `1c` is a GW-fraction variant. The former `2b-process-usgs-gwsw-split.R` now lives at `scripts/2_postprocess/adjust_runoff_shares/` next to its consumer; it is not part of the validation pipeline. `old/` holds archived earlier versions of `5b` / `5c`; do not edit unless intentionally rolling back.

Stage 5a writes into both `validation/figures/` and `../paper/figures/` by default. Disable the paper write with `pixi run paper-figures -- --no-paper` or `WRITE_PAPER=false pixi run paper-figures`. Stage 5d writes directly into the paper submodule with no toggle. The local `validation/air.toml` overrides the global R formatter (line-width 120, indent 2) for this directory only.

## Working with the paper submodule

`paper/` is the LaTeX manuscript (`main_v4.tex`, `bib/`, `figures/`, `flow-chart.tex`, `previous_versions/`, `reviews/`, `diffs/`, `build_diff.sh`). Figures are written into it by validation stages 5a/5d and `sensitivity/eq5-hdd-cdd-thresholds.py`. Touch the submodule only when:
- regenerating figures via the validation/sensitivity scripts, or
- the user explicitly asks for a manuscript edit.

Commits inside `paper/` are separate from the metarepo; remember to `git add paper` in the parent to bump the submodule pointer.

## Run-driver gotchas

- All Tethys run drivers (`run_scenario.py`, `run_scenario_decep.py`, `run_tethys.ipynb`) consume `scripts/3_config/test_config.yml`. Scenario-specific overrides are layered in-script, not via separate YAML files.
- `test_config.yml` uses relative paths that assume `CWD = repo root`. Run from the repo root, or `cd` to it inside any wrapper.
- `compute_monthly_weights.py` is **active** -- `run_scenario.py` and `test_config.yml` both depend on it. Do not move or rename without updating both.
- Many stage-0 scripts still hard-code `/pic/projects/im3/...` paths. `paths.yml` is the agreed source of truth going forward; migrate paths there as scripts are touched.

## Sensitivity analyses

`sensitivity/eq5-hdd-cdd-thresholds.py` reproduces paper Figure 9 (Eq. 5 HDD/CDD threshold sensitivity for Electricity weights). Reads `Tavg_HDD_CDD_Historical_2010_2019.nc` from `/Volumes/data/m5-backup/.../tethys_integration_metarepo/data/historical/`. New sensitivity scripts go here, not under `validation/` or `scripts/`.

## Local data prerequisites

- `/Volumes/data/tethys/output_adjusted_usgs_method2/` -- canonical Tethys output read by stages 5a, 5d, 6, the sponsor deck, and the manuscript scripts.
- `/Volumes/data/shapefiles/HUC{2,4,6,8,12}/HUC<n>.shp` -- HUC polygons. `4a-compare-tethys-usgs.R` etc. read directly from this path.

If a script fails with a `/Volumes/...` path error, the external volume isn't mounted; that's a user-side fix, not a code fix.

## Conventions specific to this repo

- USGS Domestic is multiplied by 1.12 in `4a-compare-tethys-usgs.R` and `6-compute-table2-metrics.py` to align with the public-supply-only definition introduced after 2015. Keep the two scripts consistent if you change the factor.
- Historical Tethys output runs 1975–2020; futures run 2020–2100. Scenario timeseries plots join them at 2020 for visual continuity.
- Dominant-sector palette: Okabe-Ito (Wong 2011), shared between `5a-paper-figures.R` and `5d-dominant-sector-map.py`. Keep them in sync.
