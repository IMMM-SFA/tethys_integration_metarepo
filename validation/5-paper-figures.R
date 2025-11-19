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

input_data_dir = 'data'
plot_dir = '~/Dropbox/Apps/Overleaf/TETHYS data paper/'

# huc scale to use
h = 6

read_demand_file = function(fn) {
  fn_split = str_split(fn, '-')
  demand_category = fn_split[[1]][2]
  demand_type = fn_split[[1]][3]
  # TODO could add error checking here
  read_csv(fn) |>
    mutate(demand_sector = demand_category, water_use_type = demand_type)
}

# read usgs-tethys demand data
demand_huc_all_list = list()
# huci = 0
# for (h in c(2, 4, 6, 8)) {
# huci = huci + 1
# combine demand category files
huc_demand_files = list.files(
  input_data_dir,
  paste0('huc', sprintf('%02d', h), '-*'),
  full.names = T
)
demand_huc_all_list[[1]] = huc_demand_files |>
  map(read_demand_file) |>
  bind_rows() |>
  mutate(huc_scale = h)
# }
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
    usgs_km3 = ifelse(demand_sector == 'Domestic', usgs_km3 * 1.12, usgs_km3),
    usgs_mgd = ifelse(demand_sector == 'Domestic', usgs_mgd * 1.12, usgs_mgd),
  ) %>%
  bind_rows(
    . |>
      group_by(year, huc_scale, water_use_type) |>
      summarise(
        usgs_km3 = sum(usgs_km3),
        tethys_km3 = sum(tethys_km3),
        pdiff = (usgs_km3 - tethys_km3) / ((usgs_km3 + tethys_km3) / 2)
      ) |>
      mutate(demand_sector = 'Total')
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

huc_shape = "/Volumes/data/shapefiles/HUC%s/HUC%s.shp" |>
  sprintf(h, h) |>
  st_read(quiet = TRUE) |>
  rename(huc = as.name(!!huc_name)) |>
  mutate(huc2 = substr(huc, 1, 2)) |>
  # only include conus huc 2's
  filter(huc2 %in% sprintf("%02d", 1:18)) #|>
# simplify the polygons for faster plotting
# need to project before simplifying
# st_transform(54032) |> # azimuthal equidistant
# st_transform("ESRI:102003") |> # USA_Contiguous_Albers_Equal_Area_Conic
# st_simplify(dTolerance = .005) |>
# st_transform(4326) # back to lat/lon

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

# --------------------------------------------------
# annual total timeseries
# --------------------------------------------------
p_annual_total = demand_annual |>
  mutate(plot_date = ISOdate(year, 1, 1)) |>
  pivot_longer(c(usgs_km3, tethys_km3)) |>
  mutate(
    name = case_when(
      name == 'tethys_km3' ~ 'Tethys [km^3]',
      name == 'usgs_km3' ~ 'USGS [km^3]'
    )
  ) |>
  filter(huc_scale == h) |>
  ggplot() +
  geom_line(aes(plot_date, value, color = name), linewidth = 1) +
  # geom_bar(
  #   aes(year, value, fill = name),
  #   position = "dodge",
  #   stat = "identity",
  #   color = "black"
  # ) +
  # facet_wrap(water_use_type ~ demand_sector, scales = 'free', nrow = 2) +
  facet_grid(water_use_type ~ demand_sector, scales = 'free') +
  # scale_fill_viridis_d("Dataset", option = "G") +
  scale_color_manual('Data Source', values = colorblind_pal()(8)[c(1, 2)]) +
  labs(
    x = "",
    y = "Water Demand [km^3/year]",
    title = 'USGS/Tethys total annual water use'
  ) +
  theme_bw() +
  theme(legend.position = 'bottom') +
  scale_fill_discrete('')
p_annual_total

"%s/val1-huc%02d-usgs-tethys-annual-total.png" |>
  sprintf(plot_dir, h) |>
  ggsave(p_annual_total, width = 10, height = 6)


# --------------------------------------------------
# annual total timeseries for IM3 update slides
# --------------------------------------------------
p_annual_total2 = demand_annual |>
  filter(demand_sector != 'Total', water_use_type == 'Withdrawals') |>
  mutate(plot_date = ISOdate(year, 1, 1)) |>
  pivot_longer(c(usgs_km3, tethys_km3)) |>
  mutate(
    name = case_when(
      name == 'tethys_km3' ~ 'Tethys [km^3]',
      name == 'usgs_km3' ~ 'USGS [km^3]'
    )
  ) |>
  filter(huc_scale == h) |>
  ggplot() +
  geom_line(aes(plot_date, value, color = name), linewidth = 1) +

  # geom_bar(
  #   aes(year, value, fill = name),
  #   position = "dodge",
  #   stat = "identity",
  #   color = "black"
  # ) +
  # facet_wrap(water_use_type ~ demand_sector, scales = 'free', nrow = 2) +
  facet_grid(water_use_type ~ demand_sector, scales = 'free') +
  # scale_fill_viridis_d("Dataset", option = "G") +
  scale_color_manual('Data Source', values = colorblind_pal()(8)[c(1, 2)]) +
  labs(
    x = "",
    y = "Water Demand [km^3/year]",
    title = 'USGS/Tethys total annual water use'
  ) +
  theme_bw() +
  theme(
    legend.position = 'bottom',
    axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1)
  ) +
  scale_fill_discrete('')
p_annual_total2

# --------------------------------------------------
# annual pdiff boxplot
# --------------------------------------------------
p_annual_total_pdiff = demand_annual |>
  ggplot() +
  geom_boxplot(aes(demand_sector, pdiff * 100)) +
  facet_wrap(~water_use_type) +
  theme_bw() +
  labs(x = 'Demand Sector', y = 'Percent difference (USGS-Tethys) [%]')
p_annual_total_pdiff

"%s/val2-huc%02d-usgs-tethys-annual-total-pdiff.png" |>
  sprintf(plot_dir, h) |>
  ggsave(p_annual_total_pdiff, width = 8, height = 3)

# --------------------------------------------------
# annual pdiff lines
# --------------------------------------------------
demand_annual |>
  ggplot() +
  geom_line(aes(year, pdiff * 100, linetype = demand_sector)) +
  facet_wrap(~water_use_type)

# --------------------------------------------------
# monthly total timeseries
# --------------------------------------------------
p_monthly_total = demand_monthly |>
  pivot_longer(c(usgs_km3, tethys_km3)) |>
  ggplot() +
  # geom_line(aes(datetime, value, color = name)) +
  geom_boxplot(aes(factor(month(datetime)), value, fill = name)) +
  facet_wrap(water_use_type ~ demand_sector, scales = 'free_y') +
  scale_fill_manual("Dataset", values = colorblind_pal()(8)[1:2]) +
  labs(
    x = "",
    y = "Water Demand [km^3/year]",
    title = 'USGS/Tethys total monthly water use'
  ) +
  theme_bw() +
  theme(legend.position = 'bottom')
# scale_fill_discrete('')
p_monthly_total
"%s/val5-huc%02d-usgs-tethys-monthly-total.png" |>
  sprintf(plot_dir, h) |>
  ggsave(p_monthly_total, width = 10, height = 6)


# --------------------------------------------------
# plot difference between tethys and USGS
# --------------------------------------------------
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
    # scale_fill_viridis_c("Average difference\nin water demand\n[USGS-Tethys]\n(MGD)", option = "G") +
    # https://stackoverflow.com/questions/37482977/
    # what-is-a-good-palette-for-divergent-colors-in-r-or-can-viridis-and-magma-b
    facet_grid(water_use_type ~ demand_sector) +
    scale_fill_scico(
      color_label,
      # palette = "vik", "broc", "roma", "cork"
      palette = ifelse(diff_type == "diff", "roma", "batlow"),
      midpoint = ifelse(diff_type == "diff", 0, NA),
      trans = color_trans
    ) +
    labs(title = title) +
    theme_void() +
    theme(
      # legend.position = "inside",
      # legend.position.inside = c(.9, .2),
      legend.position = "bottom",
      strip.text.y.right = element_text(angle = -90),
      strip.text.x = element_text(margin = margin(b = 5)),
      panel.grid = element_blank(),
      plot.background = element_rect(fill = 'white', colour = NA)
    )
}

p_map_ave_pdiff_huc = plot_huc_map_diff(
  huc_diff_agg_data,
  "Annual ave HUC %s Tethys vs. USGS water demand" |>
    sprintf(h),
  "pdiff"
)
p_map_ave_pdiff_huc
"%s/val3-huc%02d-pdiff-usgs-tethys.png" |>
  sprintf(plot_dir, h) |>
  ggsave(p_map_ave_pdiff_huc, width = 10, height = 5)


# --------------------------------------------------
# scatter plots
# --------------------------------------------------
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
  ggplot() +
  geom_point(aes(mean_usgs, mean_tethys)) +
  facet_wrap(water_use_type ~ demand_sector, scales = 'free') +
  geom_abline(slope = 1) +
  geom_text(
    aes(x, y, label = label, hjust = hjustvar, vjust = vjustvar),
    data = cordf
  ) +
  theme_bw() +
  theme(plot.background = element_rect(fill = 'white')) +
  labs(
    x = 'USGS Annual Average Volume [km^3]',
    y = 'USGS Annual Average Volume [km^3]'
  )
p_scatter
"%s/val4-huc%02d-scatter-usgs-tethys.png" |>
  sprintf(plot_dir, h) |>
  ggsave(p_scatter, width = 8, height = 5)

# --------------------------------------------------
# max use plot
# --------------------------------------------------

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
"%s/usage1-dominant-sector-tethys-grid.png" |>
  sprintf(plot_dir) |>
  ggsave(p_dominant_sector, width = 10, height = 5)


# --------------------------------------------------
# projection plot
# --------------------------------------------------

scenarios = c(
  'historical',
  'rcp45cooler_ssp3',
  'rcp45cooler_ssp5',
  'rcp45hotter_ssp3',
  'rcp45hotter_ssp5',
  'rcp85cooler_ssp3',
  'rcp85cooler_ssp5',
  'rcp85hotter_ssp3',
  'rcp85hotter_ssp5'
)

read_tethys_file = function(fn) {
  fn_split = str_split(fn, '_')
  demand_category = fn_split[[1]][2]
  demand_type = fn_split[[1]][3]
  # TODO could add error checking here
  read_csv(fn) |>
    mutate(sector = demand_category, water_use_type = demand_type)
}


# combine demand category files
read_tethys_scenario_data = function(dir, scenario, h) {
  huc_demand_files = list.files(
    input_data_dir,
    paste0('*huc', sprintf('%s', h), '_', scenario),
    full.names = T
  )

  demand_huc_all = huc_demand_files |>
    map(read_tethys_file) |>
    bind_rows() |>
    mutate(huc_scale = h) |>
    mutate(water_use_type = str_to_title(water_use_type)) |>
    filter(huc_scale == h)

  demand_huc_all
}

h = 2
tethys_projections_huc2 = map(scenarios, function(scenario) {
  read_tethys_scenario_data(input_data_dir, scenario, h) |>
    mutate(scenario = scenario)
}) |>
  bind_rows() |>
  group_by(year, sector, water_use_type, scenario) |>
  summarise(demand_km3 = sum(demand_km3))


p_projections = tethys_projections_huc2 |>
  ggplot() +
  geom_line(aes(
    year,
    demand_km3,
    linetype = water_use_type,
    color = scenario
  )) +
  facet_wrap(~sector, scales = 'free') +
  theme_bw() +
  scale_color_scico_d() +
  labs(
    title = 'Tethys total US projected demands',
    x = '',
    y = 'Demand [km^3]'
  )

p_projections
"%s/usage2-projections-tethys-timeseries.png" |>
  sprintf(plot_dir) |>
  ggsave(p_projections, width = 10, height = 5)
