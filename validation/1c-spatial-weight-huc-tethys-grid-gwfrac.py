# Spatially weight the Tethys 1/8-degree grid to HUC polygons while
# preserving the groundwater-vs-surface-water fraction from
# gridded_runoff_shares.nc. Sibling to 1-postprocess-tethys.py, but
# computes HUC-level GW/SW splits instead of total demand.
# (Formerly 1b-spatial-weight-huc-tethys-grid-gwfrac.py; renamed to 1c
#  so 1b unambiguously refers to the prior-version comparison.)

import xarray as xr
import xagg as xa
import geopandas as gpd
import yaml

P = yaml.safe_load(open("paths.yml"))

path = f"{P['tethys_output_raw']}/historical/"
output_path = P["data_dir"]
# demand_type = "withdrawals"
# demand_category = "Irrigation"
hucs_to_compute = [2, 4, 6, 8]

fn = f"{path}/gridded_runoff_shares.nc"
print(fn)
runoff_share = xr.open_dataset(fn)


for h in hucs_to_compute:
    print("HUC", h)
    gdf = gpd.read_file(P[f"huc{h}_shapefile"])

    # Get overlap between pixels and polygons
    weightmap = xa.pixel_overlaps(runoff_share, gdf)

    # Aggregate data in [ds] onto polygons
    aggregated = xa.aggregate(runoff_share, weightmap)

    out_csv = f"{output_path}/tethys_runoff_share_huc{h}.csv"
    aggregated.to_csv(out_csv)
