import xarray as xr
import geopandas as gpd
import xagg as xa
import pandas as pd
import os

path = "/Volumes/data/tethys/output/historical/"
output_path = "data"
# demand_type = "withdrawals"
# demand_category = "Irrigation"
hucs_to_compute = [2, 4, 6, 8]
demand_categories = [
    "Irrigation",
    "Electricity",
    "Domestic",
    "Livestock",
    "Manufacturing",
    "Mining",
]
# demand_type = "consumption"
for demand_type in ["withdrawals", "consumption"]:
    print(demand_type)
    demand_list = []
    for demand_category in demand_categories:
        # for demand_category in ['Domestic']:
        print(demand_category)

        if demand_category == "Irrigation":
            loss_postfix = "_with_losses"
        else:
            loss_postfix = ""

        fn = f"{path}/{demand_category}_{demand_type}{loss_postfix}.nc"
        print(fn)
        tethys = xr.open_dataset(fn)
        # demand might have different components, sum them all together
        demand = (
            tethys.load()
            .to_array()
            .sum("variable")
            .to_dataset(name=demand_category)
            .mean(dim="year")
        )
        demand_list.append(demand)
        tethys.close()
    demand_by_sector = xr.combine_by_coords(demand_list)

    da = demand_by_sector.to_array("sector")

    # Argmax across sectors
    max_idx = da.argmax(dim="sector")

    # Mask cells where all sectors are NaN (avoid meaningless argmax=0)
    valid = da != 0
    # max_idx = max_idx.where(valid)

    # Sector labels (in the same order used by argmax)
    labels_da = xr.DataArray(
        da["sector"].values,
        dims=("sector",),
        # coords={"sector": da["sector"].values}
    )

    # Vectorized indexing: pick sector name at each cell
    name_da = labels_da.isel(sector=max_idx).where(valid).rename("max_sector")
    name_da.to_pandas().to_csv(
        f"data/tethys_{demand_type}_dominant_sector_by_grid_cell.csv"
    )
