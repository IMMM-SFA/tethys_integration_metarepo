"""
Compute the per-sector validation metrics for Table 2 of the TETHYS data paper.

Inputs:
  validation/data/huc06-{Sector}-withdrawals-usgs-tethys.csv

For each sector in {Domestic, Electricity, Irrigation}, aggregate to
HUC6 annual totals (sum over months by huc and year), then compute
against USGS:
  - Pearson r
  - Spearman rho
  - NSE (Nash-Sutcliffe)
  - KGE (Kling-Gupta with alpha/beta/r decomposition)
  - MBE in percent of USGS mean
  - NRMSE in percent of USGS mean
  - MedAPE: median absolute percent error (excluding USGS=0 rows)

Outputs:
  figures/validation-metrics.csv
  - one row per sector with the metrics

Run:
  python3 compute-table2-metrics.py
"""

# %% setup
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE.parent.parent / "tethys-data-paper" / "figures"
OUT.mkdir(exist_ok=True, parents=True)

SECTORS = ["Domestic", "Electricity", "Irrigation"]
DEMAND_TYPE = "withdrawals"


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


def nrmse_pct(obs, sim):
    rmse = float(np.sqrt(np.mean((sim - obs) ** 2)))
    return 100.0 * rmse / float(np.mean(obs))


def medape_pct(obs, sim):
    mask = obs != 0
    return 100.0 * float(np.median(np.abs((sim[mask] - obs[mask]) / obs[mask])))


# %% per-sector compute
rows = []
for sector in SECTORS:
    csv = DATA / f"huc06-{sector}-{DEMAND_TYPE}-usgs-tethys.csv"
    df = pd.read_csv(csv, dtype={"huc": str})
    df["year"] = pd.to_datetime(df["datetime"]).dt.year

    annual = (
        df.groupby(["huc", "year"], as_index=False)
        .agg(usgs_km3=("usgs_km3", "sum"), tethys_km3=("tethys_km3", "sum"))
    )

    # restrict to USGS reference years (5-year cadence; data covers 2000-2020)
    usgs_years = sorted(annual.loc[annual["usgs_km3"] > 0, "year"].unique())
    sub = annual[annual["year"].isin(usgs_years)].copy()
    sub = sub[(sub["usgs_km3"].notna()) & (sub["tethys_km3"].notna())]

    obs = sub["usgs_km3"].to_numpy()
    sim = sub["tethys_km3"].to_numpy()

    pearson_r = pearson(obs, sim)
    spearman_r = spearman(obs, sim)
    nse_val = nse(obs, sim)
    kge_val, kge_alpha, kge_beta, kge_r = kge(obs, sim)
    mbe = mbe_pct(obs, sim)
    nrmse = nrmse_pct(obs, sim)
    medape = medape_pct(obs, sim)
    n_huc = sub["huc"].nunique()
    n_obs = len(sub)

    print(
        f"{sector:11s}  n_huc={n_huc}  n_obs={n_obs}  "
        f"r={pearson_r:.3f}  spearman={spearman_r:.3f}  "
        f"NSE={nse_val:.3f}  KGE={kge_val:.3f} "
        f"(alpha={kge_alpha:.3f} beta={kge_beta:.3f} r={kge_r:.3f})  "
        f"MBE={mbe:+.1f}%  NRMSE={nrmse:.1f}%  MedAPE={medape:.1f}%"
    )

    rows.append(
        {
            "sector": sector,
            "demand_type": DEMAND_TYPE,
            "n_huc6": n_huc,
            "n_obs": n_obs,
            "pearson_r": round(pearson_r, 2),
            "spearman_rho": round(spearman_r, 2),
            "nse": round(nse_val, 2),
            "kge": round(kge_val, 2),
            "kge_alpha": round(kge_alpha, 2),
            "kge_beta": round(kge_beta, 2),
            "kge_r": round(kge_r, 2),
            "mbe_pct": round(mbe, 0),
            "nrmse_pct": round(nrmse, 0),
            "medape_pct": round(medape, 0),
        }
    )

# %% write csv
out_df = pd.DataFrame(rows)
out_csv = OUT / "validation-metrics.csv"
out_df.to_csv(out_csv, index=False)
print(f"\nWrote {out_csv}")
print(out_df.to_string(index=False))
