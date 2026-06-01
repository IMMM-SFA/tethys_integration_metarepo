# %%
import xarray as xr
import geopandas as gpd
import xagg as xa
import pandas as pd
import os

# %%
scenarios = [
    "rcp45cooler_ssp3",
    "rcp45cooler_ssp5",
    "rcp45hotter_ssp3",
    "rcp45hotter_ssp5",
    "rcp85cooler_ssp3",
    "rcp85cooler_ssp5",
    "rcp85hotter_ssp3",
    "rcp85hotter_ssp5",
    "historical",
]
path = "/Volumes/data/tethys/output/"
output_path = "data"
hucs_to_compute = [2, 4, 6, 8]
demand_categories = [
    "Irrigation",
    "Electricity",
    "Domestic",
    "Livestock",
    "Manufacturing",
    "Mining",
]

# demand_type = "withdrawals"
# demand_category = "Irrigation"

##########################################################################
# spatially weight the Tethys grid to HUC basins
##########################################################################
# %%
for scenario in scenarios:
    print(scenario)
    for demand_category in demand_categories:
        # for demand_category in ['Domestic']:
        print("\t", demand_category)
        for demand_type in ["withdrawals", "consumption"]:
            print("\t", demand_type)

            if demand_category == "Irrigation":
                loss_postfix = "_with_losses"
            else:
                loss_postfix = ""

            fn = f"{path}/{scenario}/{demand_category}_{demand_type}_monthly{loss_postfix}.nc"
            print(fn)
            tethys = xr.open_dataset(fn)
            # demand might have different components, sum them all together
            demand = tethys.load().to_array().sum("variable").to_dataset(name="demand")
            # pull out a single year
            demand_year = demand.where(demand.year == demand.year[0]).sum(
                ["month", "year"]
            )

            for h in hucs_to_compute:
                print(f"Computing pixel overlaps with huc boundaries for HUC{h}")
                # h = 6
                pix_area_fn = f"data/pixel_area_proportion_{demand_category}_huc{h}.csv"
                # skip the creation of the pixel overlap proportion if the file exists
                if os.path.isfile(pix_area_fn):
                    continue

                huc_shape = gpd.read_file(f"/Volumes/data/shapefiles/HUC{h}/HUC{h}.shp")
                # force the HUC to be a string to keep the leading zero
                huc_shape["huc"] = huc_shape[f"huc{h}"].astype("|S").astype(str)

                # create polygons out of raster pixels for one year
                pix_agg = xa.core.create_raster_polygons(demand_year)

                # reproject to the same crs, this one is good for north america
                # https://github.com/ks905383/xagg/blob/90b060e297f44b19455af9e7c491f35e42ee31a3/xagg/core.py#L471
                crs = "EPSG:6931"
                pix_agg_prj = pix_agg["gdf_pixels"].to_crs(crs)
                # area of each pixel
                pix_agg_prj["pix_area"] = pix_agg_prj.area
                # compute the overalpping region of each pixel with the huc
                overlaps = gpd.overlay(
                    huc_shape.to_crs(crs), pix_agg_prj, how="intersection"
                )
                # find the proportion of the area of the pixel that overlaps the huc
                overlaps["pix_area_prop"] = overlaps.area / overlaps.pix_area
                overlaps[["lon", "lat", "huc", "pix_area_prop"]].to_csv(
                    f"{output_path}/pixel_area_proportion_{demand_category}_huc{h}.csv"
                )

            for h in hucs_to_compute:
                print(f"Aggregating demand for HUC{h}")
                pix_area_fn = (
                    f"{output_path}/pixel_area_proportion_{demand_category}_huc{h}.csv"
                )
                overlaps = pd.read_csv(pix_area_fn, dtype={"huc": "str"})
                # join the pixel area proportion with the demand data
                demand_with_overlap = pd.merge(
                    demand.to_dataframe().reset_index(["month", "year"]),
                    overlaps.set_index(["lon", "lat"]),
                    left_on=["lon", "lat"],
                    right_on=["lon", "lat"],
                )
                # compute the weighted sum of the demand for each huc by year and month
                demand_with_overlap["weighted_demand"] = (
                    demand_with_overlap.demand * demand_with_overlap.pix_area_prop
                )
                weighted_sum_demand = pd.DataFrame(
                    demand_with_overlap.groupby(["huc", "year", "month"])
                    .sum("weighted_demand")["weighted_demand"]
                    .rename("demand_km3")
                )
                # weighted_sum_demand.rename("demand_km3",axis=1,inplace=True)
                weighted_sum_demand["demand_mgd"] = (
                    weighted_sum_demand.demand_km3 * 264172.05 / (365 / 12)
                )
                # write out aggregated demand
                out_csv = f"{output_path}/tethys_{demand_category}_{demand_type}_huc{h}_{scenario}.csv"
                weighted_sum_demand.to_csv(out_csv)


# %%
##########################################################################
# Determine the dominant sector by grid cell
##########################################################################
for scenario in scenarios:
    print(scenario)
    for demand_type in ["withdrawals", "consumption"]:
        print("\t", demand_type)
        demand_list = []
        for demand_category in demand_categories:
            # for demand_category in ['Domestic']:
            # print(demand_category)

            if demand_category == "Irrigation":
                loss_postfix = "_with_losses"
            else:
                loss_postfix = ""

            fn = f"{path}/{scenario}/{demand_category}_{demand_type}{loss_postfix}.nc"
            # print(fn)
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

        demand_by_sector.to_dataframe().to_csv(
            f"data/tethys_dominant_sector_grid_{demand_type}_{scenario}.csv"
        )
