# Annual CONUS water demand by scenario, for the Tethys data paper v2.
# Produces a 4-panel figure: Domestic / Electricity / Irrigation / Total,
# each with one line per scenario (historical + 8 futures), x = year,
# y = annual demand (km^3/yr). Writes PNG to the Overleaf symlink.
#
# Companion to 5-paper-figures.R. Uses the canonical Tethys output at
# /Volumes/data/tethys/output_adjusted_usgs_method2/.

library(tidyverse)
library(ncdf4)
library(scico)

options(
  readr.show_progress = FALSE,
  readr.show_col_types = FALSE,
  dplyr.summarise.inform = FALSE
)

# %% Settings

tethys_base = "/Volumes/data/tethys/output_adjusted_usgs_method2"
plot_dir = "figures/"
output_file = file.path(plot_dir, "val6-scenarios-annual-conus-timeseries.png")

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
historical_cutoff = 2019

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
p = ggplot() +
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
    legend.margin = margin(t = -5)
  ) +
  guides(
    color = guide_legend(order = 1, override.aes = list(linewidth = 0.8)),
    linetype = guide_legend(order = 2, override.aes = list(linewidth = 0.8)),
    linewidth = guide_legend(order = 3)
  )

# %% Save

if (interactive()) {
  print(p)
}
message("Writing ", output_file)
ggsave(
  output_file,
  plot = p,
  width = 9,
  height = 6,
  dpi = 200,
  bg = "white"
)

message("Done.")
