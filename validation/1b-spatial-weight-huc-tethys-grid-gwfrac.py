import xarray as xr
import xagg as xa
import geopandas as gpd

path = "/Volumes/data/tethys/output/historical/"
output_path = "data"
# demand_type = "withdrawals"
# demand_category = "Irrigation"
hucs_to_compute = [2, 4, 6, 8]

fn = f"{path}/gridded_runoff_shares.nc"
print(fn)
runoff_share = xr.open_dataset(fn)


for h in hucs_to_compute:
    print("HUC", h)
    gdf = gpd.read_file(f"/Volumes/data/shapefiles/HUC{h}/HUC{h}.shp")

    # Get overlap between pixels and polygons
    weightmap = xa.pixel_overlaps(runoff_share, gdf)

    # Aggregate data in [ds] onto polygons
    aggregated = xa.aggregate(runoff_share, weightmap)

    out_csv = f"{output_path}/tethys_runoff_share_huc{h}.csv"
    aggregated.to_csv(out_csv)
