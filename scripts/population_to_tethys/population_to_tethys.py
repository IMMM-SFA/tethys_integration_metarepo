# Example call to use this script in terminal:
# python /Users/d3y010/projects/im3/population_to_tethys/population_to_tethys.py \
#     --global_dir <original Tethys population data directory> \
#     --local_dir <root directory holding the US state level gridded population data> \
#     --mosaic_dir <directory to save mosaic outputs to> \
#     --output_dir <directory to write the modified new outputs to> \
#     --percent_area_file <full path to percent_grid.shp> \
#     --ssp_list SSP3 SSP5 \
#     --year_list 2020 2030 2040 2050 2060 2070 2080 2090 2100

import argparse
import os
import glob
import logging
from typing import List

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.warp import calculate_default_transform, reproject, Resampling


# set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def mosaic_geotiffs(
    raster_list: List[str], 
    output_file: str
):
    """
    Create a mosaic from a list of GeoTIFF files and save it to an output file.

    This function takes a list of file paths to GeoTIFF files, merges them into 
    a single mosaic, and writes the resulting mosaic to the specified output file.

    :param raster_list: List of file paths to the GeoTIFF files to be merged.
    :type raster_list: List[str]
    :param output_file: Path to the output GeoTIFF file.
    :type output_file: str
    """
    src_files_to_mosaic = [rasterio.open(fp) for fp in raster_list]

    mosaic, out_trans = merge(src_files_to_mosaic)

    out_meta = src_files_to_mosaic[0].meta.copy()

    out_meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_trans
    })

    with rasterio.open(output_file, "w", **out_meta) as dest:
        dest.write(mosaic)

    # close all open files
    for src in src_files_to_mosaic:
        src.close()


def reproject_geotiff(
    input_file: str, 
    output_file: str, 
    target_crs='EPSG:4623'
):
    """
    Reproject a GeoTIFF file to a target coordinate reference system (CRS).

    This function reads an input GeoTIFF file, reprojects it to the specified 
    target CRS, and writes the reprojected data to an output file.

    :param input_file: Path to the input GeoTIFF file.
    :type input_file: str
    :param output_file: Path to the output GeoTIFF file.
    :type output_file: str
    :param target_crs: The target coordinate reference system in EPSG code format.
                       Default is 'EPSG:4623'.
    :type target_crs: str
    """
    with rasterio.open(input_file) as src:

        # calculate the transform and dimensions for the output file
        transform, width, height = calculate_default_transform(
            src.crs, 
            target_crs, 
            src.width, 
            src.height, 
            *src.bounds
        )

        # update the metadata with the new CRS, transform, and dimensions
        out_meta = src.meta.copy()
        out_meta.update({
            'crs': target_crs,
            'transform': transform,
            'width': width,
            'height': height
        })

        # open the output file and perform the reprojection
        with rasterio.open(output_file, 'w', **out_meta) as dest:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dest, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.sum
                )


def rescale_raster_to_match(
    input_raster: str, 
    reference_raster: str, 
    output_raster: str, 
    nodata_value: int = 0
):
    """
    Rescale an input raster to match the resolution and dimensions of a reference raster.

    This function reads an input raster file and rescales it to match the resolution,
    dimensions, and coordinate reference system (CRS) of a reference raster file. The
    rescaled raster is then saved to an output file. Nodata values in the input raster
    can be replaced with a specified nodata value in the output raster.

    :param input_raster: Path to the input raster file to be rescaled.
    :type input_raster: str
    :param reference_raster: Path to the reference raster file whose resolution and 
                             dimensions will be matched.
    :type reference_raster: str
    :param output_raster: Path to the output raster file where the rescaled raster 
                          will be saved.
    :type output_raster: str
    :param nodata_value: Value to use for nodata pixels in the output raster. 
                         Default is 0.
    :type nodata_value: int, optional
    """
    with rasterio.open(reference_raster) as ref:
        ref_transform = ref.transform
        ref_width = ref.width
        ref_height = ref.height
        ref_crs = ref.crs

    with rasterio.open(input_raster) as src:
        
        # calculate the transform for the rescaled raster
        transform, width, height = calculate_default_transform(
            src.crs, 
            ref_crs, 
            ref_width, 
            ref_height, 
            *src.bounds
        )

        out_meta = src.meta.copy()
        out_meta.update({
            'crs': ref_crs,
            'transform': ref_transform,
            'width': ref_width,
            'height': ref_height,
            'nodata': nodata_value
        })

        # open the output raster and perform the rescaling, setting nodata values to 0
        with rasterio.open(output_raster, 'w', **out_meta) as dest:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dest, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=ref_transform,
                    dst_crs=ref_crs,
                    resampling=Resampling.sum,
                    src_nodata=src.nodata,
                    dst_nodata=nodata_value
                )


def read_raster(
    raster_file: str, 
    sub_value=np.nan):
    """
    Read a raster file and replace nodata values.

    :param raster_file: Path to the raster file.
    :type raster_file: str
    :param sub_value: Value to substitute for nodata values in the raster. Default is numpy.nan.
    :type sub_value: float, optional
    :return: Array with nodata values replaced by `sub_value`.
    :rtype: numpy.ndarray
    """
    with rasterio.open(raster_file) as src:
        arr = src.read(1)
        nodata = src.nodata
        return np.where(arr == nodata, sub_value, arr)


def workhorse(
    target_ssp: str,
    target_year: int,
    global_dir: str,
    local_dir: str,
    mosaic_dir: str,
    output_dir: str,
    percent_area_file: str,
):
    """
    Process and integrate population data from various sources into a unified grid.

    This function performs several steps to process state-level gridded population data,
    mosaic them into a single raster, reproject and rescale the raster, and integrate 
    it with global population data. The final output is a new raster file that combines 
    the processed data.

    :param target_ssp: The target Shared Socioeconomic Pathway (SSP) scenario.
    :type target_ssp: str
    :param target_year: The target year for the population data.
    :type target_year: int
    :param global_dir: Directory containing global population data.
    :type global_dir: str
    :param local_dir: Directory containing state-level gridded population data.
    :type local_dir: str
    :param mosaic_dir: Directory to save the intermediate mosaic files.
    :type mosaic_dir: str
    :param output_dir: Directory to save the final output raster file.
    :type output_dir: str
    :param percent_area_file: Path to the shapefile containing percent area data.
    :type percent_area_file: str
    """
    logger.info(f"Processing {target_ssp} for year {target_year}")
    # generate a raster list from the sorce state-level gridded population root directory
    raster_list = glob.glob(
            os.path.join(
            local_dir, 
            "*", 
            "outputs",
            "model",
            target_ssp,
            f"*_total_{target_year}.tif"
        )
    )

    # ignore AK and HI
    raster_list = [i for i in raster_list if "alaska" not in i and "hawaii" not in i]

    len_raster_list = len(raster_list)
    assert(len_raster_list == 49), f"There should be 49 states present.  You only have {len_raster_list}"

    # mosaic individual state rasters into a US raster
    mosaic_file = os.path.join(mosaic_dir, f"gridded_usa_1km_{target_ssp.casefold()}_{target_year}.tif")
    mosaic_geotiffs(raster_list, mosaic_file)
    logger.info(f"Created file:  {mosaic_file}")  

    # reproject mosaic to WGS84 (EPSG:4326)
    mosaic_wgs_file = os.path.join(mosaic_dir, f"gridded_usa_1km_{target_ssp.casefold()}_{target_year}_wgs84.tif")
    reproject_geotiff(mosaic_file, mosaic_wgs_file)
    logger.info(f"Created file:  {mosaic_wgs_file}")

    # regrid reprojected US mosaic to 0.125 degrees
    reference_raster = os.path.join(global_dir, f"{target_ssp.casefold()}_{target_year}.tif")
    mosaic_wgs_rescale_file = os.path.join(
        mosaic_dir, 
        f"gridded_usa_0p125-deg_{target_ssp.casefold()}_{target_year}_wgs84.tif"
    )
    rescale_raster_to_match(mosaic_wgs_file, reference_raster, mosaic_wgs_rescale_file)
    logger.info(f"Created file:  {mosaic_wgs_rescale_file}")

    # Read in the percent area shapefile containing the percent area from the USA data that falls in 
    # -- global grid cells.
    pdf = gpd.read_file(percent_area_file)
    pdf.columns=["fid", "percent_in_grid", "geometry"]

    # grid cells having less than 50% area from the US data
    edge_grid_cells = pdf.loc[pdf["percent_in_grid"] < 50]["fid"].values.astype(np.int64)

    # read in original tethys global data
    tethys_file = os.path.join(global_dir, f"{target_ssp.casefold()}_{target_year}.tif")
    tethys_arr = read_raster(tethys_file, np.nan)

    # read in us raster and sub nodata values for nan
    mosaic_wgs_rescale_arr = read_raster(mosaic_wgs_rescale_file, sub_value=np.nan)

    # get edge values from the new and old data
    usa_flat = mosaic_wgs_rescale_arr.flatten()
    usa_edge_values = usa_flat[edge_grid_cells]
    tethys_edge_values = tethys_arr.flatten()[edge_grid_cells]

    # get the maximum population value of edge cells between USA and existing Tethys arrays
    max_grid_values = np.maximum(usa_edge_values, tethys_edge_values)

    # apply max values to the USA grid
    usa_flat[edge_grid_cells] = max_grid_values

    # reshape back 
    usa_final = usa_flat.reshape(mosaic_wgs_rescale_arr.shape)

    # zero out Tethys grid cells for the USA
    usa_grid_cells = np.where(~np.isnan(usa_final))
    tethys_no_usa = tethys_arr.copy()
    tethys_no_usa[usa_grid_cells] = 0

    # imprint USA values
    usa_final = np.where(np.isnan(usa_final), 0, usa_final)
    new_tethys_grid = tethys_no_usa + usa_final

    # write new file
    output_file = os.path.join(output_dir, f"{target_ssp.casefold()}_{target_year}.tif")

    with rasterio.open(tethys_file) as src:

        # adjust no data value to the original format
        new_tethys_grid = np.where(np.isnan(new_tethys_grid), src.nodata, new_tethys_grid)
        
        with rasterio.open(output_file, "w", **src.meta) as dest:
            dest.write(new_tethys_grid, 1)

    logger.info(f"Created output file: {output_file}")


def generate_population_data(
    global_dir: str,
    local_dir: str,
    mosaic_dir: str,
    output_dir: str,
    percent_area_file: str,
    ssp_list: List[str],
    year_list: List[int],
):
    """
    Generate and integrate population data into a unified grid.

    This function processes state-level gridded population data, mosaics them into a single raster,
    reprojects and rescales the raster, and integrates it with global population data. The final 
    output is a new raster file that combines the processed data for specified SSP scenarios and years.

    :param global_dir: Directory containing global population data.
    :type global_dir: str
    :param local_dir: Directory containing state-level gridded population data.
    :type local_dir: str
    :param mosaic_dir: Directory to save the intermediate mosaic files.
    :type mosaic_dir: str
    :param output_dir: Directory to save the final output raster file.
    :type output_dir: str
    :param percent_area_file: Path to the shapefile containing percent area data.
    :type percent_area_file: str
    :param ssp_list: List of SSPs scenarios to process.
    :type ssp_list: List[str]
    :param year_list: List of years to process.
    :type year_list: List[int]
    """

    for target_ssp in ssp_list:
        for target_year in year_list:

            workhorse(
                target_ssp=target_ssp,
                target_year=target_year,
                global_dir=global_dir,
                local_dir=local_dir,
                mosaic_dir=mosaic_dir,
                output_dir=output_dir,
                percent_area_file=percent_area_file,
            )


def parse_args():
    """
    Parse command-line arguments for generating and integrating population data.

    This function sets up an argument parser to handle the command-line arguments
    required for the script. It includes directories for global and state-level
    population data, directories for saving intermediate and final output files,
    the path to the shapefile containing percent area data, and lists of SSP
    scenarios and years to process.

    :return: Parsed command-line arguments.
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(description="Generate and integrate population data into a unified grid.")
    parser.add_argument('--global_dir', type=str, required=True, help='Directory containing global population data.')
    parser.add_argument('--local_dir', type=str, required=True, help='Directory containing state-level gridded population data.')
    parser.add_argument('--mosaic_dir', type=str, required=True, help='Directory to save the intermediate mosaic files.')
    parser.add_argument('--output_dir', type=str, required=True, help='Directory to save the final output raster file.')
    parser.add_argument('--percent_area_file', type=str, required=True, help='Path to the shapefile containing percent area data.')
    parser.add_argument('--ssp_list', type=str, nargs='+', required=True, help='List of SSPs scenarios to process.')
    parser.add_argument('--year_list', type=int, nargs='+', required=True, help='List of years to process.')
    
    return parser.parse_args()
    

if __name__ == "__main__":

    args = parse_args()

    generate_population_data(
        global_dir=args.global_dir,
        local_dir=args.local_dir,
        mosaic_dir=args.mosaic_dir,
        output_dir=args.output_dir,
        percent_area_file=args.percent_area_file,
        ssp_list=args.ssp_list,
        year_list=args.year_list,
    )

