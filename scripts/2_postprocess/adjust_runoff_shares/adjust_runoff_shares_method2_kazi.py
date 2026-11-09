#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adjust GCAM basin renewable/non-renewable shares against USGS (method 2).

Rebuilds the adjusted output tree from the raw Tethys output, then rewrites
gridded_runoff_shares.nc per scenario using the static USGS baseline and
writes a per-scenario diagnostic PNG. Canonical producer of the tree named
output_adjusted_usgs_method2.

The rebuild deletes --method2-root and re-copies --orig-root over it, which
is tens of GB on the full scenario set, so an existing tree requires --force.

Paths default to scripts/3_config/paths.yml under $TETHYS_ENV (pnl_rcfs
unless set). Code and bulk output live in different directories on
deception; see the pnl_rcfs block there.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import xarray as xr
import yaml
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --------------------------------------------------
# PATHS
# --------------------------------------------------
# Resolved from scripts/3_config/paths.yml, keyed by $TETHYS_ENV
# (default pnl_rcfs). Override any of the three on the command line.
PATHS_YML = Path(__file__).resolve().parents[2] / "3_config" / "paths.yml"


def resolve_paths():
    env = os.environ.get("TETHYS_ENV", "pnl_rcfs")
    try:
        cfg = yaml.safe_load(PATHS_YML.read_text())["environments"][env]
    except KeyError:
        sys.exit(f"error: no '{env}' environment in {PATHS_YML}")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--orig-root", default=cfg.get("tethys_raw_output"),
                    help="raw Tethys output tree, read-only")
    ap.add_argument("--method2-root", default=cfg.get("tethys_canonical_output"),
                    help="adjusted tree; REBUILT FROM SCRATCH, see --force")
    ap.add_argument("--usgs-baseline", default=cfg.get("usgs_baseline"))
    ap.add_argument("--force", action="store_true",
                    help="allow deleting an existing --method2-root")
    args = ap.parse_args()

    missing = [k for k in ("orig_root", "method2_root", "usgs_baseline")
               if not getattr(args, k)]
    if missing:
        sys.exit(f"error: {env} in {PATHS_YML} defines no " + ", ".join(missing))
    return args


args = resolve_paths()
ORIG_ROOT = args.orig_root
METHOD2_ROOT = args.method2_root
USGS_BASELINE_FILE = args.usgs_baseline

for label, path in (("--orig-root", ORIG_ROOT), ("--usgs-baseline", USGS_BASELINE_FILE)):
    if not os.path.exists(path):
        sys.exit(f"error: {label} does not exist: {path}")

print(f"raw output:    {ORIG_ROOT}")
print(f"adjusted tree: {METHOD2_ROOT}")
print(f"usgs baseline: {USGS_BASELINE_FILE}\n")

# --------------------------------------------------
# REBUILD METHOD2 FOLDER (DETERMINISTIC)
# --------------------------------------------------
# The rebuild deletes METHOD2_ROOT outright and re-copies ORIG_ROOT over it,
# which is tens of GB on the full scenario set. --force is the guard.
if os.path.exists(METHOD2_ROOT):
    if not args.force:
        sys.exit(
            f"error: {METHOD2_ROOT} already exists.\n"
            "       This script deletes it and re-copies the raw tree over it.\n"
            "       Pass --force if that is what you want."
        )
    print("Removing existing _method2 folder...")
    shutil.rmtree(METHOD2_ROOT)

print("Copying raw output -> _method2 ...")
shutil.copytree(ORIG_ROOT, METHOD2_ROOT)

print("Copy complete.\n")

# --------------------------------------------------
# LOAD STATIC USGS BASELINE
# --------------------------------------------------
ds_usgs = xr.open_dataset(USGS_BASELINE_FILE)
usgs_base = ds_usgs["share"].values.astype(np.float32)
usgs_valid = np.isfinite(usgs_base)
ds_usgs.close()

# --------------------------------------------------
# LOAD COMMON DENOMINATOR (HISTORICAL 2015 FROM CLEAN COPY)
# --------------------------------------------------
hist_file = os.path.join(
    METHOD2_ROOT,
    "historical",
    "gridded_runoff_shares.nc"
)

ds_hist = xr.open_dataset(hist_file)
hist_2015 = ds_hist["share"].sel(year=2015).values.astype(np.float32)
ds_hist.close()

denom_mask = (
    (hist_2015 > 0.0) &
    usgs_valid &
    np.isfinite(hist_2015)
)

denom = np.zeros_like(hist_2015, dtype=np.float32)
denom[denom_mask] = hist_2015[denom_mask]

# --------------------------------------------------
# LOOP OVER SCENARIOS IN _method2
# --------------------------------------------------
for scen in sorted(os.listdir(METHOD2_ROOT)):

    scen_dir = os.path.join(METHOD2_ROOT, scen)
    if not os.path.isdir(scen_dir):
        continue

    gcam_nc = os.path.join(scen_dir, "gridded_runoff_shares.nc")
    if not os.path.exists(gcam_nc):
        continue

    print("Processing scenario:", scen)

    ds = xr.open_dataset(gcam_nc)
    gcam = ds["share"]

    years = gcam.year.values
    lat = gcam.lat.values
    lon = gcam.lon.values

    out = np.zeros_like(gcam.values, dtype=np.float32)

    # --------------------------------------------------
    # YEAR LOOP
    # --------------------------------------------------
    for i, yr in enumerate(years):

        gy = gcam.sel(year=yr).values.astype(np.float32)

        out[i] = gy  # preserve original everywhere

        ratio = np.ones_like(gy, dtype=np.float32)
        ratio[denom_mask] = gy[denom_mask] / denom[denom_mask]

        adj = usgs_base * ratio
        out[i][denom_mask] = np.clip(adj[denom_mask], 0.0, 1.0)

    # --------------------------------------------------
    # SAFE WRITE
    # --------------------------------------------------
    temp_file = gcam_nc + ".tmp"

    out_ds = ds.copy(deep=True)
    out_ds["share"].values = out.astype(out_ds["share"].dtype)

    ds.close()

    out_ds.to_netcdf(temp_file)
    os.replace(temp_file, gcam_nc)

    print("  Overwritten safely:", gcam_nc)

    # --------------------------------------------------
    # DIAGNOSTIC PLOT
    # --------------------------------------------------
    ny = len(years)

    fig, axes = plt.subplots(
        ny, 3,
        figsize=(12, 3 * ny),
        constrained_layout=True
    )

    if ny == 1:
        axes = axes[np.newaxis, :]

    for i, yr in enumerate(years):

        im0 = axes[i, 0].pcolormesh(
            lon, lat, gcam.sel(year=yr),
            vmin=0.0, vmax=1.0, shading="nearest"
        )
        axes[i, 0].set_title(f"Original ({yr})")

        axes[i, 1].pcolormesh(
            lon, lat, usgs_base,
            vmin=0.0, vmax=1.0, shading="nearest"
        )
        axes[i, 1].set_title("USGS baseline")

        axes[i, 2].pcolormesh(
            lon, lat, out[i],
            vmin=0.0, vmax=1.0, shading="nearest"
        )
        axes[i, 2].set_title("Adjusted")

        for j in range(3):
            axes[i, j].set_xticks([])
            axes[i, j].set_yticks([])

    cbar = fig.colorbar(im0, ax=axes, shrink=0.7)
    cbar.set_label("Runoff share")

    fig.suptitle(
        f"USGS adjustment using historical 2015 denominator\nScenario: {scen}",
        fontsize=14
    )

    plot_png = os.path.join(scen_dir, "usgs_adjustment_diagnostic.png")
    plt.savefig(plot_png, dpi=200)
    plt.close()

    print("  Saved:", plot_png)

print("\nAll scenarios processed deterministically.")
