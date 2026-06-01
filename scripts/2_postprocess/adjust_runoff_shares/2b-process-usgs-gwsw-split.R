library(sf)
library(terra)
library(tidyverse)
library(scico)

options(
  readr.show_progress = FALSE,
  readr.show_col_types = FALSE,
  pillar.width = 1000,
  dplyr.summarise.inform = FALSE
)

huc12_shape <- "/Volumes/data/shapefiles/HUC12/HUC12.shp" |>
  st_read(quiet = TRUE) |>
  rename(huc = huc12) |>
  mutate(huc2 = substr(huc, 1, 2)) |>
  # only include conus huc 2's
  filter(huc2 %in% sprintf("%02d", 1:18)) |>
  rename(huc12_id = huc)

huc2_shape <- "/Volumes/data/shapefiles/HUC2/HUC2.shp" |>
  st_read(quiet = TRUE)

read_usgs_long = function(fn) {
  fn |>
    read_csv() |>
    mutate(datetime = ym(year_month)) |>
    select(-year_month)
}

# units=MGD
# irrcuftot = public supply consumptive use fresh water total (surface + ground)
usgs_irr = "/Volumes/data/tethys/USGS-2025/combined_wu-irrigation-wd_CONUS_200001-202012_long.csv" |>
  read_usgs_long() |>
  inner_join(
    "/Volumes/data/tethys/USGS-2025/combined_wu-irrigation-cu_CONUS_200001-202012_long.csv" |>
      read_usgs_long(),
    by = join_by(datetime, huc12_id)
  )


usgs_irr_annual = usgs_irr |>
  mutate(year = year(datetime)) |>
  group_by(huc12_id, year) |>
  summarise(
    irrwdtot_mgd = mean(irrwdtot_mgd),
    irrwdgw_mgd = mean(irrwdgw_mgd)
  ) |>
  mutate(gw_frac = ifelse(irrwdtot_mgd == 0, 0, irrwdgw_mgd / irrwdtot_mgd)) |>
  left_join(huc12_shape, by = join_by(huc12_id))

usgs_irr_huc2 = usgs_irr_annual |>
  mutate(gw_frac = ifelse(irrwdtot_mgd == 0, 0, irrwdgw_mgd / irrwdtot_mgd)) |>
  group_by(huc12_id) |>
  summarise(gw_frac = mean(gw_frac)) |>
  left_join(huc12_shape, by = join_by(huc12_id)) |>
  mutate(huc2 = substr(huc12_id, 1, 2)) |>
  group_by(huc2) |>
  summarise(
    gw_frac = sum(areasqkm * gw_frac, na.rm = T) / sum(areasqkm, na.rm = T)
  ) |>
  left_join(huc2_shape, by = join_by(huc2))

usgs_irr_huc2 |>
  ggplot() +
  geom_sf(aes(fill = gw_frac, geometry = geometry), color = NA) +
  scale_fill_scico(palette = 'batlow') +
  theme_void()

# units=MGD
# pscuftot = public supply consumptive use fresh water total (surface + ground)
usgs_ps = "/Volumes/data/tethys/USGS-2025/combined_wu-public-supply-cu_CONUS_200901-202012_long.csv" |>
  read_usgs_long() |>
  inner_join(
    "/Volumes/data/tethys/USGS-2025/combined_wu-public-supply-wd_CONUS_200001-202012_long.csv" |>
      read_usgs_long(),
    by = join_by(datetime, huc12_id)
  )

usgs_ps_annual = usgs_ps |>
  mutate(year = year(datetime)) |>
  group_by(huc12_id, year) |>
  summarise(pswdtot_mgd = mean(pswdtot_mgd), pswdgw_mgd = mean(pswdgw_mgd)) |>
  mutate(gw_frac = ifelse(pswdtot_mgd == 0, 0, pswdgw_mgd / pswdtot_mgd)) |>
  left_join(huc12_shape, by = join_by(huc12_id))

usgs_ps_huc2 = usgs_ps_annual |>
  mutate(gw_frac = ifelse(pswdtot_mgd == 0, 0, pswdgw_mgd / pswdtot_mgd)) |>
  group_by(huc12_id) |>
  summarise(gw_frac = mean(gw_frac)) |>
  left_join(huc12_shape, by = join_by(huc12_id)) |>
  mutate(huc2 = substr(huc12_id, 1, 2)) |>
  group_by(huc2) |>
  summarise(
    gw_frac = sum(areasqkm * gw_frac, na.rm = T) / sum(areasqkm, na.rm = T)
  ) |>
  left_join(huc2_shape, by = join_by(huc2))

usgs_ps_huc2 |>
  ggplot() +
  geom_sf(aes(fill = gw_frac, geometry = geometry), color = NA) +
  scale_fill_scico(palette = 'batlow') +
  theme_void()

# units=MGD
# pscuftot = public supply consumptive use fresh water total (surface + ground)
usgs_te = "/Volumes/data/tethys/USGS-2025/combined_wu-thermoelectric_CONUS_200801-202012_long.csv" |>
  read_usgs_long()

usgs_te_annual = usgs_te |>
  mutate(year = year(datetime)) |>
  group_by(huc12_id, year) |>
  summarise(
    tewdftot_mgd = mean(tewdftot_mgd),
    tewdfgw_mgd = mean(tewdfgw_mgd)
  ) |>
  mutate(gw_frac = ifelse(tewdftot_mgd == 0, 0, tewdfgw_mgd / tewdftot_mgd)) |>
  left_join(huc12_shape, by = join_by(huc12_id))

usgs_te_huc2 = usgs_te_annual |>
  mutate(gw_frac = ifelse(tewdftot_mgd == 0, 0, tewdfgw_mgd / tewdftot_mgd)) |>
  group_by(huc12_id) |>
  summarise(gw_frac = mean(gw_frac)) |>
  left_join(huc12_shape, by = join_by(huc12_id)) |>
  mutate(huc2 = substr(huc12_id, 1, 2)) |>
  group_by(huc2) |>
  summarise(
    gw_frac = sum(areasqkm * gw_frac, na.rm = T) / sum(areasqkm, na.rm = T)
  ) |>
  left_join(huc2_shape, by = join_by(huc2))

usgs_te_huc2 |>
  ggplot() +
  geom_sf(aes(fill = gw_frac, geometry = geometry), color = NA) +
  scale_fill_scico(palette = 'batlow') +
  theme_void()


# sum of irr ps te
usgs_irr_ps_te_annual =
  usgs_irr |>
  left_join(usgs_ps, by = join_by(huc12_id, datetime)) |>
  left_join(usgs_te, by = join_by(huc12_id, datetime)) |>
  mutate(year = year(datetime)) |>
  group_by(huc12_id, year) |>
  mutate(
    irrwdtot_mgd = replace_na(irrwdtot_mgd, 0),
    pswdtot_mgd = replace_na(pswdtot_mgd, 0),
    tewdftot_mgd = replace_na(tewdftot_mgd, 0),
    irrwdgw_mgd = replace_na(irrwdgw_mgd, 0),
    pswdgw_mgd = replace_na(pswdgw_mgd, 0),
    tewdfgw_mgd = replace_na(tewdfgw_mgd, 0)
  ) |>
  summarise(
    irr_ps_te_wdtot_mgd = mean(irrwdtot_mgd + pswdtot_mgd + tewdftot_mgd),
    irr_ps_te_wdgw_mgd = mean(irrwdgw_mgd + pswdgw_mgd + tewdfgw_mgd)
  ) |>
  mutate(
    gw_frac = ifelse(
      irr_ps_te_wdtot_mgd == 0,
      0,
      irr_ps_te_wdgw_mgd / irr_ps_te_wdtot_mgd
    )
  )

usgs_irr_ps_te_mean = usgs_irr_ps_te_annual |>
  filter(year >= 2009) |>
  mutate(
    gw_frac = ifelse(
      irr_ps_te_wdtot_mgd == 0,
      0,
      irr_ps_te_wdgw_mgd / irr_ps_te_wdtot_mgd
    )
  ) |>
  group_by(huc12_id) |>
  summarise(gw_frac = mean(gw_frac)) |>
  left_join(huc12_shape, by = join_by(huc12_id))

usgs_irr_ps_te_huc2 = usgs_irr_ps_te_annual |>
  mutate(
    gw_frac = ifelse(
      irr_ps_te_wdtot_mgd == 0,
      0,
      irr_ps_te_wdgw_mgd / irr_ps_te_wdtot_mgd
    )
  ) |>
  group_by(huc12_id) |>
  summarise(gw_frac = mean(gw_frac)) |>
  left_join(huc12_shape, by = join_by(huc12_id)) |>
  mutate(huc2 = substr(huc12_id, 1, 2)) |>
  group_by(huc2) |>
  summarise(
    gw_frac = sum(areasqkm * gw_frac, na.rm = T) / sum(areasqkm, na.rm = T)
  ) |>
  left_join(huc2_shape, by = join_by(huc2))

usgs_irr_ps_te_huc2 |>
  ggplot() +
  geom_sf(aes(fill = gw_frac, geometry = geometry), color = NA) +
  scale_fill_scico(palette = 'batlow', limits = c(0, 0.6)) +
  theme_void()


# all USGS
usgs_irr_huc2 |>
  mutate(demand_type = 'irr') |>
  bind_rows(usgs_ps_huc2 |> mutate(demand_type = 'ps')) |>
  bind_rows(usgs_te_huc2 |> mutate(demand_type = 'te')) |>
  bind_rows(usgs_irr_ps_te_huc2 |> mutate(demand_type = 'irr_ps_te')) |>
  ggplot() +
  geom_sf(aes(fill = gw_frac, geometry = geometry), color = NA) +
  facet_wrap(~demand_type) +
  scale_fill_scico(palette = 'batlow') +
  theme_void()


tethys_huc2 = read_csv('../../../validation/data/tethys_runoff_share_huc2.csv') |>
  group_by(huc2) |>
  summarise(gw_frac = 1 - mean(share)) |>
  left_join(huc2_shape, by = join_by(huc2)) |>
  mutate(demand_type = 'Tethys') |>
  bind_rows(
    usgs_irr_ps_te_huc2 |>
      mutate(demand_type = 'USGS irr+ps+te')
  )

tethys_huc2 |>
  ggplot() +
  geom_sf(aes(fill = gw_frac, geometry = geometry), color = NA) +
  geom_label(aes(label = huc2)) +
  facet_wrap(~demand_type) +
  scale_fill_scico(palette = 'batlow') +
  theme_void()

tethys_huc2 |>
  ggplot() +
  geom_bar(
    aes(huc2, gw_frac, fill = demand_type),
    stat = 'identity',
    position = 'dodge',
    color = 'black'
  ) +
  scale_fill_scico_d(palette = scico_palette_names(categorical = TRUE)[2]) +
  theme_bw() +
  theme(legend.position = 'bottom')


# rasterize the HUC12 polygons to 1/8th de
usgs_irr_ps_te_annual_wide = usgs_irr_ps_te_annual |>
  filter(year >= 2009) |>
  mutate(sw_frac = 1 - gw_frac) |>
  pivot_wider(id_cols = huc12_id, names_from = year, values_from = sw_frac)

polygons = huc12_shape |> left_join(usgs_irr_ps_te_annual_wide)

# Define raster extent and resolution
raster_grid <- rast(
  ext(-124.9375, -67.0625, 25.0625, 52.9375),
  res = c(0.0625, 0.0625)
) # Specify resolution

# Time stamps
timestamps <- paste0(2009:2020)

# Initialize list to hold raster grids
raster_list <- list()

# Rasterize for each timestamp
for (timestamp in timestamps) {
  # Rasterize current timestamp's data (assumes data column matches timestamp)
  rasterized <- rasterize(vect(polygons), raster_grid, field = timestamp)
  raster_list[[timestamp]] <- rasterized
}

# Convert rasters to a multi-layer RasterBrick
brick <- rast(raster_list)

# Save RasterBrick to NetCDF
writeCDF(brick, "usgs-runoff-share-2009-2020.nc", overwrite = TRUE)
print("NetCDF file saved.")
