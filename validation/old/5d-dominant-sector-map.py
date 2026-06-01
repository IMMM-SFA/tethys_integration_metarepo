"""
Render the dominant water-use sector at each 1/8 deg cell across CONUS for the
Tethys data paper. This is the flagship figure: it summarises the multi-sector
spatial structure of demand the dataset captures.

Inputs (canonical recent output):
  /Volumes/data/tethys/output_adjusted_usgs_method2/historical/<Sector>_consumption.nc

Output:
  ../../tethys-data-paper/usage1-dominant-sector-tethys-grid.png
  ../../tethys-data-paper/figures/dominant-sector-tethys-grid.csv (raw label grid)

The previous version of the figure is preserved at
  ../../tethys-data-paper/usage1-dominant-sector-tethys-grid_v3rollback.png
"""

# %% setup
from pathlib import Path

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
TETHYS_BASE = Path("/Volumes/data/tethys/output_adjusted_usgs_method2/historical")
PAPER_DIR = HERE.parent.parent / "tethys-data-paper"
FIG_DIR = PAPER_DIR / "figures"
FIG_DIR.mkdir(exist_ok=True, parents=True)

OUT_PNG = PAPER_DIR / "usage1-dominant-sector-tethys-grid.png"
OUT_CSV = FIG_DIR / "dominant-sector-tethys-grid.csv"

SECTORS = ["Domestic", "Electricity", "Irrigation", "Livestock", "Manufacturing", "Mining"]

# Okabe-Ito colorblind-safe palette, matching the prior published figure.
# Wong (2011) Nature Methods 8:441; perceptually distinct under deuteranopia,
# protanopia, and tritanopia.
PALETTE = {
    "Domestic":      "#0072b2",  # blue
    "Electricity":   "#d55e00",  # vermillion
    "Irrigation":    "#009e73",  # bluish green
    "Livestock":     "#e69f00",  # orange
    "Manufacturing": "#cc79a7",  # reddish purple
    "Mining":        "#56b4e9",  # sky blue
}


# %% load mean annual consumption by sector
demand_layers = {}
for sector in SECTORS:
    if sector == "Irrigation":
        fn = TETHYS_BASE / f"{sector}_consumption_with_losses.nc"
        if not fn.exists():
            fn = TETHYS_BASE / f"{sector}_consumption.nc"
    else:
        fn = TETHYS_BASE / f"{sector}_consumption.nc"
    print(f"Reading {fn}")
    ds = xr.open_dataset(fn).load()
    # sum sub-variables (e.g., crop classes for irrigation), then average across years
    demand = ds.to_array().sum("variable").mean(dim="year")
    demand_layers[sector] = demand
    ds.close()

# stack sectors into one (sector, lat, lon) DataArray
da = xr.concat(
    [d.expand_dims(sector=[s]) for s, d in demand_layers.items()],
    dim="sector",
)

# %% argmax
max_idx = da.argmax(dim="sector")
valid = (da.sum(dim="sector") > 0)
sector_labels = list(da["sector"].values)

# numeric grid for plotting; -1 where invalid
grid = max_idx.where(valid).fillna(-1).astype(int)

# %% plot
fig, ax = plt.subplots(figsize=(11, 6), facecolor="white")
ax.set_facecolor("white")
n = len(sector_labels)
# White (not grey) for invalid/no-demand cells, then the Okabe-Ito sector hues.
cmap_colors = ["white"] + [PALETTE[s] for s in sector_labels]
cmap = colors.ListedColormap(cmap_colors)
boundaries = np.arange(-1.5, n + 0.5)
norm = colors.BoundaryNorm(boundaries, cmap.N)

lon = grid["lon"].values
lat = grid["lat"].values
extent = [lon.min(), lon.max(), lat.min(), lat.max()]
img = ax.imshow(
    grid.values, origin="upper", extent=extent, cmap=cmap, norm=norm,
    interpolation="nearest",
)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect(1 / np.cos(np.deg2rad(np.mean(lat))))

# Legend
handles = [Patch(facecolor=PALETTE[s], edgecolor="white", label=s) for s in sector_labels]
ax.legend(
    handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.18),
    ncol=len(sector_labels), frameon=False,
)

ax.set_title(
    "Dominant water-use sector at each 1/8 deg cell, by annual-average consumption",
    fontsize=11,
)
for spine in ax.spines.values():
    spine.set_visible(False)
fig.tight_layout()
fig.savefig(OUT_PNG, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Wrote {OUT_PNG}")

# also write a CSV of the labelled grid
out = grid.where(grid >= 0).to_pandas()
out.to_csv(OUT_CSV)
print(f"Wrote {OUT_CSV}")
