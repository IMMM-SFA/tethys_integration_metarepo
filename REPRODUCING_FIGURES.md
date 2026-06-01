# Reproducing the figures and tables of the Tethys data paper

This document describes how to regenerate every figure and table in the
Tethys CONUS multi-sector water-demand data descriptor (`main_v4.tex` in
the Overleaf project) from the canonical Tethys output.

## 1. Prerequisites

### 1.1 Data

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

The HDD/CDD-derived sensitivity test additionally reads
`/Volumes/data/m5-backup/projects/im3/water-scarcity/tethys_integration_metarepo/data/historical/Tavg_HDD_CDD_Historical_*.nc`.

If those volumes are not mounted, edit the path constants at the top of
each script.

### 1.2 Python environment

The Python figure scripts require numpy, pandas, xarray, matplotlib, and
geopandas (only for the optional HUC overlay). On the corresponding
author's machine, the conda env `tethys` satisfies all dependencies:

```bash
/opt/homebrew/Caskroom/mambaforge/base/envs/tethys/bin/python <script>
```

For a fresh environment:

```bash
mamba create -n tethys-paper -c conda-forge \
    python=3.12 numpy pandas xarray matplotlib geopandas xagg netCDF4 \
    pyarrow rioxarray
```

### 1.3 R environment

The R figure scripts use tidyverse, ncdf4, scico, ggthemes, sf. R 4.5.x
is sufficient; install via `install.packages(c("tidyverse", "ncdf4",
"scico", "ggthemes", "sf"))`.

The R formatter `air` (line-width 100, declared in `air.toml`) is
configured for the meta-repository; running it is optional.

## 2. Figure-by-figure reproduction

### Figure 1 — Dominant water-use sector across CONUS

**Output file:** `tethys-data-paper/usage1-dominant-sector-tethys-grid.png`
**Script:** `validation/5d-dominant-sector-map.py`

```bash
cd validation
python 5d-dominant-sector-map.py
```

The script reads the per-sector `*_consumption.nc` files from
`historical/`, takes the cell-wise argmax across sectors, and renders the
labelled grid. Output also includes a CSV of the labelled grid at
`tethys-data-paper/figures/dominant-sector-tethys-grid.csv`.

The previous version of the figure is preserved at
`tethys-data-paper/usage1-dominant-sector-tethys-grid_v3rollback.png`.

### Figure 2 — Workflow schematic

**Source:** `tethys-data-paper/flow-chart.tex` (standalone TikZ).
**Output:** `tethys-data-paper/flow-chart.pdf`, included by
`main_v4.tex` via `\includegraphics[width=\textwidth]{flow-chart.pdf}`.

```bash
cd tethys-data-paper
pdflatex flow-chart.tex
```

The standalone class crops the PDF to the figure's bounding box, so the
include scales cleanly to text width. Edit colors/positions in
`flow-chart.tex` and recompile; no rebuild of the main manuscript is
needed if only the figure changed (Overleaf will pick up the new PDF).
The legacy bitmap source `flow-chart2.pdf` remains in the project
directory in case of rollback but is no longer referenced from
`main_v4.tex`.

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
Rscript 2b-process-usgs-gwsw-split.R

# 3. Combine USGS and Tethys at HUC scale
Rscript 3-combine-usgs-tethys.R

# 4. Generate the comparison figures
Rscript 4a-compare-tethys-usgs.R
```

`4a-compare-tethys-usgs.R` writes the val1–val5 PNGs into
`tethys-data-paper/` (via the Overleaf symlink at `tethys-data-paper`).
The script applies a 1.12× scaling to USGS Domestic to align with the
public-supply-only definition introduced after 2015.

### Figure 8 — Inter-scenario consistency (CONUS annual demand)

**Output file:** `tethys-data-paper/val6-scenarios-annual-conus-timeseries.png`
**Script:** `validation/5c-scenarios-timeseries.R`

```bash
cd validation
Rscript 5c-scenarios-timeseries.R
```

The script reads `<scenario>/<Sector>_withdrawals.nc` for each of the
nine scenarios, sums to CONUS-annual totals, and plots one line per
scenario per sector. The historical line runs through 2019; each future
scenario is joined to the historical line at 2019 so the visual
hand-off is continuous. The previous version is preserved as
`val6-scenarios-annual-conus-timeseries_v3rollback.png`.

### Figure 9 — Eq. 5 HDD/CDD threshold sensitivity

**Output files:**

* `tethys-data-paper/eq5-hdd-cdd-sensitivity.png` (figure)
* `tethys-data-paper/figures/eq5-hdd-cdd-sensitivity-summary.csv`
* `tethys-data-paper/figures/eq5-hdd-cdd-sensitivity-monthly-profile.csv`

**Script:** `sensitivity/eq5-hdd-cdd-thresholds.py`

```bash
cd sensitivity
python eq5-hdd-cdd-thresholds.py
```

The script reads `Tavg_HDD_CDD_Historical_2010_2019.nc` from
`/Volumes/data/m5-backup/.../tethys_integration_metarepo/data/historical/`,
classifies each cell-year into one of the four cases of Eq. 5 under three
threshold pairs ((325, 225), default (650, 450), (975, 675)), and
plots the resulting CONUS-mean monthly Electricity weight profile under
illustrative GCAM-USA shares (p_heat = 0.20, p_cool = 0.40,
p_other = 0.40). Edit the `SCENARIOS` and `P_HEAT/P_COOL/P_OTHER` blocks
to test other perturbations.

## 3. Table-by-table reproduction

### Table 2 — Validation metrics for withdrawals at HUC6

**Output file:** `tethys-data-paper/figures/validation-metrics.csv`
**Script:** `validation/compute-table2-metrics.py`

```bash
cd validation
python compute-table2-metrics.py
```

The script consumes the per-HUC6 USGS/Tethys CSVs that
`1-postprocess-tethys.py` produces in `validation/data/`, sums to
annual per HUC6, averages across the USGS reporting years, and computes
Pearson r, Spearman ρ, NSE, KGE (with α/β/r decomposition), MBE, NRMSE,
and MedAPE per sector. Domestic USGS is scaled by 1.12 to match the
public-supply-only definition (consistent with `4a-compare-tethys-usgs.R`).

The values written to the manuscript Table 2 are the rounded `pearson_r`,
`spearman_rho`, `nse`, `mbe_pct`, `nrmse_pct`, and `medape_pct` columns
for each sector.

### Table 1 — Comparison with prior datasets

Inline LaTeX `tabular` in `main_v4.tex`; no script.

### Table 3 — Scenario directories

Inline LaTeX `tabular` in `main_v4.tex`; no script.

### Table 4 — GCAM livestock to GLW mapping

Inline LaTeX `tabular` in `main_v4.tex`; no script.

## 4. Backup files for rollback

If a regenerated figure looks wrong, the previous version is preserved:

| Backup file | Purpose |
|---|---|
| `usage1-dominant-sector-tethys-grid_v3rollback.png` | Pre-v4 dominant-sector map |
| `val6-scenarios-annual-conus-timeseries_v3rollback.png` | Pre-v4 inter-scenario plot (with 2015–2020 visual gap) |
| `flow-chart2.pdf` | Pre-v4 bitmap flow chart (replaced by inline TikZ) |

## 5. End-to-end one-liner (optional)

The full pipeline from raw Tethys output to all figures and tables can be
chained:

```bash
# data preparation
cd validation
python 1-postprocess-tethys.py
Rscript 2a-process-usgs-data.R
Rscript 2b-process-usgs-gwsw-split.R
Rscript 3-combine-usgs-tethys.R

# manuscript figures
Rscript 4a-compare-tethys-usgs.R               # val1..val5
Rscript 5c-scenarios-timeseries.R              # val6
python 5d-dominant-sector-map.py               # Figure 1
python compute-table2-metrics.py               # Table 2 csv
cd ../sensitivity
python eq5-hdd-cdd-thresholds.py               # Figure 9
```

## 6. Troubleshooting

* **`xarray.open_mfdataset` complaining about coordinates:** make sure
  the HDD/CDD per-decade NetCDFs really have matching `lat`/`lon`/`year`
  axes. The decade glob in the sensitivity script is intentionally
  narrowed to `*2010_2019*.nc`.
* **R script path rot:** `4a-compare-tethys-usgs.R` reads
  `/Volumes/data/shapefiles/HUC<n>/HUC<n>.shp`. If your shapefile path
  differs, edit the `huc_shape` block.
* **`figures/` directory missing:** Each script `mkdir -p`s its output
  directory; if you change the output root, change the path constants
  in the script and in `main_v4.tex` `\includegraphics{...}` calls.
