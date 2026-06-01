"""
Eq. 5 (electricity temporal-downscaling) HDD/CDD threshold sensitivity test.

Background. The piecewise definition in Eq. 5 of the manuscript classifies each
1/8 deg cell each year into one of four cases based on whether the annual
heating-degree-day total H_y exceeds a heating threshold (default 650) and
whether the annual cooling-degree-day total C_y exceeds a cooling threshold
(default 450). The threshold convention is from Huang et al. (2018), but no
sensitivity has been reported. This script perturbs the thresholds by +/- 50%
and reports:

  1. Partition fractions over CONUS for each threshold pair (case 1 = both
     seasons present, case 2 = heating only, case 3 = cooling only, case 4 =
     neither).
  2. CONUS-aggregated monthly Electricity weight profile under each threshold
     pair, holding GCAM-USA shares (p_heat, p_cool, p_other) at illustrative
     values (0.20, 0.40, 0.40) so the sensitivity is to the case partition
     only, not the GCAM share.

Inputs (HDD/CDD prepared by gsi_nersc/Tavg_HDD_CDD.py):
  /Volumes/data/m5-backup/projects/im3/water-scarcity/tethys_integration_metarepo/data/historical/Tavg_HDD_CDD_Historical_{decade}.nc

Outputs:
  ../../tethys-data-paper/figures/eq5-hdd-cdd-sensitivity-summary.csv
  ../../tethys-data-paper/figures/eq5-hdd-cdd-sensitivity.png
"""

# %% setup
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
HDDCDD_DIR = Path(
    "/Volumes/data/m5-backup/projects/im3/water-scarcity/"
    "tethys_integration_metarepo/data/historical"
)
OUT = HERE.parent.parent / "tethys-data-paper" / "figures"
OUT.mkdir(exist_ok=True, parents=True)

# Threshold scenarios: default plus +/- 50%
DEFAULT_HDD = 650
DEFAULT_CDD = 450
SCENARIOS = {
    "low": (DEFAULT_HDD * 0.5, DEFAULT_CDD * 0.5),       # (325, 225)
    "default": (DEFAULT_HDD, DEFAULT_CDD),                # (650, 450)
    "high": (DEFAULT_HDD * 1.5, DEFAULT_CDD * 1.5),       # (975, 675)
}

# illustrative GCAM-USA shares (heating, cooling, other)
P_HEAT, P_COOL, P_OTHER = 0.20, 0.40, 0.40


# %% load HDD / CDD over the historical reference decade (2010-2019)
nc_files = sorted(HDDCDD_DIR.glob("Tavg_HDD_CDD_Historical_*.nc"))
nc_files = [f for f in nc_files if "2010_2019" in f.name]
assert nc_files, "No HDD/CDD files found"
ds = xr.open_mfdataset(nc_files, combine="by_coords")

# annual sums
hdd_annual = ds["HDD"].sum(dim="month")  # (year, lat, lon)
cdd_annual = ds["CDD"].sum(dim="month")

# %% per-scenario partition fractions
def assign_case(h_annual, c_annual, hdd_thr, cdd_thr):
    """Return integer case 1..4 per Eq. 5."""
    case = xr.zeros_like(h_annual, dtype="int8")
    cond_h = h_annual >= hdd_thr
    cond_c = c_annual >= cdd_thr
    case = xr.where(cond_h & cond_c, 1, case)
    case = xr.where(cond_h & ~cond_c, 2, case)
    case = xr.where(~cond_h & cond_c, 3, case)
    case = xr.where(~cond_h & ~cond_c, 4, case)
    return case


partition_rows = []
for name, (hdd_thr, cdd_thr) in SCENARIOS.items():
    case = assign_case(hdd_annual, cdd_annual, hdd_thr, cdd_thr)
    # average over years -> (lat, lon) of dominant case fractions
    # but since case is an integer, compute per-cell fraction across years for each case
    n_years = case.sizes["year"]
    n_cells = case.sizes["lat"] * case.sizes["lon"]
    # CONUS-wide partition fractions averaged across all (year, cell) pairs
    total = case.size
    frac_by_case = {}
    for c in (1, 2, 3, 4):
        f = float((case == c).sum().values) / total
        frac_by_case[c] = f
    partition_rows.append(
        {
            "scenario": name,
            "hdd_threshold": hdd_thr,
            "cdd_threshold": cdd_thr,
            "case1_both_pct": round(100 * frac_by_case[1], 1),
            "case2_heating_only_pct": round(100 * frac_by_case[2], 1),
            "case3_cooling_only_pct": round(100 * frac_by_case[3], 1),
            "case4_uniform_pct": round(100 * frac_by_case[4], 1),
        }
    )

# %% per-scenario CONUS-aggregate monthly Electricity weight profile
# weight_m = p_heat * h_hat_m + p_cool * c_hat_m + p_other * (1/12)
# h_hat, c_hat depend on case: case 1 (HDD/H, CDD/C); case 2 (HDD/H, HDD/H);
# case 3 (CDD/C, CDD/C); case 4 (1/12, 1/12).

H_y = ds["HDD"].sum(dim="month")   # (year, lat, lon)
C_y = ds["CDD"].sum(dim="month")
HDD_m = ds["HDD"]                  # (year, month, lat, lon)
CDD_m = ds["CDD"]
EPS = 1e-9
hdd_share = HDD_m / (H_y + EPS)    # (year, month, lat, lon)
cdd_share = CDD_m / (C_y + EPS)
uniform = xr.full_like(hdd_share, 1 / 12)

monthly_profile_per_scenario = {}
for name, (hdd_thr, cdd_thr) in SCENARIOS.items():
    case = assign_case(H_y, C_y, hdd_thr, cdd_thr)
    case_b = case.broadcast_like(HDD_m)
    h_hat = xr.where(
        case_b == 1, hdd_share,
        xr.where(case_b == 2, hdd_share,
                 xr.where(case_b == 3, cdd_share, uniform))
    )
    c_hat = xr.where(
        case_b == 1, cdd_share,
        xr.where(case_b == 2, hdd_share,
                 xr.where(case_b == 3, cdd_share, uniform))
    )
    o_hat = xr.full_like(hdd_share, 1 / 12)
    weight = P_HEAT * h_hat + P_COOL * c_hat + P_OTHER * o_hat
    # CONUS-aggregate monthly profile: cell-mean weight per month
    profile = weight.mean(dim=("year", "lat", "lon")).compute().values
    # renormalize so sum to 1 (for visual comparison)
    profile = profile / profile.sum()
    monthly_profile_per_scenario[name] = profile


# %% write summary CSV
df = pd.DataFrame(partition_rows)
csv_out = OUT / "eq5-hdd-cdd-sensitivity-summary.csv"
df.to_csv(csv_out, index=False)
print(f"Wrote {csv_out}")
print(df.to_string(index=False))

# also write the monthly profiles
prof_df = pd.DataFrame(
    {name: monthly_profile_per_scenario[name] for name in SCENARIOS},
    index=pd.Index(range(1, 13), name="month"),
)
prof_csv = OUT / "eq5-hdd-cdd-sensitivity-monthly-profile.csv"
prof_df.to_csv(prof_csv)
print(f"Wrote {prof_csv}")
print(prof_df.round(4).to_string())

# CONUS-mean shift relative to default
print()
print("Max monthly weight difference vs default (percentage points):")
default = monthly_profile_per_scenario["default"]
for name in SCENARIOS:
    diff = (monthly_profile_per_scenario[name] - default) * 100
    print(f"  {name:8s}  max abs: {np.max(np.abs(diff)):.3f}pp"
          f"  range: [{diff.min():+.3f}, {diff.max():+.3f}]pp")


# %% plot
fig, axes = plt.subplots(1, 2, figsize=(11, 4))

# (a) partition fractions stacked bar
ax = axes[0]
cases = ["case1_both_pct", "case2_heating_only_pct",
         "case3_cooling_only_pct", "case4_uniform_pct"]
labels = ["Case 1: both", "Case 2: heating only",
          "Case 3: cooling only", "Case 4: uniform"]
colors = ["#406084", "#a05a2c", "#5f8a3f", "#888888"]
bottom = np.zeros(len(SCENARIOS))
xs = list(SCENARIOS.keys())
for c, lbl, col in zip(cases, labels, colors):
    vals = df[c].to_numpy()
    ax.bar(xs, vals, bottom=bottom, color=col, label=lbl, edgecolor="white")
    bottom = bottom + vals
ax.set_ylabel("CONUS cell-year fraction (%)")
ax.set_xlabel("Threshold scenario")
xs_with_thr = [
    f"{name}\n(HDD={int(hdd)}, CDD={int(cdd)})"
    for name, (hdd, cdd) in SCENARIOS.items()
]
ax.set_xticks(range(len(xs)))
ax.set_xticklabels(xs_with_thr)
ax.set_ylim(0, 100)
ax.legend(loc="lower right", fontsize=8)
ax.set_title("(a) Eq. 5 case partition")

# (b) monthly weight profile
ax = axes[1]
for name, color in zip(SCENARIOS, ["#a05a2c", "#406084", "#5f8a3f"]):
    ax.plot(range(1, 13), monthly_profile_per_scenario[name],
            "o-", color=color, label=f"{name} (HDD={int(SCENARIOS[name][0])},"
                                     f" CDD={int(SCENARIOS[name][1])})")
ax.set_xlabel("Month")
ax.set_ylabel("CONUS-mean Electricity monthly weight")
ax.set_xticks(range(1, 13))
ax.legend(fontsize=8)
ax.set_title("(b) Resulting monthly weight profile")

fig.suptitle(
    "Eq. 5 HDD/CDD threshold sensitivity (CONUS, historical 2010--2019)",
    fontsize=11,
)
fig.tight_layout()
fig_out = OUT / "eq5-hdd-cdd-sensitivity.png"
fig.savefig(fig_out, dpi=200, bbox_inches="tight")
print(f"Wrote {fig_out}")
