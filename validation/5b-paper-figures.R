# Generates publication figures for the Tethys data paper.
#
# Inputs:  ./data/huc{02,04,06,08}-{Sector}-{withdrawals,consumption}-usgs-tethys.csv
#          ./data/tethys_dominant_sector_by_grid_cell.csv
#          HUC6 and CONUS state shapefiles configured in paths.yml
#
# Output dirs (writes to all enabled dirs):
#   - Local: ./figures/
#   - Paper: ../paper/figures/

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
P <- yaml::read_yaml("paths.yml")
input_data_dir <- P$data_dir
local_plot_dir <- P$figures_dir
paper_plot_dir <- P$paper_figures_dir
tethys_base <- P$tethys_output_canonical

write_to_paper <- TRUE

dir.create(local_plot_dir, showWarnings = FALSE, recursive = TRUE)
if (write_to_paper) {
  dir.create(
    path.expand(paper_plot_dir),
    showWarnings = FALSE,
    recursive = TRUE
  )
}

save_plot <- function(filename, plot, ..., dpi = 300, bg = "white") {
  out_paths <- file.path(local_plot_dir, filename)
  if (write_to_paper) {
    out_paths <- c(out_paths, file.path(path.expand(paper_plot_dir), filename))
  }
  for (p in out_paths) {
    ggsave(p, plot = plot, dpi = dpi, bg = bg, ...)
    message("Wrote ", p)
  }
}

# Shared publication theme across cartesian validation figures
theme_tethys <- function(base_size = 12) {
  theme_minimal(base_size = base_size, base_family = "sans") +
    theme(
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(colour = "grey90", linewidth = 0.35),
      panel.border = element_rect(colour = "grey25", fill = NA, linewidth = 0.5),
      strip.text = element_text(face = "bold", size = base_size),
      axis.title = element_text(size = base_size),
      axis.text = element_text(size = base_size - 1.5, colour = "grey15"),
      legend.position = "bottom",
      legend.title = element_text(face = "bold", size = base_size - 0.5),
      legend.text = element_text(size = base_size - 1),
      plot.background = element_rect(fill = "white", colour = NA)
    )
}

# Harmonized validation window and HUC scale
h <- 6
val_years <- 2010:2019
domestic_usgs_scale <- 1.12

read_demand_file <- function(fn) {
  fn_split <- str_split(basename(fn), "-")
  demand_category <- fn_split[[1]][2]
  demand_type <- fn_split[[1]][3]
  read_csv(fn) |>
    mutate(demand_sector = demand_category, water_use_type = demand_type)
}

# Read USGS-Tethys demand at HUC6 and filter strictly to 2010-2019 --------
# %%
huc_demand_files <- list.files(
  input_data_dir,
  paste0("huc", sprintf("%02d", h), "-*"),
  full.names = TRUE
)

demand_huc_all <- huc_demand_files |>
  map(read_demand_file) |>
  bind_rows() |>
  mutate(
    huc_scale = h,
    water_use_type = str_to_title(water_use_type),
    year = year(datetime),
    month = month(datetime),
    usgs_km3 = ifelse(
      demand_sector == "Domestic",
      usgs_km3 * domestic_usgs_scale,
      usgs_km3
    ),
    usgs_mgd = ifelse(
      demand_sector == "Domestic",
      usgs_mgd * domestic_usgs_scale,
      usgs_mgd
    )
  ) |>
  filter(huc_scale == h, year %in% val_years)

huc_name <- paste0("huc", h)

demand_annual_sector <- demand_huc_all |>
  group_by(year, huc_scale, demand_sector, water_use_type) |>
  summarise(
    usgs_km3 = sum(usgs_km3),
    usgs_mgd = sum(usgs_mgd) / 12,
    tethys_km3 = sum(tethys_km3),
    tethys_mgd = sum(tethys_mgd) / 12,
    .groups = "drop"
  )

demand_annual_total <- demand_annual_sector |>
  group_by(year, huc_scale, water_use_type) |>
  summarise(
    usgs_km3 = sum(usgs_km3),
    usgs_mgd = sum(usgs_mgd),
    tethys_km3 = sum(tethys_km3),
    tethys_mgd = sum(tethys_mgd),
    .groups = "drop"
  ) |>
  mutate(demand_sector = "Total")

demand_annual <- bind_rows(demand_annual_sector, demand_annual_total) |>
  mutate(
    pdiff = 100 * (usgs_km3 - tethys_km3) / ((usgs_km3 + tethys_km3) / 2),
    demand_sector = factor(
      demand_sector,
      levels = c("Domestic", "Electricity", "Irrigation", "Total")
    )
  )

demand_monthly <- demand_huc_all |>
  group_by(datetime, year, month, huc_scale, demand_sector, water_use_type) |>
  summarise(
    usgs_km3 = sum(usgs_km3),
    tethys_km3 = sum(tethys_km3),
    usgs_mgd = sum(usgs_mgd),
    tethys_mgd = sum(tethys_mgd),
    .groups = "drop"
  )

huc_shape <- P[[sprintf("huc%s_shapefile", h)]] |>
  st_read(quiet = TRUE) |>
  rename(huc = as.name(!!huc_name)) |>
  mutate(huc2 = substr(huc, 1, 2)) |>
  filter(huc2 %in% sprintf("%02d", 1:18))

# Per-HUC annual totals and 2010-2019 annual means
huc_annual_sector <- demand_huc_all |>
  group_by(huc, huc_scale, year, demand_sector, water_use_type) |>
  summarise(
    sum_usgs = sum(usgs_km3),
    sum_tethys = sum(tethys_km3),
    .groups = "drop"
  )

ave_diff_huc <- huc_annual_sector |>
  group_by(huc, huc_scale, demand_sector, water_use_type) |>
  summarise(
    mean_usgs = mean(sum_usgs),
    mean_tethys = mean(sum_tethys),
    mean_diff = mean_usgs - mean_tethys,
    mean_pdiff = ifelse(
      (mean_usgs + mean_tethys) > 0,
      100 * (mean_usgs - mean_tethys) / ((mean_usgs + mean_tethys) / 2),
      NA_real_
    ),
    .groups = "drop"
  )

ave_diff_huc_total <- ave_diff_huc |>
  group_by(huc, huc_scale, water_use_type) |>
  summarise(
    mean_usgs = sum(mean_usgs),
    mean_tethys = sum(mean_tethys),
    mean_diff = mean_usgs - mean_tethys,
    mean_pdiff = ifelse(
      (mean_usgs + mean_tethys) > 0,
      100 * (mean_usgs - mean_tethys) / ((mean_usgs + mean_tethys) / 2),
      NA_real_
    ),
    .groups = "drop"
  ) |>
  mutate(demand_sector = "Total")

ave_diff_huc_with_total <- bind_rows(ave_diff_huc, ave_diff_huc_total) |>
  mutate(
    demand_sector = factor(
      demand_sector,
      levels = c("Domestic", "Electricity", "Irrigation", "Total")
    )
  )

message("Active HUC6 counts (mean_usgs > 0 over 2010-2019):")
ave_diff_huc_with_total |>
  filter(mean_usgs > 0) |>
  count(water_use_type, demand_sector) |>
  print()

# Fig 3: Annual total timeseries (2010-2019) ------------------------------
# %%
p_annual_total <- demand_annual |>
  mutate(year = as.integer(year)) |>
  pivot_longer(c(tethys_km3, usgs_km3), names_to = "source", values_to = "value") |>
  mutate(
    source = factor(
      case_when(
        source == "tethys_km3" ~ "Tethys",
        source == "usgs_km3" ~ "USGS"
      ),
      levels = c("Tethys", "USGS")
    )
  ) |>
  ggplot(aes(x = year, y = value, color = source, linetype = source)) +
  geom_line(linewidth = 1.05) +
  facet_grid(water_use_type ~ demand_sector, scales = "free_y") +
  scale_color_manual(
    "Dataset",
    values = c("Tethys" = "#1a1a1a", "USGS" = "#E69F00")
  ) +
  scale_linetype_manual(
    "Dataset",
    values = c("Tethys" = "solid", "USGS" = "dashed")
  ) +
  scale_x_continuous(breaks = seq(2010, 2019, 2)) +
  labs(
    x = NULL,
    y = expression("Annual water demand (km"^3 * " yr"^-1 * ")")
  ) +
  theme_tethys(base_size = 12) +
  theme(
    axis.text.x = element_text(angle = 35, hjust = 1),
    legend.key.width = unit(1.8, "cm")
  ) +
  guides(
    color = guide_legend(override.aes = list(linewidth = 1.1))
  )

if (interactive()) {
  print(p_annual_total)
}
save_plot(
  sprintf("val1-huc%02d-usgs-tethys-annual-total.png", h),
  p_annual_total,
  width = 10,
  height = 5.8
)

# Fig 4: HUC6 annual-mean symmetric percent difference boxplot ------------
# %%
p_annual_total_pdiff <- ave_diff_huc_with_total |>
  filter(mean_usgs > 0) |>
  mutate(use_abbrev = str_sub(water_use_type, 1, 1)) |>
  ggplot(aes(x = use_abbrev, y = mean_pdiff, fill = use_abbrev)) +
  geom_hline(yintercept = 0, linetype = "dashed", colour = "grey45", linewidth = 0.45) +
  geom_boxplot(width = 0.55, outlier.size = 1.3, outlier.alpha = 0.65, linewidth = 0.45) +
  facet_wrap(~demand_sector, nrow = 1) +
  scale_fill_manual(
    "Water use type",
    labels = c("C" = "C = Consumption", "W" = "W = Withdrawals"),
    values = c("C" = "#D55E00", "W" = "#0072B2")
  ) +
  scale_y_continuous(breaks = seq(-200, 200, 100), limits = c(-205, 205)) +
  labs(
    x = NULL,
    y = "Symmetric % difference, USGS - Tethys (%)"
  ) +
  theme_tethys(base_size = 12)

if (interactive()) {
  print(p_annual_total_pdiff)
}
save_plot(
  sprintf("val2-huc%02d-usgs-tethys-annual-total-pdiff.png", h),
  p_annual_total_pdiff,
  width = 9,
  height = 4.0
)

# Fig 7: Monthly CONUS total boxplot (2010-2019) --------------------------
# %%
p_monthly_total <- demand_monthly |>
  pivot_longer(c(tethys_km3, usgs_km3), names_to = "source", values_to = "value") |>
  mutate(
    source = factor(
      case_when(
        source == "tethys_km3" ~ "Tethys",
        source == "usgs_km3" ~ "USGS"
      ),
      levels = c("Tethys", "USGS")
    ),
    month_f = factor(month, levels = 1:12, labels = 1:12)
  ) |>
  ggplot(aes(x = month_f, y = value, fill = source)) +
  geom_boxplot(outlier.size = 1.1, outlier.alpha = 0.7, linewidth = 0.35) +
  facet_wrap(
    vars(water_use_type, demand_sector),
    labeller = label_wrap_gen(multi_line = FALSE),
    scales = "free_y"
  ) +
  scale_fill_manual(
    "Dataset",
    values = c("Tethys" = "grey60", "USGS" = "#E69F00")
  ) +
  labs(
    x = "Month",
    y = expression("Monthly water demand (km"^3 * " month"^-1 * ")")
  ) +
  theme_tethys(base_size = 12)

if (interactive()) {
  print(p_monthly_total)
}
save_plot(
  sprintf("val5-huc%02d-usgs-tethys-monthly-total.png", h),
  p_monthly_total,
  width = 9.5,
  height = 6.2
)

# Fig 5: HUC6 map of symmetric percent difference (2010-2019) -------------
# %%
huc_diff_agg_data <- huc_shape |>
  left_join(ave_diff_huc, by = "huc")

plot_huc_map_diff <- function(
  data,
  diff_type = "pdiff",
  color_trans = "identity"
) {
  color_label <- ifelse(
    diff_type == "pdiff",
    "Mean annual symmetric % difference, USGS - Tethys (%)",
    expression("Mean annual difference, USGS - Tethys (km"^3 * " yr"^-1 * ")")
  )
  varname <- paste0("mean_", diff_type)
  data |>
    filter(!is.na(!!as.name(varname))) |>
    ggplot(aes(fill = !!as.name(varname))) +
    geom_sf(colour = "grey25", linewidth = ifelse(h > 8, 0.02, 0.06)) +
    facet_grid(water_use_type ~ demand_sector) +
    scale_fill_scico(
      color_label,
      palette = ifelse(diff_type == "diff", "roma", "batlow"),
      midpoint = ifelse(diff_type == "diff", 0, NA),
      limits = if (diff_type == "pdiff") c(-200, 200) else NULL,
      breaks = if (diff_type == "pdiff") seq(-200, 200, 100) else waiver(),
      trans = color_trans
    ) +
    coord_sf(expand = FALSE) +
    theme_void(base_size = 12, base_family = "sans") +
    theme(
      legend.position = "bottom",
      legend.title = element_text(face = "bold", size = 11.5),
      legend.text = element_text(size = 10.5),
      strip.text.x = element_text(face = "bold", size = 12, margin = margin(b = 6)),
      strip.text.y.right = element_text(
        face = "bold",
        size = 12,
        angle = -90,
        margin = margin(l = 6)
      ),
      panel.spacing = unit(0.6, "lines"),
      plot.margin = margin(6, 8, 6, 8),
      plot.background = element_rect(fill = "white", colour = NA)
    ) +
    guides(
      fill = guide_colorbar(
        title.position = "top",
        title.hjust = 0.5,
        barwidth = unit(11, "cm"),
        barheight = unit(0.45, "cm")
      )
    )
}

p_map_ave_pdiff_huc <- plot_huc_map_diff(
  huc_diff_agg_data,
  diff_type = "pdiff"
)
if (interactive()) {
  print(p_map_ave_pdiff_huc)
}
save_plot(
  sprintf("val3-huc%02d-pdiff-usgs-tethys.png", h),
  p_map_ave_pdiff_huc,
  width = 10.5,
  height = 5.4
)

# Fig 6: Scatter USGS vs Tethys per HUC6 (2010-2019, mean_usgs > 0) -------
# %%
huc_area <- huc_shape |>
  st_transform(5070) |>
  mutate(area_km2 = as.numeric(st_area(geometry)) / 1e6) |>
  st_drop_geometry() |>
  select(huc, area_km2)

scatter_df <- ave_diff_huc |>
  filter(mean_usgs > 0) |>
  left_join(huc_area, by = "huc")

cordf <- scatter_df |>
  group_by(water_use_type, demand_sector) |>
  summarise(
    x = -Inf,
    y = Inf,
    hjustvar = -0.35,
    vjustvar = 1.6,
    label = sprintf("r = %.2f", cor(mean_tethys, mean_usgs)),
    .groups = "drop"
  )

p_scatter <- scatter_df |>
  ggplot() +
  geom_abline(slope = 1, intercept = 0, colour = "grey30", linewidth = 0.6) +
  geom_point(aes(mean_usgs, mean_tethys, color = area_km2), size = 2.2, alpha = 0.9) +
  facet_wrap(
    water_use_type ~ demand_sector,
    scales = "free",
    labeller = label_wrap_gen(multi_line = FALSE)
  ) +
  geom_text(
    aes(x, y, label = label, hjust = hjustvar, vjust = vjustvar),
    data = cordf,
    size = 4.0,
    fontface = "bold",
    family = "sans"
  ) +
  scale_color_viridis_c(
    name = expression("Basin area (km"^2 * ")"),
    option = "G",
    direction = -1,
    trans = "log10",
    labels = scales::label_log()
  ) +
  labs(
    x = expression("USGS mean annual demand (km"^3 * " yr"^-1 * ")"),
    y = expression("Tethys mean annual demand (km"^3 * " yr"^-1 * ")")
  ) +
  theme_tethys(base_size = 12) +
  guides(
    color = guide_colorbar(
      title.position = "left",
      title.vjust = 0.85,
      barwidth = unit(7.5, "cm"),
      barheight = unit(0.45, "cm")
    )
  )

if (interactive()) {
  print(p_scatter)
}
save_plot(
  sprintf("val4-huc%02d-scatter-usgs-tethys.png", h),
  p_scatter,
  width = 9.0,
  height = 6.3
)

# Fig 1: Dominant sector map at 1/8 deg with CONUS state borders ----------
# %%
sector_palette <- c(
  "Domestic" = "#0072B2",
  "Electricity" = "#D55E00",
  "Irrigation" = "#009E73",
  "Livestock" = "#E69F00",
  "Manufacturing" = "#CC79A7",
  "Mining" = "#56B4E9"
)

conus_states <- st_read(P$state_shapefile, quiet = TRUE) |>
  filter(!STUSPS %in% c("AK", "HI", "PR", "VI", "GU", "MP", "AS")) |>
  st_transform(4326)

sector <- read_csv(file.path(input_data_dir, "tethys_dominant_sector_by_grid_cell.csv")) |>
  pivot_longer(
    -c(lat, lon, spatial_ref),
    names_to = "sector",
    values_to = "demand"
  )

p_dominant_sector <- sector |>
  group_by(lon, lat) |>
  mutate(demand_fix = ifelse(demand == 0, NA_real_, demand)) |>
  reframe(sector = sector[which.max(demand_fix)]) |>
  mutate(sector = factor(sector, levels = names(sector_palette))) |>
  ggplot() +
  geom_raster(aes(x = lon, y = lat, fill = sector)) +
  geom_sf(
    data = conus_states,
    fill = NA,
    colour = "grey15",
    linewidth = 0.25,
    inherit.aes = FALSE
  ) +
  scale_fill_manual(
    "Dominant sector",
    values = sector_palette,
    drop = FALSE
  ) +
  coord_sf(crs = 4326, expand = FALSE) +
  theme_void(base_size = 12, base_family = "sans") +
  theme(
    plot.background = element_rect(fill = "white", colour = NA),
    plot.margin = margin(6, 8, 6, 8),
    legend.position = "bottom",
    legend.title = element_text(face = "bold", size = 12),
    legend.text = element_text(size = 11),
    legend.key.size = unit(0.55, "cm")
  ) +
  guides(fill = guide_legend(nrow = 1))

if (interactive()) {
  print(p_dominant_sector)
}
save_plot(
  "usage1-dominant-sector-tethys-grid.png",
  p_dominant_sector,
  width = 10,
  height = 5.4
)

# Fig 8: Scenario projection plot (1975-2100) -----------------------------
# %%
demand_type <- "withdrawals"

scenarios <- c(
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

sectors <- c("Domestic", "Electricity", "Irrigation")
historical_cutoff <- 2020

read_annual_sum <- function(path) {
  if (!file.exists(path)) {
    return(tibble(year = integer(), demand_km3 = numeric()))
  }
  nc <- nc_open(path)
  on.exit(nc_close(nc))

  years <- ncvar_get(nc, "year")
  var_names <- setdiff(names(nc$var), c("lat", "lon", "spatial_ref"))

  total_per_year <- rep(0, length(years))
  for (v in var_names) {
    arr <- ncvar_get(nc, v)
    total_per_year <- total_per_year +
      apply(arr, length(dim(arr)), sum, na.rm = TRUE)
  }

  tibble(year = as.integer(years), demand_km3 = total_per_year)
}

parse_scenario <- function(s) {
  if (s == "historical") {
    tibble(
      scenario = s,
      rcp = "Historical",
      climate = NA_character_,
      ssp = NA_character_
    )
  } else {
    m <- str_match(s, "^rcp(45|85)(cooler|hotter)_ssp([35])$")
    tibble(
      scenario = s,
      rcp = paste0("RCP", str_sub(m[, 2], 1, 1), ".", str_sub(m[, 2], 2, 2)),
      climate = m[, 3],
      ssp = paste0("SSP", m[, 4])
    )
  }
}

message("Loading ", demand_type, " from ", tethys_base)

demand <- expand_grid(scenario = scenarios, sector = sectors) |>
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

total_by_sector <- demand |>
  group_by(scenario, year) |>
  summarise(demand_km3 = sum(demand_km3), .groups = "drop") |>
  mutate(sector = "Total")

demand_all <- bind_rows(demand, total_by_sector) |>
  mutate(
    sector = factor(
      sector,
      levels = c("Domestic", "Electricity", "Irrigation", "Total")
    )
  ) |>
  left_join(map_dfr(scenarios, parse_scenario), by = "scenario") |>
  filter(!(scenario == "historical" & year > historical_cutoff))

historical_anchor <- demand_all |>
  filter(scenario == "historical", year == historical_cutoff) |>
  select(sector, demand_km3_hist = demand_km3)

future_starts <- demand_all |>
  filter(scenario != "historical") |>
  distinct(scenario, sector, rcp, climate, ssp) |>
  left_join(historical_anchor, by = "sector") |>
  transmute(
    scenario,
    sector,
    rcp,
    climate,
    ssp,
    year = historical_cutoff,
    demand_km3 = demand_km3_hist
  )

demand_all <- bind_rows(future_starts, demand_all) |>
  arrange(scenario, sector, year)

scenario_colors <- c(
  "Historical" = "#222222",
  "RCP4.5" = "#3d6b7a",
  "RCP8.5" = "#a8501c"
)

ssp_linetypes <- c("SSP3" = "solid", "SSP5" = "22")
climate_widths <- c("cooler" = 0.45, "hotter" = 0.95)

p_projections <- ggplot() +
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
  geom_line(
    data = demand_all |> filter(scenario == "historical"),
    aes(x = year, y = demand_km3, group = scenario, color = rcp),
    linewidth = 0.95
  ) +
  facet_wrap(~sector, scales = "free_y", ncol = 2) +
  scale_color_manual(
    values = scenario_colors,
    breaks = c("Historical", "RCP4.5", "RCP8.5"),
    name = "Pathway"
  ) +
  scale_linetype_manual(values = ssp_linetypes, name = "SSP") +
  scale_linewidth_manual(values = climate_widths, name = "GCM") +
  scale_x_continuous(breaks = seq(1980, 2100, 20)) +
  labs(
    x = NULL,
    y = expression("Annual CONUS demand (km"^3 * " yr"^-1 * ")")
  ) +
  theme_tethys(base_size = 12) +
  theme(
    legend.box = "horizontal",
    legend.title = element_text(face = "bold", size = 10.5),
    legend.text = element_text(size = 10),
    legend.spacing.x = unit(0.2, "cm")
  ) +
  guides(
    color = guide_legend(
      order = 1,
      keywidth = unit(0.95, "cm"),
      override.aes = list(linewidth = 0.95)
    ),
    linetype = guide_legend(
      order = 2,
      keywidth = unit(1.5, "cm"),
      override.aes = list(linewidth = 0.95, colour = "grey15")
    ),
    linewidth = guide_legend(
      order = 3,
      keywidth = unit(0.95, "cm")
    )
  )

if (interactive()) {
  print(p_projections)
}
save_plot(
  "usage2-projections-annual-conus-timeseries.png",
  p_projections,
  width = 10.0,
  height = 6.0
)

message("Done.")
