#!/bin/zsh

source ../../venv/bin/activate

for s in SSP3 SSP5; do
    for y in 2010 2020 2030 2040 2050 2060 2070 2080 2090 2100; do
        python population_to_tethys.py --global_dir ../../data/population --local_dir ../../data/population/zoraghein-oneill_population_gravity_inputs_outputs --mosaic_dir . --output_dir . --percent_area_file ./percent_grid.zip --ssp_list $s --year_list $y
    done
done
