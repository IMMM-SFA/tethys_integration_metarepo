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
plot_dir = 'figures/'

hucs = 6 #c(2, 4, 6, 8)


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

for (h in hucs) {
  #
  # h = 2
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

  "%s/huc%02d-usgs-tethys-annual-total.png" |>
    sprintf(plot_dir, h) |>
    ggsave(p_annual_total, width = 10, height = 6)

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

  "%s/huc%02d-usgs-tethys-annual-total-pdiff.png" |>
    sprintf(plot_dir, h) |>
    ggsave(p_annual_total_pdiff, width = 10, height = 3)

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
  "%s/huc%02d-usgs-tethys-monthly-total.png" |>
    sprintf(plot_dir, h) |>
    ggsave(p_monthly_total, width = 10, height = 6)

  # --------------------------------------------------
  # annual total sum timeseries
  # --------------------------------------------------
  p_annual_total_sum = demand_annual |>
    filter(demand_sector == 'Total') |>
    pivot_longer(c(usgs_km3, tethys_km3)) |>
    filter(huc_scale == h) |>
    ggplot() +
    geom_bar(
      aes(year, value, fill = name),
      position = "dodge",
      stat = "identity",
      color = "black"
    ) +
    facet_grid(water_use_type ~ ., scales = 'free_y') +
    theme_bw() +
    # scale_fill_viridis_d("Dataset", option = "G") +
    labs(
      x = "",
      y = "Water Demand [km^3/year]",
      title = 'USGS/Tethys total annual water use, Domestic + Irrigation + Thermoelectric'
    ) +
    theme(legend.position = 'bottom') +
    scale_fill_discrete('')
  p_annual_total_sum
  "%s/huc%02d-usgs-tethys-annual-total-sum.png" |>
    sprintf(plot_dir, h) |>
    ggsave(p_annual_total_sum, width = 10, height = 6)

  # --------------------------------------------------
  # aggregated huc map
  # --------------------------------------------------
  # plot_huc_map = function(
  #   data,
  #   plot_variable,
  #   title,
  #   color_trans = "identity"
  # ) {
  #   ggplot(data, aes(fill = !!as.name(plot_variable))) +
  #     geom_sf(linewidth = ifelse(h > 8, .001, .01)) +
  #     facet_wrap(~source) +
  #     scale_fill_viridis_c(
  #       "Average annual\nwater %s\n(km^3)" |> sprintf(demand_type),
  #       option = "G",
  #       trans = color_trans,
  #       direction = -1
  #     ) +
  #     facet_grid(water_use_type ~ demand_sector) +
  #     labs(title = title) +
  #     theme_void() +
  #     theme(
  #       legend.position = "bottom",
  #       # legend.position.inside = c(.5, .2),
  #       strip.text.y.right = element_text(angle = -90),
  #       panel.grid = element_blank()
  #     )
  # }
  # huc_agg_data = huc_shape |>
  #   left_join(ave_diff_huc, by = "huc") |>
  #   pivot_longer(c(mean_usgs, mean_tethys), names_to = "source")

  # p_map_ave_huc = plot_huc_map(
  #   huc_agg_data,
  #   "value",
  #   "Annual ave %s HUC %s Tethys %s vs. USGS water demand" |>
  #     sprintf(tethys_demand_category, h, demand_type)
  # )
  # # p_map_ave_huc
  # "%s/huc%02d-usgs-tethys.png" |>
  #   sprintf(plot_dir, h) |>
  #   ggsave(p_map_ave_huc, width = 12, height = 6)

  # p_map_ave_huc_log = plot_huc_map(huc_agg_data, "value",
  #   "Annual ave %s HUC %s Tethys %s vs. USGS water demand" |> sprintf(tethys_demand_category, h, demand_type),
  #   color_trans = "log10"
  # )
  # p_map_ave_huc_log
  # "figures/huc%02d-%s-%s-usgs-tethys-log.png" |>
  #   sprintf(h, tethys_demand_category, demand_type) |>
  # ggsave(p_map_ave_huc_log, width = 20, height = 6)

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
      "Average annual %sdifference in water \n %s [USGS-Tethys] (km^3)",
      ifelse(diff_type == "pdiff", "% ", ""),
      sprintf(demand_type)
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
        plot.background = element_rect(fill = 'white')
      )
  }

  p_map_ave_diff_huc = plot_huc_map_diff(
    huc_diff_agg_data,
    "Annual ave HUC %s Tethys vs. USGS water demand" |>
      sprintf(h)
  )
  p_map_ave_diff_huc
  "%s/huc%02d-diff-usgs-tethys.png" |>
    sprintf(plot_dir, h) |>
    ggsave(p_map_ave_diff_huc, width = 10, height = 6)

  p_map_ave_pdiff_huc = plot_huc_map_diff(
    huc_diff_agg_data,
    "Annual ave %s HUC %s Tethys %s vs. USGS water demand" |>
      sprintf(tethys_demand_category, h, demand_type),
    "pdiff"
  )
  p_map_ave_pdiff_huc
  "%s/huc%02d-pdiff-usgs-tethys.png" |>
    sprintf(plot_dir, h) |>
    ggsave(p_map_ave_pdiff_huc, width = 10, height = 6)

  # p_map_ave_diff_huc_log = plot_huc_map_diff(
  #   huc_diff_agg_data,
  #   "Annual ave %s HUC %s Tethys %s vs. USGS water demand" |> sprintf(tethys_demand_category, h, demand_type),
  #   color_trans = "log10"
  # )
  # p_map_ave_diff_huc_log
  # "figures/huc%02d-%s-%s-diff-usgs-tethys-log.png" |>
  #   sprintf(h, tethys_demand_category, demand_type) |>
  #   ggsave(p_map_ave_diff_huc_log, width = 10, height = 6)

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
  "figures/huc%02d-scatter-usgs-tethys.png" |>
    sprintf(h) |>
    ggsave(p_scatter, width = 8, height = 5)

  # p_scatter_log = ave_diff_huc |> ggplot() +
  #   geom_point(aes(mean_usgs, mean_tethys)) +
  #   geom_abline(slope = 1) +
  #   geom_text(aes(x, y, label = label), data = cordf) +
  #   theme_minimal() +
  #   scale_x_log10() +
  #   scale_y_log10()
  # p_scatter_log
  # "figures/huc%02d-%s-%s-scatter-usgs-tethys-log.png" |>
  #   sprintf(h, tethys_demand_category, demand_type) |>
  #   ggsave(p_scatter, width = 6, height = 6)
  # # stop()

  # monthly plots
  # p_ave_diff_month_huc = huc_shape |>
  #   left_join(ave_diff_monthly_huc, by = "huc") |>
  #   # filter(mean_diff > 0) |>
  #   ggplot(aes(fill = mean_diff)) +
  #   geom_sf(linewidth = 0.01) +
  #   facet_wrap(~month, nrow = 4) +
  #   scale_fill_scico(
  #     "Average difference\nin water %s\n[USGS-Tethys]\n(km^3)" |>
  #       sprintf(demand_type),
  #     palette = "roma",
  #     midpoint = 0
  #   ) +
  #   labs(
  #     title = "HUC %s monthly Tethys %s vs. USGS water demand" |>
  #       sprintf(h, demand_type)
  #   ) +
  #   theme_void()
  # p_ave_diff_month_huc
  # "figures/huc%02d-%s-%s-diff-monthly-usgs-tethys.png" |>
  #   sprintf(h, tethys_demand_category, demand_type) |>
  #   ggsave(p_ave_diff_month_huc, width = 10, height = 6)

  # stop()
  # if (h == 2) {
  #   p_boxplot = demand_huc |> ggplot() +
  #     geom_boxplot(aes(factor(month), diff)) +
  #     facet_wrap(~huc, nrow = 3, scale='free_y') +
  #     theme_bw() +
  #     scale_fill_viridis_d(option = "F") +
  #     theme(panel.grid.minor = element_blank()) +
  #     labs(y = "Difference in water %s [USGS-Tethys] (MGD)" |> sprintf(demand_type), x = "Month")
  #   p_boxplot
  #   "figures/huc-%s-%s-diff-boxplot-monthly-usgs-tethys.png" |>
  #     sprintf(h, demand_type) |>
  #     ggsave(p_boxplot, width = 12, height = 5)
  # }
}
