# tethys_integration_metarepo

Meta-repository for the code, inputs, and validation that produce the IM3
Experiment Group C multi-sector water-demand dataset for the contiguous
United States (CONUS) at 1/8° resolution, monthly, 1980–2100. The dataset
is the gridded output of [Tethys](https://github.com/JGCRI/tethys)
downscaling driven by GCAM-USA scenarios, and it is consumed downstream
by mosartwmpy for river routing and water management.

## Repository layout

```
tethys_integration_metarepo/
├── README.md                         # this file
├── TASKS.md                          # open tasks & domain discussion
├── PIPELINE.md                       # end-to-end run instructions
├── requirements.txt
├── docs/
│   └── CLEANUP.md                    # 2026 reorganization rationale
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
│   └── 3_config/
│       ├── test_config.yml           # canonical Tethys config
│       └── reference_data/
└── validation/                       # numbered Tethys vs USGS comparison
    ├── 1 – postprocess-tethys.py
    ├── 1b – process-previous-tethys.R (Khan 2023)
    ├── 1c – spatial-weight-huc-tethys-grid-gwfrac.py
    ├── 2a/2b – process-usgs-data*.R
    ├── 3 – combine-usgs-tethys.R
    ├── 4a/4b – compare-tethys-usgs*.R    (HUC6 / HUC12)
    ├── 5 – paper-figures.R
    ├── 5b – demand-sector-by-grid-cell.py
    └── 5c – scenarios-timeseries.R        (TBD, for paper v2)
```

## Getting started

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

Then follow **`PIPELINE.md`** for the full stage-by-stage workflow, from
climate-forcing preprocessing through scenario runs, runoff-share
adjustment, and validation.

Open tasks and longer-running discussion points live in **`TASKS.md`**.

## Scenarios

- `historical` (1980–2019)
- `rcp{45,85}{cooler,hotter}_ssp{3,5}` — 8 future scenarios, 2020–2099

CONUS bounding box: `[25.0625, 52.9375, -124.9375, -67.0625]` at 1/8° (0.125°).

## Related repos

- [JGCRI/tethys](https://github.com/JGCRI/tethys) — upstream Tethys
  package (`pip install tethys-downscale`).
- [IMMM-SFA/mosartwmpy](https://github.com/IMMM-SFA/mosartwmpy) — river
  routing and water management, downstream of Tethys.
- [IMMM-SFA/demeter](https://github.com/IMMM-SFA/demeter) — land-use
  downscaling that supplies irrigation proxies.
- [IMMM-SFA/cerf](https://github.com/IMMM-SFA/cerf) — power-plant siting
  that supplies electricity proxies.
