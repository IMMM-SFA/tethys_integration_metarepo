"""
Compute per-sector validation metrics for Table 4 of the Tethys data paper.

Inputs:
  validation/data/huc06-{Sector}-withdrawals-usgs-tethys.csv

Harmonized comparison window: 2010-2019 (strict overlap of the Tethys
historical period 1980-2019 and all three USGS reanalysis sectors).

For each sector in {Domestic (1.12x scaled and unscaled USGS Public Supply),
Electricity, Irrigation}, sum monthly volumes to annual totals per HUC6 and
year over 2010-2019, average across the 10-year window per HUC6 (excluding
basins where USGS reports zero demand for that sector), and compute:
  - Pearson r and Spearman rho
  - NSE (Nash-Sutcliffe) and KGE (Kling-Gupta)
  - MBE (%) relative to USGS mean
  - MAE (km^3 yr^-1) and RMSE (km^3 yr^-1)
  - NRMSE (%) relative to USGS mean
  - MdAPE (%): median absolute percentage error, 100 * median(|sim - obs| / obs)
  - MdAPD (%): median symmetric absolute percent difference,
               100 * median(|sim - obs| / ((sim + obs) / 2))

Outputs:
  {figures_dir}/validation-metrics.csv
  {paper_figures_dir}/validation-metrics.csv

Run (from validation/):
  pixi run python 6-compute-table2-metrics.py
"""

# %% setup
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
with open(HERE / "paths.yml", encoding="utf-8") as fh:
    P = yaml.safe_load(fh)

DATA = (HERE / P["data_dir"]).resolve()
OUT_LOCAL = (HERE / P["figures_dir"]).resolve()
OUT_PAPER = (HERE / P["paper_figures_dir"]).resolve()
OUT_LOCAL.mkdir(exist_ok=True, parents=True)
OUT_PAPER.mkdir(exist_ok=True, parents=True)

START_YEAR = 2010
END_YEAR = 2019
DEMAND_TYPE = "withdrawals"

SECTOR_SPECS = [
    ("Domestic (1.12x USGS Public Supply)", "Domestic", 1.12),
    ("Domestic (unscaled USGS Public Supply)", "Domestic", 1.00),
    ("Electricity", "Electricity", 1.00),
    ("Irrigation", "Irrigation", 1.00),
]


# %% metric functions
def pearson(x, y):
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x, y):
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    return float(np.corrcoef(rx, ry)[0, 1])


def nse(obs, sim):
    return 1.0 - float(np.sum((sim - obs) ** 2) / np.sum((obs - np.mean(obs)) ** 2))


def kge(obs, sim):
    r = pearson(obs, sim)
    alpha = float(np.std(sim) / np.std(obs))
    beta = float(np.mean(sim) / np.mean(obs))
    kge_val = 1.0 - float(np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2))
    return kge_val, alpha, beta, r


def mbe_pct(obs, sim):
    return 100.0 * float(np.mean(sim - obs) / np.mean(obs))


def mae_val(obs, sim):
    return float(np.mean(np.abs(sim - obs)))


def rmse_val(obs, sim):
    return float(np.sqrt(np.mean((sim - obs) ** 2)))


def nrmse_pct(obs, sim):
    return 100.0 * rmse_val(obs, sim) / float(np.mean(obs))


def mdape_pct(obs, sim):
    mask = obs > 0
    return 100.0 * float(np.median(np.abs((sim[mask] - obs[mask]) / obs[mask])))


def mdapd_sym_pct(obs, sim):
    denom = (sim + obs) / 2.0
    mask = denom > 0
    return 100.0 * float(np.median(np.abs((sim[mask] - obs[mask]) / denom[mask])))


# %% per-sector compute (2010-2019 HUC6 annual means, USGS > 0)
rows = []
for label, sector_file, usgs_scale in SECTOR_SPECS:
    csv = DATA / f"huc06-{sector_file}-{DEMAND_TYPE}-usgs-tethys.csv"
    df = pd.read_csv(csv, dtype={"huc": str})
    df["year"] = pd.to_datetime(df["datetime"]).dt.year
    df = df[(df["year"] >= START_YEAR) & (df["year"] <= END_YEAR)].copy()
    df["usgs_km3"] = df["usgs_km3"] * usgs_scale

    annual = df.groupby(["huc", "year"], as_index=False).agg(
        usgs_km3=("usgs_km3", "sum"),
        tethys_km3=("tethys_km3", "sum"),
    )
    huc_mean = annual.groupby("huc", as_index=False).agg(
        usgs_km3=("usgs_km3", "mean"),
        tethys_km3=("tethys_km3", "mean"),
    )
    sub = huc_mean[
        (huc_mean["usgs_km3"].notna())
        & (huc_mean["tethys_km3"].notna())
        & (huc_mean["usgs_km3"] > 0)
    ].copy()

    obs = sub["usgs_km3"].to_numpy()
    sim = sub["tethys_km3"].to_numpy()

    pearson_r = pearson(obs, sim)
    spearman_r = spearman(obs, sim)
    nse_val = nse(obs, sim)
    kge_val, kge_alpha, kge_beta, kge_r = kge(obs, sim)
    mbe = mbe_pct(obs, sim)
    mae = mae_val(obs, sim)
    rmse = rmse_val(obs, sim)
    nrmse = nrmse_pct(obs, sim)
    mdape = mdape_pct(obs, sim)
    mdapd = mdapd_sym_pct(obs, sim)
    n_huc = len(sub)

    print(
        f"{label:38s}  n_huc={n_huc:3d}  "
        f"r={pearson_r:.3f}  MBE={mbe:+5.1f}%  "
        f"MAE={mae:.3f}  RMSE={rmse:.3f}  NRMSE={nrmse:5.1f}%  "
        f"MdAPE={mdape:5.1f}%  MdAPD_sym={mdapd:5.1f}%"
    )

    rows.append(
        {
            "sector": label,
            "demand_type": DEMAND_TYPE,
            "years": f"{START_YEAR}-{END_YEAR}",
            "usgs_scale": usgs_scale,
            "n_huc6": n_huc,
            "pearson_r": round(pearson_r, 2),
            "spearman_rho": round(spearman_r, 2),
            "nse": round(nse_val, 2),
            "kge": round(kge_val, 2),
            "kge_alpha": round(kge_alpha, 2),
            "kge_beta": round(kge_beta, 2),
            "kge_r": round(kge_r, 2),
            "mbe_pct": int(round(mbe, 0)),
            "mae_km3_yr": round(mae, 2),
            "rmse_km3_yr": round(rmse, 2),
            "nrmse_pct": int(round(nrmse, 0)),
            "mdape_pct": int(round(mdape, 0)),
            "mdapd_sym_pct": int(round(mdapd, 0)),
        }
    )

# %% write csvs
out_df = pd.DataFrame(rows)
for out_dir in (OUT_LOCAL, OUT_PAPER):
    out_csv = out_dir / "validation-metrics.csv"
    out_df.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv}")

print("\nSummary table:")
print(out_df.to_string(index=False))
