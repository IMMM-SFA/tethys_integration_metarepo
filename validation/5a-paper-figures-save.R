# Generates publication figures for the Tethys data paper.
#
# Inputs:  ./data/huc{02,04,06,08}-{Sector}-{withdrawals,consumption}-usgs-tethys.csv
#          ./data/tethys_dominant_sector_by_grid_cell.csv
#          /Volumes/data/shapefiles/HUC{2,4,6,8}/HUC{2,4,6,8}.shp
#
# Output dirs (writes to all enabled dirs):
#   - Local: ./figures/  (always on)
#   - Paper: $HOME/Dropbox/Apps/Overleaf/TETHYS data paper/
#       Toggle with --paper / --no-paper, or env var WRITE_PAPER=true|false.
#       Default: off.

library(tidyverse)
library(sf)
library(ncdf4)
library(scico)
library(ggthemes)

options(
  readr.show_progress = FALSE,
  readr.show_col_types = FALSE,
  pillar.width = 1000,
  dplyr.summarise.inform = FALSE
)

# Settings ---------------------------------------------------------------
# %%
input_data_dir = "data"
local_plot_dir = "figures"
paper_plot_dir = "../paper/figures"
shapefile_path = "/Volumes/data/shapefiles"
tethys_base = "/Volumes/data/tethys/output_adjusted_usgs_method2"

# Set to TRUE to write to the paper directory in addition to the local directory.
write_to_paper = TRUE

dir.create(local_plot_dir, showWarnings = FALSE, recursive = TRUE)
if (write_to_paper) {
  dir.create(
    path.expand(paper_plot_dir),
    showWarnings = FALSE,
    recursive = TRUE
  )
}

# Save a plot to every enabled output directory. Keeps the per-figure code
# free of paper/local branching.
save_plot = function(filename, plot, ...) {
  out_paths = file.path(local_plot_dir, filename)
  if (write_to_paper) {
    out_paths = c(out_paths, file.path(path.expand(paper_plot_dir), filename))
  }
  for (p in out_paths) {
    ggsave(p, plot = plot, ...)
    message("Wrote ", p)
  }
}

# huc scale to use for the validation comparison panels
h = 6

read_demand_file = function(fn) {
  fn_split = str_split(fn, "-")
  demand_category = fn_split[[1]][2]
  demand_type = fn_split[[1]][3]
  read_csv(fn) |>
    mutate(demand_sector = demand_category, water_use_type = demand_type)
}

# Read USGS-Tethys demand at the chosen HUC scale --------------------------
# %%
demand_huc_all_list = list()
huc_demand_files = list.files(
  input_data_dir,
  paste0("huc", sprintf("%02d", h), "-*"),
  full.names = TRUE
)
demand_huc_all_list[[1]] = huc_demand_files |>
  map(read_demand_file) |>
  bind_rows() |>
  mutate(huc_scale = h)

demand_huc_all = bind_rows(demand_huc_all_list) |>
  mutate(water_use_type = str_to_title(water_use_type)) |>
  filter(huc_scale == h)

huc_name = paste0("huc", h)

demand_annual = demand_huc_all |>
  filter(huc_scale == h) |>
  mutate(year = year(datetime)) |>
  group_by(year, huc_scale, demand_sector, water_use_type) |>
  summarise(
    usgs_km3 = sum(usgs_km3),
    usgs_mgd = sum(usgs_mgd) / 12,
    tethys_km3 = sum(tethys_km3),
    tethys_mgd = sum(tethys_mgd) / 12,
    pdiff = (usgs_km3 - tethys_km3) / ((usgs_km3 + tethys_km3) / 2)
  ) |>
  mutate(
    usgs_km3 = ifelse(demand_sector == "Domestic", usgs_km3 * 1.12, usgs_km3),
    usgs_mgd = ifelse(demand_sector == "Domestic", usgs_mgd * 1.12, usgs_mgd),
  ) %>%
  bind_rows(
    . |>
      group_by(year, huc_scale, water_use_type) |>
      summarise(
        usgs_km3 = sum(usgs_km3),
        tethys_km3 = sum(tethys_km3),
        pdiff = (usgs_km3 - tethys_km3) / ((usgs_km3 + tethys_km3) / 2)
      ) |>
      mutate(demand_sector = "Total")
  )

demand_monthly = demand_huc_all |>
  filter(huc_scale == h) |>
  group_by(datetime, huc_scale, demand_sector, water_use_type) |>
  summarise(
    usgs_km3 = sum(usgs_km3),
    tethys_km3 = sum(tethys_km3),
    usgs_mgd = sum(usgs_mgd),
    tethys_mgd = sum(tethys_mgd),
    mgd_ratio = usgs_mgd / tethys_mgd,
    km3_ratio = usgs_km3 / tethys_km3
  )

demand_monthly_sum = demand_monthly |>
  group_by(datetime, huc_scale, water_use_type) |>
  summarise(usgs_km3 = sum(usgs_km3), tethys_km3 = sum(tethys_km3))

huc_shape = "%s/HUC%s/HUC%s.shp" |>
  sprintf(shapefile_path, h, h) |>
  st_read(quiet = TRUE) |>
  rename(huc = as.name(!!huc_name)) |>
  mutate(huc2 = substr(huc, 1, 2)) |>
  filter(huc2 %in% sprintf("%02d", 1:18))

ave_diff_huc = demand_huc_all |>
  filter(huc_scale == h) |>
  mutate(year = year(datetime)) |>
  group_by(huc, huc_scale, year, demand_sector, water_use_type) |>
  summarise(
    sum_usgs = sum(usgs_km3),
    sum_tethys = sum(tethys_km3),
    sum_diff = sum_usgs - sum_tethys,
    sum_pdiff = (sum_usgs - sum_tethys) /
      ((sum_usgs + sum_tethys) / 2) *
      100
  ) |>
  group_by(huc, huc_scale, demand_sector, water_use_type) |>
  summarise(
    mean_usgs = mean(sum_usgs),
    mean_tethys = mean(sum_tethys),
    mean_diff = mean(sum_diff),
    mean_pdiff = mean(sum_pdiff)
  )

ave_diff_monthly_huc = demand_huc_all |>
  filter(huc_scale == h) |>
  mutate(month = month(datetime)) |>
  group_by(huc, month, huc_scale, demand_sector, water_use_type) |>
  summarise(
    mean_usgs = mean(usgs_km3),
    mean_tethys = mean(tethys_km3),
    mean_diff = mean_usgs - mean_tethys,
    mean_pdiff = (mean_usgs - mean_tethys) /
      ((mean_usgs + mean_tethys) / 2) *
      100
  )

# Annual total timeseries -------------------------------------------------
# %%
annual_cutoff_year = 2010
annual_plot_years = annual_cutoff_year:2020
annual_year_lab = paste0("'", annual_plot_years - 2000)
p_annual_total = demand_annual |>
  filter(year >= annual_cutoff_year) |>
  mutate(year = as.integer(year)) |>
  mutate(plot_date = ISOdate(year, 1, 1)) |>
  pivot_longer(c(usgs_km3, tethys_km3)) |>
  mutate(
    name = case_when(
      name == "tethys_km3" ~ "Tethys [km^3]",
      name == "usgs_km3" ~ "USGS [km^3]"
    )
  ) |>
  filter(huc_scale == h) |>
  ggplot() +
  geom_line(aes(year, value, color = name), linewidth = 1) +
  facet_grid(water_use_type ~ demand_sector, scales = "free") +
  scale_color_manual("Data Source", values = colorblind_pal()(8)[c(1, 2)]) +
  scale_x_continuous(
    breaks = annual_plot_years
  ) +
  labs(
    x = "",
    y = "Water Demand [km^3/year]",
    title = "USGS/Tethys total annual water use"
  ) +
  theme_minimal() +
  theme(
    legend.position = "bottom",
    legend.margin = margin(t = -20, b = 0, r = 0, l = 0),
    panel.grid.minor = element_blank(),
    axis.text.x = element_text(angle = 45, hjust = 1),
    panel.grid.major = element_line(colour = "grey90"),
    plot.title.position = "plot",
    strip.text = element_text(face = "bold"),
    panel.border = element_rect(color = "black", fill = NA)
  ) +
  scale_fill_discrete("")

if (interactive()) {
  print(p_annual_total)
}
save_plot(
  sprintf("val1-huc%02d-usgs-tethys-annual-total.png", h),
  p_annual_total,
  width = 10,
  height = 6
)

# %% Annual pdiff boxplot ----------------------------------------------------
# %%
p_annual_total_pdiff = demand_annual |>
  mutate(water_use_type = str_sub(water_use_type, 1, 1)) |>
  ggplot() +
  geom_boxplot(aes(
    water_use_type,
    pdiff * 100,
    fill = factor(water_use_type)
  )) +
  facet_wrap(~demand_sector, nrow = 1) +
  scale_fill_manual(
    "Water Use Type",
    labels = c("C = Consumption", "W = Withdrawals"),
    values = c(colorblind_pal()(8)[c(7, 6)]),
    expand = expansion(mult = c(0, 0))
  ) +
  theme_minimal() +
  theme(
    legend.position = 'bottom',
    legend.margin = margin(t = -20, b = 0, r = 0, l = 0),
    strip.text = element_text(face = "bold"),
    panel.border = element_rect(color = "black", fill = NA)
  ) +
  labs(
    x = "", #"Water Use Type [C = Consuption, W = Withdrawals]",
    y = "Percent difference (USGS-Tethys) [%]",
    title = "Tethys vs. USGS annual water use percent difference"
  )

if (interactive()) {
  print(p_annual_total_pdiff)
}
save_plot(
  sprintf("val2-huc%02d-usgs-tethys-annual-total-pdiff.png", h),
  p_annual_total_pdiff,
  width = 8,
  height = 3
)

# Monthly total timeseries -------------------------------------------------
# %%
p_monthly_total = demand_monthly |>
  pivot_longer(c(usgs_km3, tethys_km3)) |>
  mutate(
    name = case_when(
      name == "tethys_km3" ~ "Tethys [km^3]",
      name == "usgs_km3" ~ "USGS [km^3]"
    )
  ) |>
  ggplot() +
  geom_boxplot(aes(factor(month(datetime)), value, fill = name)) +
  facet_wrap(
    vars(demand_sector, water_use_type),
    labeller = label_wrap_gen(multi_line = FALSE),
    scales = "free_y"
  ) +
  scale_fill_manual(
    "Dataset",
    values = c('grey60', colorblind_pal()(8)[2]),
    expand = expansion(mult = c(0, 0))
  ) +
  labs(
    x = "",
    y = "Water Demand [km^3/year]",
    title = "USGS/Tethys total monthly water use"
  ) +
  theme_minimal() +
  theme(
    legend.position = 'bottom',
    legend.margin = margin(t = -20, b = 0, r = 0, l = 0),
    strip.text = element_text(face = "bold"),
    panel.border = element_rect(color = "black", fill = NA)
  )

if (interactive()) {
  print(p_monthly_total)
}
save_plot(
  sprintf("val5-huc%02d-usgs-tethys-monthly-total.png", h),
  p_monthly_total,
  width = 8,
  height = 6
)

# HUC map: percent difference Tethys vs USGS ------------------------------
# %%
huc_diff_agg_data = huc_shape |>
  left_join(ave_diff_huc, by = "huc")

plot_huc_map_diff = function(
  data,
  title,
  diff_type = "diff",
  color_trans = "identity"
) {
  color_label = sprintf(
    "Average annual %sdifference in demand [USGS-Tethys] (km^3)",
    ifelse(diff_type == "pdiff", "% ", "")
  )
  varname = paste0("mean_", diff_type)
  data |>
    filter(!is.na(!!as.name(varname))) |>
    ggplot(aes(fill = !!as.name(varname))) +
    geom_sf(linewidth = ifelse(h > 8, .001, .01)) +
    facet_grid(water_use_type ~ demand_sector) +
    scale_fill_scico(
      color_label,
      palette = ifelse(diff_type == "diff", "roma", "batlow"),
      midpoint = ifelse(diff_type == "diff", 0, NA),
      trans = color_trans
    ) +
    labs(title = title) +
    theme_void() +
    theme(
      legend.position = "bottom",
      strip.text.y.right = element_text(angle = -90),
      strip.text.x = element_text(margin = margin(b = 5)),
      panel.grid = element_blank(),
      plot.background = element_rect(fill = "white", colour = NA)
    )
}

p_map_ave_pdiff_huc = plot_huc_map_diff(
  huc_diff_agg_data,
  sprintf("Annual ave HUC %s Tethys vs. USGS water demand", h),
  "pdiff"
)
if (interactive()) {
  print(p_map_ave_pdiff_huc)
}
save_plot(
  sprintf("val3-huc%02d-pdiff-usgs-tethys.png", h),
  p_map_ave_pdiff_huc,
  width = 10,
  height = 5
)

# Scatter: USGS vs Tethys per HUC -----------------------------------------
# %%
# Basin area in km^2 from the HUC shapefile, projected to Albers Equal Area
# CONUS (EPSG:5070) so areas are meaningful regardless of source CRS.
huc_area = huc_shape |>
  st_transform(5070) |>
  mutate(area_km2 = as.numeric(st_area(geometry)) / 1e6) |>
  st_drop_geometry() |>
  select(huc, area_km2)

cordf = ave_diff_huc |>
  group_by(water_use_type, demand_sector) |>
  summarise(
    x = -Inf,
    y = Inf,
    hjustvar = -.5,
    vjustvar = 1.5,
    label = paste0("r=", cor(mean_tethys, mean_usgs) |> round(3))
  )

p_scatter = ave_diff_huc |>
  left_join(huc_area, by = "huc") |>
  ggplot() +
  geom_point(aes(mean_usgs, mean_tethys, color = area_km2), size = 2.5) +
  facet_wrap(water_use_type ~ demand_sector, scales = "free") +
  geom_abline(slope = 1) +
  geom_text(
    aes(x, y, label = label, hjust = hjustvar, vjust = vjustvar),
    data = cordf
  ) +
  theme_minimal() +
  theme(
    legend.position = "bottom",
    panel.border = element_rect(color = "black", fill = NA)
  ) +
  labs(
    x = "USGS Annual Average Volume [km^3]",
    y = "Tethys Annual Average Volume [km^3]",
    title = sprintf("HUC %d average annual water demand: Tethys vs. USGS", h)
  ) +
  scale_color_viridis_c(
    name = expression("Basin area [km"^2 * "]"),
    option = "G",
    direction = -1,
    trans = "log10",
    labels = scales::label_comma()
  )

if (interactive()) {
  print(p_scatter)
}
save_plot(
  sprintf("val4-huc%02d-scatter-usgs-tethys.png", h),
  p_scatter,
  width = 8,
  height = 6
)

# Dominant sector map -----------------------------------------------------
# %%
# read usgs-tethys demand data
demand_huc_all_list = list()
huci = 0
for (h in c(2, 4, 6, 8)) {
  huci = huci + 1
  # combine demand category files
  huc_demand_files = list.files(
    input_data_dir,
    paste0('huc', sprintf('%02d', h), '-*'),
    full.names = T
  )
  demand_huc_all_list[[huci]] = huc_demand_files |>
    map(read_demand_file) |>
    bind_rows() |>
    mutate(huc_scale = h)
}
demand_huc_all = bind_rows(demand_huc_all_list) |>
  mutate(water_use_type = str_to_title(water_use_type))

sector = read_csv('data/tethys_dominant_sector_by_grid_cell.csv') |>
  pivot_longer(
    -c(lat, lon, spatial_ref),
    names_to = 'sector',
    values_to = 'demand'
  )

p_dominant_sector = sector |>
  group_by(lon, lat) |>
  mutate(demand_fix = ifelse(demand == 0, NA, demand)) |>
  reframe(sector = sector[which.max(demand_fix)]) |>
  ggplot() +
  geom_raster(aes(lon, lat, fill = factor(sector))) +
  theme_void() +
  # coord_map() +
  # scale_fill_brewer('Demand\nSector', palette = 'Dark2')
  # scale_fill_scico_d('Demand\nSector',palette = 'roma')
  # scale_fill_manual(
  #   'Demand\nSector',
  #   values = RColorBrewer::brewer.pal(6, 'Dark2')[c(1, 4, 2, 3, 5, 6)]
  # )
  scale_fill_manual(
    'Demand\nSector',
    values = colorblind_pal()(8)[c(2, 1, 3, 4, 6, 7)]
  )

p_dominant_sector
save_plot(
  "usage1-dominant-sector-tethys-grid.png",
  p_dominant_sector,
  width = 10,
  height = 5
)

# # Okabe-Ito colorblind-safe palette (Wong 2011, Nature Methods 8:441),
# # matching the prior published version from 5d-dominant-sector-map.py.
# sector_palette = c(
#   "Domestic" = "#0072b2", # blue
#   "Electricity" = "#d55e00", # vermillion
#   "Irrigation" = "#009e73", # bluish green
#   "Livestock" = "#e69f00", # orange
#   "Manufacturing" = "#cc79a7", # reddish purple
#   "Mining" = "#56b4e9" # sky blue
# )

# sector = read_csv("data/tethys_dominant_sector_by_grid_cell.csv") |>
#   pivot_longer(
#     -c(lat, lon, spatial_ref),
#     names_to = "sector",
#     values_to = "demand"
#   )

# p_dominant_sector = sector |>
#   group_by(lon, lat) |>
#   mutate(demand_fix = ifelse(demand == 0, NA, demand)) |>
#   reframe(sector = sector[which.max(demand_fix)]) |>
#   mutate(sector = factor(sector, levels = names(sector_palette))) |>
#   ggplot() +
#   geom_raster(aes(lon, lat, fill = sector)) +
#   scale_fill_manual("Demand\nSector", values = sector_palette, drop = FALSE) +
#   coord_quickmap() +
#   theme_void() +
#   theme(
#     plot.background = element_rect(fill = "white", colour = NA),
#     legend.position = "bottom"
#   )

# save_plot(
#   "usage1-dominant-sector-tethys-grid.png",
#   p_dominant_sector,
#   width = 10,
#   height = 5
# )

# Multi-HUC re-load for scenario projections ------------------------------
# %%
demand_huc_all_list = list()
huci = 0
for (h in c(2, 4, 6, 8)) {
  huci = huci + 1
  huc_demand_files = list.files(
    input_data_dir,
    paste0("huc", sprintf("%02d", h), "-*"),
    full.names = TRUE
  )
  demand_huc_all_list[[huci]] = huc_demand_files |>
    map(read_demand_file) |>
    bind_rows() |>
    mutate(huc_scale = h)
}
demand_huc_all = bind_rows(demand_huc_all_list) |>
  mutate(water_use_type = str_to_title(water_use_type))

# Scenario projection plot ------------------------------------------------
# %%
# Default to withdrawals; flip to "consumption" to produce the consumption panel.
demand_type = "withdrawals"

scenarios = c(
  "historical",
  "rcp45cooler_ssp3",
  "rcp45cooler_ssp5",
  "rcp45hotter_ssp3",
  "rcp45hotter_ssp5",
  "rcp85cooler_ssp3",
  "rcp85cooler_ssp5",
  "rcp85hotter_ssp3",
  "rcp85hotter_ssp5"
)

sectors = c("Domestic", "Electricity", "Irrigation")

# Extend the historical line through 2019 (the last year of the historical
# Tethys output) and join each future scenario to the historical line at
# 2019 so the eye sees a single continuous trace, not a 2015->2020 gap.
historical_cutoff = 2020

# %% Helpers

# Sum all sector sub-variables across (lat, lon) per year, returning a
# tibble with columns (year, demand_km3).
read_annual_sum = function(path) {
  if (!file.exists(path)) {
    return(tibble(year = integer(), demand_km3 = numeric()))
  }
  nc = nc_open(path)
  on.exit(nc_close(nc))

  years = ncvar_get(nc, "year")
  # All variables except coordinate vars / spatial_ref
  var_names = setdiff(names(nc$var), c("lat", "lon", "spatial_ref"))

  total_per_year = rep(0, length(years))
  for (v in var_names) {
    arr = ncvar_get(nc, v) # shape (lon, lat, year) per R's column-major load
    # Sum across spatial dims, leaving one value per year
    total_per_year = total_per_year +
      apply(arr, length(dim(arr)), sum, na.rm = TRUE)
  }

  tibble(year = as.integer(years), demand_km3 = total_per_year)
}

# Parse scenario string into rcp / climate / ssp components for aesthetics.
parse_scenario = function(s) {
  if (s == "historical") {
    tibble(
      scenario = s,
      rcp = "historical",
      climate = NA_character_,
      ssp = NA_character_
    )
  } else {
    # e.g. "rcp45cooler_ssp3"
    m = str_match(s, "^rcp(45|85)(cooler|hotter)_ssp([35])$")
    tibble(
      scenario = s,
      rcp = paste0("RCP", str_sub(m[, 2], 1, 1), ".", str_sub(m[, 2], 2, 2)),
      climate = m[, 3],
      ssp = paste0("SSP", m[, 4])
    )
  }
}

# %% Load every scenario x sector

message("Loading ", demand_type, " from ", tethys_base)

demand = expand_grid(scenario = scenarios, sector = sectors) |>
  mutate(
    path = file.path(
      tethys_base,
      scenario,
      paste0(sector, "_", demand_type, ".nc")
    )
  ) |>
  mutate(data = map(path, read_annual_sum)) |>
  select(-path) |>
  unnest(data)

# Add Total (sum across sectors)
total_by_sector = demand |>
  group_by(scenario, year) |>
  summarise(demand_km3 = sum(demand_km3), .groups = "drop") |>
  mutate(sector = "Total")

demand_all = bind_rows(demand, total_by_sector) |>
  mutate(
    sector = factor(
      sector,
      levels = c("Domestic", "Electricity", "Irrigation", "Total")
    )
  ) |>
  left_join(map_dfr(scenarios, parse_scenario), by = "scenario")

# Clip historical tail so it visually hands off to the future lines at 2019
demand_all = demand_all |>
  filter(!(scenario == "historical" & year > historical_cutoff))

# Connect each future scenario to the historical line: prepend the 2019
# historical demand as the future scenario's value at year 2019, so the future
# lines visually originate from the historical curve rather than starting in
# mid-air at 2020.
historical_2019 = demand_all |>
  filter(scenario == "historical", year == historical_cutoff) |>
  select(sector, demand_km3_hist = demand_km3)

future_starts = demand_all |>
  filter(scenario != "historical") |>
  distinct(scenario, sector, rcp, climate, ssp) |>
  left_join(historical_2019, by = "sector") |>
  transmute(
    scenario,
    sector,
    rcp,
    climate,
    ssp,
    year = historical_cutoff,
    demand_km3 = demand_km3_hist
  )

demand_all = bind_rows(demand_all, future_starts) |>
  arrange(scenario, sector, year)

# %% Plot

# Earth-toned palette per Cameron's preferences.
# RCP carries the emissions-pathway information so it gets the strongest
# visual channel (hue).
scenario_colors = c(
  "historical" = "#2a2a2a",
  "RCP4.5" = "#3d6b7a", # muted blue-teal (lower emissions)
  "RCP8.5" = "#a8501c" # rust (higher emissions)
)

# SSP carries socio-economic pathway (linetype).
ssp_linetypes = c("SSP3" = "solid", "SSP5" = "dashed")

# cooler/hotter carries climate-model variability (line width).
climate_widths = c("cooler" = 0.45, "hotter" = 0.85)

# Build a single line aesthetic by combining rcp for color, ssp for type,
# climate for width. Historical gets a plain black line.
p_projections = ggplot() +
  # Future scenarios
  geom_line(
    data = demand_all |> filter(scenario != "historical"),
    aes(
      x = year,
      y = demand_km3,
      group = scenario,
      color = rcp,
      linetype = ssp,
      linewidth = climate
    )
  ) +
  # Historical, drawn on top with distinct styling
  geom_line(
    data = demand_all |> filter(scenario == "historical"),
    aes(x = year, y = demand_km3, group = scenario),
    color = scenario_colors["historical"],
    linewidth = 0.9
  ) +
  facet_wrap(~sector, scales = "free_y", ncol = 2) +
  scale_color_manual(
    values = scenario_colors,
    breaks = c("RCP4.5", "RCP8.5"),
    name = "RCP"
  ) +
  scale_linetype_manual(values = ssp_linetypes, name = "SSP") +
  scale_linewidth_manual(values = climate_widths, name = "Climate") +
  scale_x_continuous(breaks = seq(1980, 2100, 20)) +
  labs(
    x = NULL,
    y = expression("Annual CONUS demand (km"^3 * " yr"^-1 * ")"),
    title = paste0(
      "Annual CONUS water ",
      demand_type,
      " by sector and scenario"
    ),
    subtitle = "Historical (black, 1975–2015) and eight future scenarios (2020–2100)."
  ) +
  theme_minimal(base_size = 11) +
  theme(
    panel.grid.minor = element_blank(),
    panel.grid.major = element_line(colour = "grey90"),
    plot.title.position = "plot",
    strip.text = element_text(face = "bold"),
    legend.position = "bottom",
    legend.box = "horizontal",
    legend.margin = margin(t = -5),
    panel.border = element_rect(color = "black", fill = NA)
  ) +
  guides(
    color = guide_legend(order = 1, override.aes = list(linewidth = 0.8)),
    linetype = guide_legend(order = 2, override.aes = list(linewidth = 0.8)),
    linewidth = guide_legend(order = 3)
  )

# %% Save

if (interactive()) {
  print(p_projections)
}
save_plot(
  "usage2-projections-annual-conus-timeseries.png",
  p_projections,
  width = 9,
  height = 6
)

message("Done.")
