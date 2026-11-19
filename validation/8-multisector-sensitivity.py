"""
Multi-sector spatial, source-share, and temporal downscaling sensitivity analysis.

Evaluates sensitivity across all six Tethys water-demand sectors (Irrigation,
Electricity, Domestic/Municipal, Manufacturing, Mining, and Livestock) plus the
USGS-anchored groundwater-to-surface-water source-share post-processing (Eq. 8):

  1. Spatial-proxy & source-share perturbations at the HUC6 basin scale (2015,
     holding GCAM-USA regional totals fixed so regional mass is conserved):
       - Proxy reference-epoch updates (Domestic 2010 vs. 2015 SSP population;
         Irrigation 2005 vs. 2015 Demeter irrigated cropland)
       - Subsector proxy pooling (collapsing 11 Demeter crop classes, 7 GPPD/IM3
         power-plant fuel classes, or 5 GLW3 livestock species groups)
       - Structural proxy substitution against empirical 2015 USGS county water-use
         records (Circular 1441, Dieter et al., 2018) across Domestic, Irrigation,
         Livestock, Electricity (cooling-informed thermoelectric), Manufacturing,
         and Mining, plus predecessor state-population proxy for Electricity
       - Unanchored GCAM-USA vs. USGS-anchored groundwater withdrawals (Eq. 8)

  2. Temporal-downscaling weight perturbations over the harmonized 2010-2019
     validation decade across the three weather-driven sectors (benchmarked
     against 2010-2019 USGS monthly HUC12 reanalysis profiles) and the uniform
     1/12 assumption used for Manufacturing, Mining, and Livestock:
       - Irrigation (Eq. 4): Deficit x GSI (default) vs. GSI-only (no P deficit)
         and temperature-only positive degree-month weighting
       - Electricity (Eqs. 5-6): +/-50% HDD/CDD regime thresholds around (650, 450)
         and 2x cooling-load share perturbation
       - Domestic/Municipal (Eq. 7): +/-50% Wada regional amplitude R and uniform
         1/12 baseline (R = 0)

All paths resolve through validation/paths.yml.

Outputs:
  {figures_dir}/val6-multisector-sensitivity.png
  {paper_figures_dir}/val6-multisector-sensitivity.png
  {figures_dir}/sensitivity-spatial-huc6.csv
  {paper_figures_dir}/sensitivity-spatial-huc6.csv
  {figures_dir}/sensitivity-temporal-monthly.csv
  {paper_figures_dir}/sensitivity-temporal-monthly.csv
"""

from pathlib import Path

import matplotlib.gridspec as gridspec
import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
import yaml
from scipy.sparse import csr_matrix

HERE = Path(__file__).resolve().parent
with open(HERE / "paths.yml", encoding="utf-8") as fh:
    P = yaml.safe_load(fh)

HIST_IN = (HERE / P["main_data_dir"] / "historical").resolve()
HIST_OUT = (HERE / P["tethys_output_canonical"] / "historical").resolve()
VAL_DATA = (HERE / P["data_dir"]).resolve()
REF_DATA = (HERE / P["reference_data_dir"]).resolve()
RAW_SW_PATH = (HERE / P["raw_runoff_shares_hist"]).resolve()

OUT_PAPER = (HERE / P["paper_figures_dir"]).resolve()
OUT_PAPER.mkdir(exist_ok=True, parents=True)
OUT_LOCAL = (HERE / P["figures_dir"]).resolve()
OUT_LOCAL.mkdir(exist_ok=True, parents=True)

# -----------------------------------------------------------------------------
# Grid & sparse 1/8-deg cell -> HUC6 area-weighted aggregator
# -----------------------------------------------------------------------------
with xr.open_dataset(HIST_OUT / "Domestic_withdrawals.nc") as ds_ref:
    LAT = ds_ref.lat.values  # 224, descending (52.9375 -> 25.0625)
    LON = ds_ref.lon.values  # 464, ascending (-124.9375 -> -67.0625)

pap = pd.read_csv(VAL_DATA / "pixel_area_proportion_huc6.csv")
lat_idx = np.round((LAT[0] - pap["lat"].values) / 0.125).astype(int)
lon_idx = np.round((pap["lon"].values - LON[0]) / 0.125).astype(int)
valid_pap = (lat_idx >= 0) & (lat_idx < len(LAT)) & (lon_idx >= 0) & (lon_idx < len(LON))
pap = pap.loc[valid_pap].copy()
pap["cell_flat"] = lat_idx[valid_pap] * len(LON) + lon_idx[valid_pap]
hucs = np.sort(pap["huc"].unique())
pap["huc_i"] = pap["huc"].map({h: i for i, h in enumerate(hucs)})

M_HUC6 = csr_matrix(
    (pap["pix_area_prop"].values, (pap["huc_i"].values, pap["cell_flat"].values)),
    shape=(len(hucs), len(LAT) * len(LON)),
)


def to_huc6(grid_2d: np.ndarray) -> np.ndarray:
    """Aggregate a (224, 464) 1/8-deg CONUS grid to HUC6 accounting units."""
    return M_HUC6 @ np.nan_to_num(np.asarray(grid_2d, dtype=np.float64), nan=0.0).ravel()


def sample_tif_conus(tif_path: Path) -> np.ndarray:
    """Sample a raster at exact Tethys 1/8-deg cell centers."""
    with rasterio.open(tif_path) as src:
        xx, yy = np.meshgrid(LON, LAT)
        coords = np.column_stack([xx.ravel(), yy.ravel()])
        vals = np.array([v[0] for v in src.sample(coords)], dtype=np.float64).reshape(
            len(LAT), len(LON)
        )
        if src.nodata is not None:
            vals = np.where(vals == src.nodata, np.nan, vals)
    return vals


def downscale_region(
    total_by_grid: np.ndarray, region_mask: np.ndarray, proxy_grid: np.ndarray
) -> np.ndarray:
    """Mass-conserving spatial allocation within each GCAM-USA region ID (Eq. 3)."""
    out = np.zeros_like(total_by_grid, dtype=np.float64)
    tot_clean = np.nan_to_num(total_by_grid, nan=0.0)
    prx_clean = np.maximum(np.nan_to_num(proxy_grid, nan=0.0), 0.0)
    regs = np.unique(region_mask[np.isfinite(region_mask) & (region_mask > 0)])
    for r in regs:
        m = region_mask == r
        reg_dem = tot_clean[m].sum()
        if reg_dem <= 0:
            continue
        p_sum = prx_clean[m].sum()
        if p_sum > 0:
            out[m] = reg_dem * (prx_clean[m] / p_sum)
        else:
            out[m] = reg_dem / m.sum()
    return out


# =============================================================================
# PART 1: SPATIAL-PROXY & SOURCE-SHARE SENSITIVITY (2015, ALL 6 SECTORS + EQ. 8)
# =============================================================================
states_mask = sample_tif_conus(HIST_IN / "states.tif")
stbasin_mask = sample_tif_conus(HIST_IN / "statebasins.tif")
usa_mask = sample_tif_conus(HIST_IN / "USA.tif")
counties_id_grid = np.nan_to_num(sample_tif_conus(REF_DATA / "counties.tif"), nan=-1).astype(int)

pop_2010 = np.maximum(np.nan_to_num(sample_tif_conus(HIST_IN / "ssp3_2010.tif"), nan=0.0), 0.0)
pop_2020 = np.maximum(np.nan_to_num(sample_tif_conus(HIST_IN / "ssp3_2020.tif"), nan=0.0), 0.0)
pop_2015 = 0.5 * (pop_2010 + pop_2020)

# Map county raster ID -> 5-digit county FIPS -> USGS 2015 county water use
cnames = pd.read_csv(REF_DATA / "county_names.csv")
id_to_fips = dict(zip(cnames["id"].astype(int), cnames["FIPS"].astype(int)))
fips_grid = np.vectorize(lambda cid: id_to_fips.get(cid, -1))(counties_id_grid)
uniq_fips, counts_fips = np.unique(fips_grid[fips_grid > 0], return_counts=True)
fips_cell_count = dict(zip(uniq_fips, counts_fips))

usco_raw = pd.read_csv(REF_DATA / "usco2015v2.0.csv", skiprows=1)
usco_cols = ["IN-Wtotl", "MI-Wtotl", "LI-WFrTo", "PT-Wtotl", "IR-WFrTo", "PS-Wtotl", "DO-WFrTo"]
usco = pd.DataFrame(
    {"FIPS_int": pd.to_numeric(usco_raw["FIPS"], errors="coerce").fillna(-1).astype(int)}
)
for col in usco_cols:
    usco[col] = pd.to_numeric(usco_raw[col], errors="coerce").fillna(0.0)
usco["DOM_tot"] = usco["PS-Wtotl"] + usco["DO-WFrTo"]


def county_col_to_grid(col_name: str) -> np.ndarray:
    val_map = dict(zip(usco["FIPS_int"], usco[col_name]))
    out = np.zeros_like(pop_2015)
    for f, cnt in fips_cell_count.items():
        v = val_map.get(f, 0.0)
        if v > 0:
            out[fips_grid == f] = v / cnt
    return out


sec_2015 = {}
for s in ["Domestic", "Electricity", "Irrigation", "Livestock", "Manufacturing", "Mining"]:
    with xr.open_dataset(HIST_OUT / f"{s}_withdrawals.nc") as ds:
        sec_2015[s] = sum(ds[v].sel(year=2015).fillna(0.0).values for v in ds.data_vars)

with xr.open_dataset(HIST_IN / "historical_gppd_im3_tethys_plants.nc") as ds_pl:
    ds_pl_sub = ds_pl.sel(lat=LAT, lon=LON, method="nearest")
    pooled_mw = sum(
        np.nan_to_num(ds_pl_sub[v].isel(year=0).values, nan=0.0)
        for v in ["Biomass", "Coal", "Gas", "Geothermal", "Nuclear", "Oil", "Solar"]
    )


def load_demeter_tot_irr(yr: int) -> np.ndarray:
    fname = f"output_wo_harvforest_demeter_CONUS_harmonized_im3_demeter_rcp45cooler_ssp3_{yr}.nc"
    with xr.open_dataset(HIST_IN / fname) as ds_d:
        lat_n = "latitude" if "latitude" in ds_d.coords else "lat"
        lon_n = "longitude" if "longitude" in ds_d.coords else "lon"
        ds_sub = ds_d.sel({lat_n: LAT, lon_n: LON}, method="nearest")
        tot = np.zeros((len(LAT), len(LON)), dtype=np.float64)
        for v in ds_sub.data_vars:
            if str(ds_sub[v].attrs.get("long_name", v)).endswith("_irr"):
                tot += np.nan_to_num(ds_sub[v].values, nan=0.0)
    return tot


dem_2015_pooled = load_demeter_tot_irr(2015)
dem_2005_pooled = load_demeter_tot_irr(2005)
cattle_only = np.maximum(
    np.nan_to_num(sample_tif_conus(HIST_IN / "5_Ct_2010_Da.tif"), nan=0.0), 0.0
) + np.maximum(np.nan_to_num(sample_tif_conus(HIST_IN / "5_Bf_2010_Da.tif"), nan=0.0), 0.0)

with xr.open_dataset(RAW_SW_PATH) as ds_sw_raw, xr.open_dataset(
    HIST_OUT / "gridded_runoff_shares.nc"
) as ds_sw_adj:
    sw_raw = np.nan_to_num(ds_sw_raw["share"].sel(year=2015).values, nan=1.0)
    sw_adj = np.nan_to_num(ds_sw_adj["share"].sel(year=2015).values, nan=1.0)

non_elec_2015 = sum(
    sec_2015[s] for s in ["Domestic", "Irrigation", "Livestock", "Manufacturing", "Mining"]
)
irr_pooled_2015_grid = downscale_region(sec_2015["Irrigation"], stbasin_mask, dem_2015_pooled)

spatial_specs = [
    (
        "Domestic: static 2010 vs. 2015 SSP pop.",
        "Domestic",
        "Epoch update",
        sec_2015["Domestic"],
        downscale_region(sec_2015["Domestic"], states_mask, pop_2010),
    ),
    (
        "Irrigation: static 2005 vs. 2015 Demeter",
        "Irrigation",
        "Epoch update",
        irr_pooled_2015_grid,
        downscale_region(sec_2015["Irrigation"], stbasin_mask, dem_2005_pooled),
    ),
    (
        "Irrigation: pooled vs. 11-crop Demeter",
        "Irrigation",
        "Subsector pooling",
        sec_2015["Irrigation"],
        irr_pooled_2015_grid,
    ),
    (
        "Domestic: USGS county municipal vs. pop.",
        "Domestic",
        "Alternative proxy",
        sec_2015["Domestic"],
        downscale_region(sec_2015["Domestic"], states_mask, county_col_to_grid("DOM_tot")),
    ),
    (
        "Livestock: USGS county livestock vs. GLW3",
        "Livestock",
        "Alternative proxy",
        sec_2015["Livestock"],
        downscale_region(sec_2015["Livestock"], usa_mask, county_col_to_grid("LI-WFrTo")),
    ),
    (
        "Livestock: cattle-only vs. 5-species GLW3",
        "Livestock",
        "Subsector pooling",
        sec_2015["Livestock"],
        downscale_region(sec_2015["Livestock"], usa_mask, cattle_only),
    ),
    (
        "Electricity: pooled MW vs. 7-fuel plants",
        "Electricity",
        "Subsector pooling",
        sec_2015["Electricity"],
        downscale_region(sec_2015["Electricity"], states_mask, pooled_mw),
    ),
    (
        "Irrigation: USGS county irrig. vs. Demeter",
        "Irrigation",
        "Alternative proxy",
        sec_2015["Irrigation"],
        downscale_region(sec_2015["Irrigation"], stbasin_mask, county_col_to_grid("IR-WFrTo")),
    ),
    (
        "Mining: USGS county mining vs. state pop.",
        "Mining",
        "Alternative proxy",
        sec_2015["Mining"],
        downscale_region(sec_2015["Mining"], states_mask, county_col_to_grid("MI-Wtotl")),
    ),
    (
        "Manufacturing: USGS indust. vs. state pop.",
        "Manufacturing",
        "Alternative proxy",
        sec_2015["Manufacturing"],
        downscale_region(sec_2015["Manufacturing"], states_mask, county_col_to_grid("IN-Wtotl")),
    ),
    (
        "Electricity: cooling-informed vs. plant MW",
        "Electricity",
        "Alternative proxy",
        sec_2015["Electricity"],
        downscale_region(sec_2015["Electricity"], states_mask, county_col_to_grid("PT-Wtotl")),
    ),
    (
        "Electricity: state pop. (v1) vs. plant MW",
        "Electricity",
        "Alternative proxy",
        sec_2015["Electricity"],
        downscale_region(sec_2015["Electricity"], states_mask, pop_2015),
    ),
    (
        "GW source (Eq. 8): raw GCAM vs. USGS",
        "Source share",
        "Source anchoring",
        (1.0 - sw_adj) * non_elec_2015,
        (1.0 - sw_raw) * non_elec_2015,
    ),
]

spatial_rows = []
for label, sector, category, base_g, alt_g in spatial_specs:
    h_base = to_huc6(base_g)
    h_alt = to_huc6(alt_g)
    mask = (h_base + h_alt) > 1e-4
    apd = 100.0 * np.abs(h_alt[mask] - h_base[mask]) / (0.5 * (h_alt[mask] + h_base[mask]))
    r_val = float(np.corrcoef(h_base[mask], h_alt[mask])[0, 1])
    # Normalized total variation distance (100% * 1/2 * sum|p_alt - p_base|):
    # identical to 100% * 1/2 * sum|Alt - Base| / sum(Base) when mass is conserved,
    # and isolates pure spatial reallocation when total volume also shifts (Eq. 8 GW).
    vol_shift_huc6 = float(100.0 * 0.5 * np.abs(h_alt / h_alt.sum() - h_base / h_base.sum()).sum())
    vol_shift_cell = float(100.0 * 0.5 * np.abs(alt_g / alt_g.sum() - base_g / base_g.sum()).sum())
    spatial_rows.append(
        {
            "label": label,
            "sector": sector,
            "category": category,
            "n_huc6": int(mask.sum()),
            "huc6_r": round(r_val, 3),
            "huc6_q25_pct": round(float(np.percentile(apd, 25)), 1),
            "huc6_mdapd_pct": round(float(np.median(apd)), 1),
            "huc6_q75_pct": round(float(np.percentile(apd, 75)), 1),
            "conus_vol_shifted_huc6_pct": round(vol_shift_huc6, 1),
            "conus_vol_shifted_cell_pct": round(vol_shift_cell, 1),
        }
    )

df_spatial = pd.DataFrame(spatial_rows).sort_values("huc6_mdapd_pct", ascending=True).reset_index(
    drop=True
)

# =============================================================================
# PART 2: TEMPORAL-WEIGHT SENSITIVITY OVER 2010-2019 (EQS. 4-7)
# =============================================================================
with xr.open_dataset(HIST_IN / "Tavg_HDD_CDD_Historical_2010_2019.nc") as ds_met_raw:
    ds_met = ds_met_raw.sel(lat=LAT, lon=LON, method="nearest")
    Tavg = np.nan_to_num(ds_met["Tavg"].sel(year=slice(2010, 2019)).values, nan=0.0)
    HDD = np.nan_to_num(ds_met["HDD"].sel(year=slice(2010, 2019)).values, nan=0.0)
    CDD = np.nan_to_num(ds_met["CDD"].sel(year=slice(2010, 2019)).values, nan=0.0)

pub_monthly = {}
ann_cell = {}
w_irr_pub = None
for sec in ["Domestic", "Electricity", "Irrigation"]:
    with xr.open_dataset(HIST_OUT / f"{sec}_withdrawals_monthly.nc") as ds_m:
        arr = sum(ds_m[v].sel(year=slice(2010, 2019)).fillna(0.0).values for v in ds_m.data_vars)
        dims = ds_m[list(ds_m.data_vars)[0]].dims
    arr = np.transpose(arr, [dims.index(d) for d in ("year", "month", "lat", "lon")])
    pub_monthly[sec] = 100.0 * arr.sum(axis=(0, 2, 3)) / arr.sum()
    ann_cell[sec] = arr.sum(axis=1)
    if sec == "Irrigation":
        irr_ann_4d = arr.sum(axis=1, keepdims=True)
        w_irr_pub = np.where(irr_ann_4d > 0, arr / np.where(irr_ann_4d > 0, irr_ann_4d, 1.0), 0.0)

usgs_monthly = {}
for sec in ["Domestic", "Electricity", "Irrigation"]:
    df_u = pd.read_csv(VAL_DATA / f"huc06-{sec}-withdrawals-usgs-tethys.csv")
    df_u["dt"] = pd.to_datetime(df_u["datetime"])
    df_u = df_u[(df_u["dt"].dt.year >= 2010) & (df_u["dt"].dt.year <= 2019)]
    m_vol = df_u.groupby("month")["usgs_km3"].sum().reindex(range(1, 13)).values
    usgs_monthly[sec] = 100.0 * m_vol / m_vol.sum()

# Irrigation (Eq. 4) alternatives: GSI-only (no P deficit) and Temperature-only max(T, 0)
doy_mid = np.array([15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349], dtype=float)
radlat = LAT[:, None] * np.pi / 180.0
decl = 23.45 * np.pi / 180.0 * np.cos(2.0 * np.pi * (doy_mid[None, :] - 172.0) / 365.0)
a_ang = -0.833 * np.pi / 180.0
cos_ha = np.clip(
    (np.sin(a_ang) - np.sin(radlat) * np.sin(decl)) / (np.cos(radlat) * np.cos(decl)), -1.0, 1.0
)
daylen = 2.0 * np.arccos(cos_ha) * 180.0 / (15.0 * np.pi)
iPhoto = np.clip(daylen - 10.0, 0.0, 1.0).T[None, :, :, None]


def norm_weighted_monthly(w_raw: np.ndarray, cell_ann: np.ndarray) -> np.ndarray:
    ws = w_raw.sum(axis=1, keepdims=True)
    wn = np.where(ws > 0, w_raw / np.where(ws > 0, ws, 1.0), 1.0 / 12.0)
    vol = (wn * cell_ann[:, None, :, :]).sum(axis=(0, 2, 3))
    return 100.0 * vol / vol.sum()


irr_def = pub_monthly["Irrigation"]
irr_gsi_only = norm_weighted_monthly(
    np.clip((Tavg - 3.0) / 7.0, 0.0, 1.0) * iPhoto, ann_cell["Irrigation"]
)
irr_temp_only = norm_weighted_monthly(np.maximum(Tavg, 0.0), ann_cell["Irrigation"])

# Electricity (Eqs. 5-6): demand-weighted effective GCAM-USA shares + +/-50% thresholds + 2x p_cool
H_y = HDD.sum(axis=1, keepdims=True)
C_y = CDD.sum(axis=1, keepdims=True)
hdd_sh = HDD / (H_y + 1e-9)
cdd_sh = CDD / (C_y + 1e-9)
unif_m = np.full_like(hdd_sh, 1.0 / 12.0)


def elec_basis(h_thr: float, c_thr: float):
    c1 = (H_y >= h_thr) & (C_y >= c_thr)
    c2 = (H_y >= h_thr) & (C_y < c_thr)
    c3 = (H_y < h_thr) & (C_y >= c_thr)
    h_hat = np.where(c1 | c2, hdd_sh, np.where(c3, cdd_sh, unif_m))
    c_hat = np.where(c1 | c3, cdd_sh, np.where(c2, hdd_sh, unif_m))
    bh = 100.0 * (h_hat * ann_cell["Electricity"][:, None, :, :]).sum(axis=(0, 2, 3)) / ann_cell["Electricity"].sum()
    bc = 100.0 * (c_hat * ann_cell["Electricity"][:, None, :, :]).sum(axis=(0, 2, 3)) / ann_cell["Electricity"].sum()
    bo = np.full(12, 100.0 / 12.0)
    return bh, bc, bo


bh_def, bc_def, bo_def = elec_basis(650, 450)
X_el = np.column_stack([bh_def - bo_def, bc_def - bo_def])
p_hc, *_ = np.linalg.lstsq(X_el, pub_monthly["Electricity"] - bo_def, rcond=None)
p_heat_eff, p_cool_eff = float(p_hc[0]), float(p_hc[1])
p_other_eff = 1.0 - p_heat_eff - p_cool_eff

bh_low, bc_low, bo_low = elec_basis(325, 225)
bh_hi, bc_hi, bo_hi = elec_basis(975, 675)

elec_def = pub_monthly["Electricity"]
elec_thr_low = p_heat_eff * bh_low + p_cool_eff * bc_low + p_other_eff * bo_low
elec_thr_hi = p_heat_eff * bh_hi + p_cool_eff * bc_hi + p_other_eff * bo_hi
elec_2x_cool = p_heat_eff * bh_def + (2.0 * p_cool_eff) * bc_def + (1.0 - p_heat_eff - 2.0 * p_cool_eff) * bo_def

# Domestic / Municipal (Eq. 7): Wada R +/-50% and Uniform (R = 0)
with xr.open_dataset(HIST_IN / "DomesticR.nc") as ds_r:
    R_grid = np.nan_to_num(ds_r["amplitude"].sel(lat=LAT, lon=LON, method="nearest").values, nan=0.52)

T_mean = Tavg.mean(axis=1, keepdims=True)
T_span = np.maximum(Tavg.max(axis=1, keepdims=True) - Tavg.min(axis=1, keepdims=True), 1e-6)
T_norm = (Tavg - T_mean) / T_span


def dom_r_profile(mult: float) -> np.ndarray:
    w = np.clip((T_norm * (mult * R_grid[None, None, :, :]) + 1.0) / 12.0, 0.0, None)
    return norm_weighted_monthly(w, ann_cell["Domestic"])


dom_def = pub_monthly["Domestic"]
dom_low = dom_r_profile(0.5)
dom_hi = dom_r_profile(1.5)
dom_unif = np.full(12, 100.0 / 12.0)

months = np.arange(1, 13)
df_temporal = pd.DataFrame(
    {
        "month": months,
        "irrigation_default_pct": np.round(irr_def, 3),
        "irrigation_gsi_only_pct": np.round(irr_gsi_only, 3),
        "irrigation_temp_only_pct": np.round(irr_temp_only, 3),
        "irrigation_usgs_pct": np.round(usgs_monthly["Irrigation"], 3),
        "electricity_default_pct": np.round(elec_def, 3),
        "electricity_thr_minus50_pct": np.round(elec_thr_low, 3),
        "electricity_thr_plus50_pct": np.round(elec_thr_hi, 3),
        "electricity_2x_pcool_pct": np.round(elec_2x_cool, 3),
        "electricity_usgs_pct": np.round(usgs_monthly["Electricity"], 3),
        "domestic_default_pct": np.round(dom_def, 3),
        "domestic_r_minus50_pct": np.round(dom_low, 3),
        "domestic_r_plus50_pct": np.round(dom_hi, 3),
        "uniform_1_12_pct": np.round(dom_unif, 3),
        "domestic_usgs_pct": np.round(usgs_monthly["Domestic"], 3),
    }
)

for out_dir in (OUT_PAPER, OUT_LOCAL):
    df_spatial.to_csv(out_dir / "sensitivity-spatial-huc6.csv", index=False)
    df_temporal.to_csv(out_dir / "sensitivity-temporal-monthly.csv", index=False)

print("=== Spatial-proxy & source-share HUC6 sensitivity (2015) ===")
print(df_spatial.to_string(index=False))
print("\n=== Temporal monthly sensitivity max shifts (pp) ===")
print(
    f"  Irrigation GSI-only max |d|: {np.max(np.abs(irr_gsi_only - irr_def)):.2f} pp; "
    f"Temp-only max |d|: {np.max(np.abs(irr_temp_only - irr_def)):.2f} pp"
)
print(
    f"  Electricity Thr -50% max |d|: {np.max(np.abs(elec_thr_low - elec_def)):.2f} pp; "
    f"Thr +50% max |d|: {np.max(np.abs(elec_thr_hi - elec_def)):.2f} pp; "
    f"2x p_cool max |d|: {np.max(np.abs(elec_2x_cool - elec_def)):.2f} pp"
)
print(
    f"  Domestic -50% R max |d|: {np.max(np.abs(dom_low - dom_def)):.2f} pp; "
    f"+50% R max |d|: {np.max(np.abs(dom_hi - dom_def)):.2f} pp; "
    f"Uniform max |d|: {np.max(np.abs(dom_unif - dom_def)):.2f} pp"
)

# =============================================================================
# PART 3: COMPOSITE 4-PANEL PUBLICATION FIGURE (val6-multisector-sensitivity.png)
# =============================================================================
plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "Nimbus Sans", "DejaVu Sans"],
        "mathtext.fontset": "stixsans",
        "font.size": 9.5,
        "axes.labelsize": 10,
        "axes.titlesize": 10.5,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8.3,
    }
)

fig = plt.figure(figsize=(10.6, 7.8), facecolor="white")
gs_top = gridspec.GridSpec(1, 1, left=0.268, right=0.988, top=0.945, bottom=0.475)
gs_bot = gridspec.GridSpec(1, 3, left=0.052, right=0.988, top=0.355, bottom=0.072, wspace=0.14)

# --- Panel (a): Spatial-proxy & source-share sensitivity across all 6 sectors ---
ax_a = fig.add_subplot(gs_top[0, 0])
cat_styles = {
    "Epoch update": ("#2b6f6b", "o", "Proxy epoch update"),
    "Subsector pooling": ("#8c6d2c", "s", "Subsector pooling"),
    "Alternative proxy": ("#a8501c", "D", "Alternative spatial proxy"),
    "Source anchoring": ("#5c3d6e", "^", "GW source anchoring (Eq. 8)"),
}

y_pos = np.arange(len(df_spatial))
for i, row in df_spatial.iterrows():
    color, marker, _ = cat_styles[row["category"]]
    ax_a.plot(
        [row["huc6_q25_pct"], row["huc6_q75_pct"]],
        [i, i],
        color=color,
        linewidth=2.2,
        alpha=0.82,
        solid_capstyle="round",
        zorder=2,
    )
    ax_a.plot(
        row["huc6_mdapd_pct"],
        i,
        marker=marker,
        color=color,
        markersize=6.2,
        markeredgecolor="white",
        markeredgewidth=0.6,
        zorder=3,
    )
    ax_a.text(
        221.0,
        i,
        f"{row['conus_vol_shifted_huc6_pct']:4.1f}%",
        va="center",
        ha="right",
        fontsize=8.6,
        color="#333333",
    )

ax_a.text(
    221.0,
    -0.85,
    "HUC6 share shifted",
    va="bottom",
    ha="right",
    fontsize=8.3,
    fontweight="bold",
    color="#333333",
)

ax_a.set_yticks(y_pos)
ax_a.set_yticklabels(df_spatial["label"])
ax_a.invert_yaxis()
ax_a.set_xlim(-3, 224)
ax_a.set_xticks([0, 25, 50, 75, 100, 125, 150, 175, 200])
ax_a.axvline(200, color="#cccccc", linestyle=":", linewidth=0.8, zorder=1)
ax_a.set_xlabel(
    "HUC6 basin symmetric absolute percent difference, median and interquartile range (%)"
)
ax_a.set_title(
    "(a) Spatial-proxy (Eq. 3) and source-share (Eq. 8) sensitivity across HUC6 basins (2015)",
    loc="left",
    fontweight="bold",
    pad=16,
)
ax_a.grid(axis="x", color="#e6e6e6", linewidth=0.7, zorder=0)
ax_a.spines["top"].set_visible(False)
ax_a.spines["right"].set_visible(False)
for sp in ("left", "bottom"):
    ax_a.spines[sp].set_edgecolor("#404040")
    ax_a.spines[sp].set_linewidth(0.8)

legend_handles_a = [
    mlines.Line2D(
        [],
        [],
        color=col,
        marker=mk,
        linestyle="-",
        linewidth=2.0,
        markersize=6,
        label=lbl,
    )
    for col, mk, lbl in cat_styles.values()
]
ax_a.legend(
    handles=legend_handles_a,
    loc="upper right",
    bbox_to_anchor=(0.86, 0.99),
    frameon=True,
    facecolor="white",
    edgecolor="#d8d8d8",
    ncol=1,
)

# --- Shared helper for bottom-row monthly temporal sensitivity panels (b)-(d) ---
month_labels = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]


def style_monthly_ax(ax, title_str, show_ylabel=False):
    ax.set_title(title_str, loc="left", fontweight="bold", pad=6)
    ax.set_xlabel("Month")
    if show_ylabel:
        ax.set_ylabel("Share of annual withdrawals (%)")
    ax.set_xticks(months)
    ax.set_xticklabels(month_labels)
    ax.set_xlim(0.6, 12.4)
    ax.grid(True, color="#e6e6e6", linewidth=0.7, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_edgecolor("#404040")
        ax.spines[sp].set_linewidth(0.8)


# --- Panel (b): Irrigation temporal sensitivity (Eq. 4) ---
ax_b = fig.add_subplot(gs_bot[0, 0])
ax_b.plot(
    months,
    irr_def,
    color="#222222",
    linestyle="-",
    marker="s",
    markersize=4.2,
    linewidth=1.6,
    label="Default (Deficit × GSI)",
    zorder=4,
)
ax_b.plot(
    months,
    irr_gsi_only,
    color="#2b6f6b",
    linestyle="-.",
    marker="^",
    markersize=4.4,
    linewidth=1.4,
    label="GSI-only (no deficit)",
    zorder=3,
)
ax_b.plot(
    months,
    irr_temp_only,
    color="#8c6d2c",
    linestyle=":",
    marker="D",
    markersize=3.8,
    linewidth=1.5,
    label="Temp.-only ($T > 0\\,^\\circ\\mathrm{C}$)",
    zorder=3,
)
ax_b.plot(
    months,
    usgs_monthly["Irrigation"],
    color="#d55e00",
    linestyle="--",
    marker="o",
    markerfacecolor="white",
    markersize=4.4,
    linewidth=1.5,
    label="USGS (2010–2019)",
    zorder=5,
)
ax_b.set_ylim(-0.8, 38.5)
style_monthly_ax(ax_b, "(b) Irrigation (Eq. 4)", show_ylabel=True)
ax_b.legend(
    loc="upper left",
    fontsize=7.9,
    labelspacing=0.28,
    borderpad=0.35,
    frameon=True,
    facecolor="white",
    edgecolor="#e0e0e0",
)

# --- Panel (c): Electricity temporal sensitivity (Eqs. 5-6) ---
ax_c = fig.add_subplot(gs_bot[0, 1])
ax_c.fill_between(
    months,
    np.minimum(elec_thr_low, elec_thr_hi),
    np.maximum(elec_thr_low, elec_thr_hi),
    color="#2b6f6b",
    alpha=0.22,
    zorder=2,
)
ax_c.plot(
    months,
    elec_thr_low,
    color="#2b6f6b",
    linestyle="-.",
    linewidth=1.2,
    label="HDD/CDD thr. $\\pm 50\\%$",
    zorder=3,
)
ax_c.plot(months, elec_thr_hi, color="#2b6f6b", linestyle="-.", linewidth=1.2, zorder=3)
ax_c.plot(
    months,
    elec_def,
    color="#222222",
    linestyle="-",
    marker="s",
    markersize=4.2,
    linewidth=1.6,
    label="Default (650, 450)",
    zorder=4,
)
ax_c.plot(
    months,
    elec_2x_cool,
    color="#8c6d2c",
    linestyle=":",
    marker="^",
    markersize=4.4,
    linewidth=1.5,
    label="$2\\times$ cooling share ($p_{\\mathrm{cool}}$)",
    zorder=3,
)
ax_c.plot(
    months,
    usgs_monthly["Electricity"],
    color="#d55e00",
    linestyle="--",
    marker="o",
    markerfacecolor="white",
    markersize=4.4,
    linewidth=1.5,
    label="USGS (2010–2019)",
    zorder=5,
)
ax_c.set_ylim(6.0, 13.8)
style_monthly_ax(ax_c, "(c) Electricity (Eqs. 5–6)", show_ylabel=False)
ax_c.legend(
    loc="upper left",
    fontsize=7.9,
    labelspacing=0.28,
    borderpad=0.35,
    frameon=True,
    facecolor="white",
    edgecolor="#e0e0e0",
)

# --- Panel (d): Domestic / Municipal & uniform sectors temporal sensitivity (Eq. 7) ---
ax_d = fig.add_subplot(gs_bot[0, 2])
ax_d.fill_between(
    months,
    dom_low,
    dom_hi,
    color="#2b6f6b",
    alpha=0.20,
    zorder=2,
)
ax_d.plot(
    months,
    dom_low,
    color="#2b6f6b",
    linestyle="-.",
    linewidth=1.2,
    label="Wada $R \\pm 50\\%$",
    zorder=3,
)
ax_d.plot(months, dom_hi, color="#2b6f6b", linestyle="-.", linewidth=1.2, zorder=3)
ax_d.plot(
    months,
    dom_def,
    color="#222222",
    linestyle="-",
    marker="s",
    markersize=4.2,
    linewidth=1.6,
    label="Default Wada $R$",
    zorder=4,
)
ax_d.plot(
    months,
    dom_unif,
    color="#7a7a7a",
    linestyle=(0, (5, 2)),
    linewidth=1.2,
    label="Uniform 1/12 (Mfg./Min./Liv.)",
    zorder=2,
)
ax_d.plot(
    months,
    usgs_monthly["Domestic"],
    color="#d55e00",
    linestyle="--",
    marker="o",
    markerfacecolor="white",
    markersize=4.4,
    linewidth=1.5,
    label="USGS (2010–2019)",
    zorder=5,
)
ax_d.set_ylim(4.8, 14.6)
style_monthly_ax(ax_d, "(d) Domestic & uniform (Eq. 7)", show_ylabel=False)
ax_d.legend(
    loc="upper left",
    fontsize=7.9,
    labelspacing=0.28,
    borderpad=0.35,
    frameon=True,
    facecolor="white",
    edgecolor="#e0e0e0",
)

for out_dir in (OUT_PAPER, OUT_LOCAL):
    out_png = out_dir / "val6-multisector-sensitivity.png"
    fig.savefig(out_png, dpi=300, bbox_inches="tight", pad_inches=0.08, facecolor="white")
    print(f"Wrote {out_png}")
plt.close(fig)
