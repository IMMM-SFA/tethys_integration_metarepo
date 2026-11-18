"""
Eq. 5 (electricity temporal-downscaling) HDD/CDD threshold sensitivity test.

Background: The piecewise definition in Eq. 5 of the manuscript classifies each
1/8 deg cell each year into one of four cases based on whether the annual
heating-degree-day total H_y exceeds a heating threshold (default 650) and
whether the annual cooling-degree-day total C_y exceeds a cooling threshold
(default 450). The threshold convention follows Huang et al. (2018). This
script perturbs the thresholds by +/- 50% and reports:

  1. Partition fractions over CONUS for each threshold pair (case 1 = both
     seasons present, case 2 = heating only, case 3 = cooling only, case 4 =
     neither).
  2. CONUS-aggregated monthly Electricity weight profile under each threshold
     pair, holding GCAM-USA shares (p_heat, p_cool, p_other) at illustrative
     values (0.20, 0.40, 0.40) so the sensitivity isolates the case partition.

Paths resolve through paths.yml; retarget them there, not here.

Inputs (HDD/CDD prepared by gsi_nersc/Tavg_HDD_CDD.py):
  {main_data_dir}/historical/Tavg_HDD_CDD_Historical_*.nc

Outputs:
  {figures_dir}/eq5-hdd-cdd-sensitivity.png
  {paper_figures_dir}/eq5-hdd-cdd-sensitivity.png
  {paper_figures_dir}/eq5-hdd-cdd-sensitivity-summary.csv
  {paper_figures_dir}/eq5-hdd-cdd-sensitivity-monthly-profile.csv
"""

# %% setup
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
import yaml

HERE = Path(__file__).resolve().parent
with open(HERE / "paths.yml", encoding="utf-8") as fh:
    P = yaml.safe_load(fh)

HDDCDD_DIR = (HERE / P["main_data_dir"] / "historical").resolve()

OUT_PAPER = (HERE / P["paper_figures_dir"]).resolve()
OUT_PAPER.mkdir(exist_ok=True, parents=True)

OUT_LOCAL = (HERE / P["figures_dir"]).resolve()
OUT_LOCAL.mkdir(exist_ok=True, parents=True)

# Threshold scenarios: default plus +/- 50%
DEFAULT_HDD = 650
DEFAULT_CDD = 450
SCENARIOS = {
    "low": (DEFAULT_HDD * 0.5, DEFAULT_CDD * 0.5),  # (325, 225)
    "default": (DEFAULT_HDD, DEFAULT_CDD),  # (650, 450)
    "high": (DEFAULT_HDD * 1.5, DEFAULT_CDD * 1.5),  # (975, 675)
}

# Illustrative GCAM-USA shares (heating, cooling, other)
P_HEAT, P_COOL, P_OTHER = 0.20, 0.40, 0.40


# %% load HDD / CDD over the historical reference decade (2010-2019)
nc_files = sorted(HDDCDD_DIR.glob("Tavg_HDD_CDD_Historical_*.nc"))
nc_files = [f for f in nc_files if "2010_2019" in f.name]
assert nc_files, "No HDD/CDD files found"
ds = xr.open_mfdataset(nc_files, combine="by_coords")

hdd_annual = ds["HDD"].sum(dim="month")
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
    total = case.size
    frac_by_case = {}
    for c in (1, 2, 3, 4):
        frac_by_case[c] = float((case == c).sum().values) / total
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
H_y = ds["HDD"].sum(dim="month")
C_y = ds["CDD"].sum(dim="month")
HDD_m = ds["HDD"]
CDD_m = ds["CDD"]
EPS = 1e-9
hdd_share = HDD_m / (H_y + EPS)
cdd_share = CDD_m / (C_y + EPS)
uniform = xr.full_like(hdd_share, 1 / 12)

monthly_profile_per_scenario = {}
for name, (hdd_thr, cdd_thr) in SCENARIOS.items():
    case = assign_case(H_y, C_y, hdd_thr, cdd_thr)
    case_b = case.broadcast_like(HDD_m)
    h_hat = xr.where(
        case_b == 1,
        hdd_share,
        xr.where(case_b == 2, hdd_share, xr.where(case_b == 3, cdd_share, uniform)),
    )
    c_hat = xr.where(
        case_b == 1,
        cdd_share,
        xr.where(case_b == 2, hdd_share, xr.where(case_b == 3, cdd_share, uniform)),
    )
    o_hat = xr.full_like(hdd_share, 1 / 12)
    weight = P_HEAT * h_hat + P_COOL * c_hat + P_OTHER * o_hat
    profile = weight.mean(dim=("year", "lat", "lon")).compute().values
    profile = profile / profile.sum()
    monthly_profile_per_scenario[name] = profile


# %% write summary CSVs
df = pd.DataFrame(partition_rows)
csv_out = OUT_PAPER / "eq5-hdd-cdd-sensitivity-summary.csv"
df.to_csv(csv_out, index=False)
print(f"Wrote {csv_out}")
print(df.to_string(index=False))

prof_df = pd.DataFrame(
    {name: monthly_profile_per_scenario[name] for name in SCENARIOS},
    index=pd.Index(range(1, 13), name="month"),
)
prof_csv = OUT_PAPER / "eq5-hdd-cdd-sensitivity-monthly-profile.csv"
prof_df.to_csv(prof_csv)
print(f"Wrote {prof_csv}")
print(prof_df.round(4).to_string())

print("\nMax monthly weight difference vs default (percentage points):")
default = monthly_profile_per_scenario["default"]
for name in SCENARIOS:
    diff = (monthly_profile_per_scenario[name] - default) * 100
    print(
        f"  {name:8s}  max abs: {np.max(np.abs(diff)):.3f}pp"
        f"  range: [{diff.min():+.3f}, {diff.max():+.3f}]pp"
    )


# %% plot (consistent sans-serif styling, accessible markers/linestyles, no redundant title)
plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.labelsize": 11.5,
        "xtick.labelsize": 10.5,
        "ytick.labelsize": 10.5,
        "legend.fontsize": 10,
    }
)

fig, ax = plt.subplots(figsize=(6.5, 4.5), facecolor="white")
styles = {
    "low": ("#a8501c", "o", "--", "Low (-50%: HDD = 325, CDD = 225)"),
    "default": ("#222222", "s", "-", "Default (HDD = 650, CDD = 450)"),
    "high": ("#3d6b7a", "^", "-.", "High (+50%: HDD = 975, CDD = 675)"),
}

months = np.arange(1, 13)
for name in ("low", "default", "high"):
    color, marker, ls, label = styles[name]
    ax.plot(
        months,
        monthly_profile_per_scenario[name],
        linestyle=ls,
        marker=marker,
        markersize=5.5,
        linewidth=1.6,
        color=color,
        label=label,
    )

ax.set_xlabel("Month")
ax.set_ylabel("CONUS-mean monthly weight")
ax.set_xticks(months)
ax.grid(True, color="#e5e5e5", linewidth=0.7)
for spine in ax.spines.values():
    spine.set_edgecolor("#404040")
    spine.set_linewidth(0.8)
ax.legend(
    frameon=True,
    facecolor="white",
    edgecolor="#cccccc",
    loc="upper center",
    bbox_to_anchor=(0.5, -0.15),
    ncol=1,
)

for out_dir in (OUT_PAPER, OUT_LOCAL):
    fig_out = out_dir / "eq5-hdd-cdd-sensitivity.png"
    fig.savefig(fig_out, dpi=300, bbox_inches="tight", pad_inches=0.08, facecolor="white")
    print(f"Wrote {fig_out}")
plt.close(fig)
