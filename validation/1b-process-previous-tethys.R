library(tidyverse)
library(sf)
library(scico)
library(ggthemes)

options(
  readr.show_progress = FALSE,
  readr.show_col_types = FALSE,
  pillar.width = 1000,
  dplyr.summarise.inform = FALSE
)

##--------------------------------
## Old Tethys
##--------------------------------
read_crop_data = function(dir, water_use_type) {
  fns = list.files(dir, full.names = T)
  map(fns, function(fn) {
    crop_type = (fn |> basename() |> str_split('_'))[[1]][3]
    read_csv(fn) |>
      pivot_longer(
        -c(Grid_ID, lon, lat, ilon, ilat),
        names_to = 'year',
        values_to = 'demand_km3'
      ) |>
      mutate(crop_type = crop_type, water_use_type = water_use_type)
  }) |>
    bind_rows() |>
    group_by(year, water_use_type) |>
    summarise(demand_km3 = sum(demand_km3)) |>
    mutate(sector = 'Irrigation')
}

read_sector_data = function(dir) {
  fns = list.files(dir, full.names = T)
  map(fns, function(fn) {
    sector = (fn |> basename() |> str_split('_'))[[1]][1]
    read_csv(fn) |>
      pivot_longer(
        -c(Grid_ID, lon, lat, ilon, ilat),
        names_to = 'year',
        values_to = 'demand_km3'
      ) |>
      mutate(
        sector = sector |> substr(3, 20),
        water_use_type = fn |> basename() |> substr(1, 2)
      )
  }) |>
    bind_rows() |>
    filter(lon > -124.9, lon < -67.06, lat > 25.06, lat < 52.94) |>
    group_by(year, sector, water_use_type) |>
    summarise(demand_km3 = sum(demand_km3))
}

old_tethys = bind_rows(
  read_sector_data(
    'data/ssp3_rcp45_gfdl_consumption_sectors_annual'
  ),
  read_sector_data(
    'data/ssp3_rcp45_gfdl_withdrawals_sectors_annual'
  )
) |>
  mutate(
    tethys_version = '1.3',
    year = as.numeric(year),
    date = as.Date(sprintf('%s-01-01', year)),
    sector = case_when(
      sector == 'dom' ~ 'Domestic',
      sector == 'elec' ~ 'Electricity',
      sector == 'irr' ~ 'Irrigation',
      sector == 'liv' ~ 'Livestock',
      sector == 'mfg' ~ 'Manufacturing',
      sector == 'min' ~ 'Mining',
      sector == 'nonag' ~ 'Non-Agg',
      sector == 'total' ~ 'Total'
    ),
    water_use_type = case_when(
      water_use_type == 'cd' ~ 'Consumption',
      water_use_type == 'wd' ~ 'Withdrawals'
    )
  ) |>
  filter(sector %in% c("Domestic", "Electricity", "Irrigation")) %>%
  bind_rows(
    . |>
      group_by(year, date, water_use_type) |>
      summarise(demand_km3 = sum(demand_km3)) |>
      mutate(sector = 'Total')
  )

old_tethys |>
  ggplot() +
  geom_line(aes(date, demand_km3, color = water_use_type)) +
  facet_wrap(~sector, scales = 'free') +
  theme_minimal()


total = read_csv(
  'data/ssp3_rcp45_gfdl_consumption_sectors_annual/cdtotal_km3peryr.csv'
) |>
  pivot_longer(
    -c(Grid_ID, lon, lat, ilon, ilat),
    names_to = 'year',
    values_to = 'demand_km3'
  ) |>
  mutate(
    sector = 'Total',
    water_use_type = 'Consumption'
  ) |>
  filter(lon > -124.9, lon < -67.06, lat > 25.06, lat < 52.94)

##--------------------------------
## New Tethys
##--------------------------------

input_data_dir = 'data'

# huc scale to use
h = 6

read_demand_file = function(fn) {
  fn_split = str_split(fn, '_')
  demand_category = fn_split[[1]][2]
  demand_type = fn_split[[1]][3]
  # TODO could add error checking here
  read_csv(fn) |>
    mutate(sector = demand_category, water_use_type = demand_type)
}

# read usgs-tethys demand data
# combine demand category files
read_tethys_scenario_data = function(dir, scenario) {
  huc_demand_files = list.files(
    input_data_dir,
    paste0('*huc', sprintf('%s', h), '_', scenario),
    full.names = T
  )

  demand_huc_all = huc_demand_files |>
    map(read_demand_file) |>
    bind_rows() |>
    mutate(huc_scale = h) |>
    mutate(water_use_type = str_to_title(water_use_type)) |>
    filter(huc_scale == h)

  demand_huc_all
}


new_tethys = read_tethys_scenario_data(input_data_dir, 'rcp45cooler_ssp3') |>
  filter(sector %in% c("Domestic", "Electricity", "Irrigation")) %>%
  filter(huc_scale == h) |>
  group_by(year, huc_scale, sector, water_use_type) |>
  summarise(tethys_km3 = sum(demand_km3)) %>%
  bind_rows(
    . |>
      group_by(year, huc_scale, water_use_type) |>
      summarise(tethys_km3 = sum(tethys_km3)) |>
      mutate(sector = 'Total')
  ) |>
  rename(demand_km3 = tethys_km3) |>
  mutate(date = as.Date(sprintf('%s-01-01', year)))

new_tethys |>
  ggplot() +
  geom_line(aes(date, demand_km3, color = water_use_type)) +
  facet_wrap(~sector, scales = 'free') +
  theme_minimal()

##--------------------------------
## Compare new and old versions
##--------------------------------
tethys_compare = bind_rows(
  old_tethys |> mutate(tethys_version = '1.3-2022'),
  new_tethys |> mutate(tethys_version = '2.1-dev-2025')
)

tethys_compare |>
  filter(year < 2060, year > 2019) |>
  ggplot() +
  geom_line(aes(
    date,
    demand_km3,
    color = water_use_type,
    linetype = tethys_version
  )) +
  facet_wrap(~sector, scales = 'free') +
  theme_minimal() +
  scale_color_manual(values = colorblind_pal()(8)[2:3]) +
  labs(
    title = 'Tethys total US projected demands rcp45hotter_ssp3 version comparison'
  )
# scale_color_scico_d(palette = scico_palette_names(categorical = TRUE)[6])
