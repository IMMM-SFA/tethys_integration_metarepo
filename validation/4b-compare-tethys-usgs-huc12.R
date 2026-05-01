# Compare Tethys vs USGS water-use estimates at the HUC12 scale. USGS
# public-supply and irrigation data are reported at HUC12 (thermoelectric
# is per-plant and aggregated up); this script produces fine-scale
# agreement plots and distribution diagnostics complementary to 4a.

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


km3_per_year_TO_Mgal_per_day <- 264172.1 / 365
km3_in_one_million_gallons <- 3.785412e-06 # 1e6/264172052358.15

demand_categories = c("Irrigation", "Electricity", "Domestic")
demand_types = c("withdrawals", "consumption")

# units=MGD
usgs_public_supply_cu_wd <- read_csv(
  "data/usgs_public_supply_consumption_huc12_monthly_2009-2020.csv"
) |>
  inner_join(
    read_csv("data/usgs_public_supply_withdrawal_huc12_monthly_2000-2020.csv"),
    by = join_by(datetime, huc12)
  )
usgs_irrigation_cu_wd <- read_csv(
  "data/usgs_irrigation_consumption_huc12_monthly_2000-2020.csv"
) |>
  inner_join(
    read_csv("data/usgs_irrigation_withdrawal_huc12_monthly_2000-2020.csv"),
    by = join_by(datetime, huc12)
  )
# usgs_thermelectric_cu_wd <- read_csv(
#   "data/usgs_thermoelectric_consumption_withdrawl_huc12_monthly_2008-2020.csv"
# )

usgs_thermoelectric_cu_wd <- read_csv(
  "data/usgs_thermoelectric_consumption_huc12_monthly_2008-2020.csv"
) |>
  inner_join(
    read_csv("data/usgs_thermoelectric_withdrawal_huc12_monthly_2008-2020.csv"),
    by = join_by(datetime, huc12)
  )

for (tethys_demand_category in demand_categories) {
  # for (tethys_demand_category in c("Domestic")) {
  #
  message(tethys_demand_category)

  for (h in c(2, 4, 6, 8)) {
    #
    huc_name <- paste0("huc", h)

    message(huc_name)

    # huc_shape <- "/Volumes/data/shapefiles/HUC%s/HUC%s.shp" |>
    #   sprintf(h, h) |>
    #   st_read(quiet = TRUE) |>
    #   rename(huc = as.name(!!huc_name)) |>
    #   mutate(huc2 = substr(huc, 1, 2)) |>
    #   # only include conus huc 2's
    #   filter(huc2 %in% sprintf("%02d", 1:18)) #|>
    # simplify the polygons for faster plotting
    # need to project before simplifying
    # st_transform(54032) |> # azimuthal equidistant
    # st_transform("ESRI:102003") |> # USA_Contiguous_Albers_Equal_Area_Conic
    # st_simplify(dTolerance = .005) |>
    # st_transform(4326) # back to lat/lon

    for (demand_type in demand_types) {
      # there is no usgs public supply consumptive use at the moment
      # if (demand_type == "consumption" & tethys_demand_category == "Domestic") next
      # if (demand_type != "withdrawals" | tethys_demand_category != "Domestic") next

      message(demand_type)

      column <- ifelse(
        demand_type == "withdrawals",
        "usgs_wd_mgd",
        "usgs_cu_mgd"
      )
      usgs_demand <- if (tethys_demand_category == "Irrigation") {
        usgs_irrigation_cu_wd
      } else if (tethys_demand_category == "Domestic") {
        usgs_public_supply_cu_wd
      } else if (tethys_demand_category == "Electricity") {
        usgs_thermoelectric_cu_wd
      }

      cache_output_fn = "data/huc%02d-%s-%s-usgs-tethys.csv" |>
        sprintf(h, tethys_demand_category, demand_type)

      if (!file.exists(cache_output_fn)) {
        # annual average, then average across all years for each huc
        usgs_demand_huc <- usgs_demand |>
          select(datetime, huc12, !!as.name(column)) |>
          rename(usgs_mgd = !!as.name(column)) |>
          mutate(year = year(datetime)) |>
          mutate(usgs_mgd = ifelse(is.na(usgs_mgd), 0, usgs_mgd)) |>
          mutate(usgs_km3 = usgs_mgd / (264172.05 / (365 / 12))) |>
          # group_by(huc12, year) |>
          # # average of all months for each year at each huc12
          # summarise(usgs_mgd = mean(usgs_mgd)) |>
          # group_by(huc12) |>
          # # average of all years at each huc 12
          # summarise(usgs_mgd = mean(usgs_mgd)) |>
          mutate(huc = substr(huc12, 1, h)) |>
          group_by(datetime, huc) |>
          # spatial average
          summarise(
            usgs_mgd = sum(usgs_mgd),
            usgs_km3 = sum(usgs_km3)
          )

        # usgs_2015 = usgs_demand_huc |>
        #   # mutate(usgs_km3) |>
        #   mutate(year = year(datetime)) |>
        #   filter(year == 2015) |>
        #   group_by(huc, year) |>
        #   summarise(usgs_mgd = sum(usgs_mgd)) |>
        #   mutate(usgs_mgy=usgs_mgd*365)

        tethys_demand_huc <- "/Volumes/data/tethys/tethys_%s_%s_huc%s.csv" |>
          sprintf(tethys_demand_category, demand_type, h) |>
          read_csv() |>
          mutate(datetime = ymd(sprintf("%s-%s-01", year, month))) |>
          # rename(huc = as.name(!!huc_name)) |>
          select(
            datetime,
            huc,
            tethys_mgd = demand_mgd,
            tethys_km3 = demand_km3
          )

        demand_huc <- usgs_demand_huc |>
          inner_join(tethys_demand_huc, by = join_by(datetime, huc)) |>
          mutate(
            # diff = usgs_km3_per_month - tethys_km3_per_month,
            diff = usgs_mgd - tethys_mgd,
            pdiff = abs(usgs_mgd - tethys_mgd) / ((usgs_mgd + tethys_mgd) / 2) * 100,
            pdiff = ifelse(is.na(pdiff), 0, pdiff),
            month = month(datetime)
          )

        demand_annual <- demand_huc |>
          mutate(year = year(datetime)) |>
          group_by(year) |>
          summarise(
            usgs_km3 = sum(usgs_km3),
            tethys_km3 = sum(tethys_km3),
            usgs_mgd = sum(usgs_mgd),
            tethys_mgd = sum(tethys_mgd),
            mgd_ratio = usgs_mgd / tethys_mgd,
            km3_ratio = usgs_km3 / tethys_km3
          )

        huc_shape <- "/Volumes/data/shapefiles/HUC%s/HUC%s.shp" |>
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

        for (demand_type in c("withdrawals", "consumption")) {
          # ave_diff_huc <- demand_huc |>
          #   mutate(year = year(datetime)) |>
          #   group_by(huc, year) |>
          #   summarise(
          #     mean_usgs = mean(usgs_mgd),
          #     mean_tethys = mean(tethys_mgd),
          #     mean_diff = mean(diff),
          #     mean_pdiff = mean(pdiff)
          #   ) |>
          #   group_by(huc) |>
          #   summarise(
          #     mean_usgs = mean(mean_usgs),
          #     mean_tethys = mean(mean_tethys),
          #     mean_diff = mean(mean_diff),
          #     mean_pdiff = mean(mean_pdiff)
          #   )

          ave_diff_huc <- demand_huc |>
            mutate(year = year(datetime)) |>
            group_by(huc, year) |>
            summarise(
              sum_usgs = sum(usgs_km3),
              sum_tethys = sum(tethys_km3),
              sum_diff = sum_usgs - sum_tethys,
              sum_pdiff = abs(sum_usgs - sum_tethys) /
                ((sum_usgs + sum_tethys) / 2) *
                100
            ) |>
            group_by(huc) |>
            summarise(
              mean_usgs = mean(sum_usgs),
              mean_tethys = mean(sum_tethys),
              mean_diff = mean(sum_diff),
              mean_pdiff = mean(sum_pdiff)
            )

          ave_diff_monthly_huc <- demand_huc |>
            mutate(month = month(datetime)) |>
            group_by(huc, month) |>
            summarise(
              mean_usgs = mean(usgs_km3),
              mean_tethys = mean(tethys_km3),
              mean_diff = mean_usgs - mean_tethys,
              mean_pdiff = abs(mean_usgs - mean_tethys) /
                ((mean_usgs + mean_tethys) / 2) *
                100
            )

          # --------------------------------------------------
          # annual total timeseries
          # --------------------------------------------------
          p_annual_total <- ggplot(
            demand_annual |> pivot_longer(c(usgs_km3, tethys_km3))
          ) +
            geom_bar(
              aes(year, value, fill = name),
              position = "dodge",
              stat = "identity",
              color = "black"
            ) +
            theme_bw() +
            scale_fill_viridis_d("Dataset", option = "G") +
            labs(x = "", y = "Water Demand [km^3/year]")
          p_annual_total
          "figures/huc%02d-%s-%s-usgs-tethys-annual-total.png" |>
            sprintf(h, tethys_demand_category, demand_type) |>
            ggsave(p_annual_total, width = 10, height = 6)

          # --------------------------------------------------
          # aggregated huc map
          # --------------------------------------------------
          plot_huc_map <- function(
            data,
            plot_variable,
            title,
            color_trans = "identity"
          ) {
            ggplot(data, aes(fill = !!as.name(plot_variable))) +
              geom_sf(linewidth = ifelse(h > 8, .001, .01)) +
              facet_wrap(~source) +
              scale_fill_viridis_c(
                "Average annual\nwater %s\n(km^3)" |> sprintf(demand_type),
                option = "G",
                trans = color_trans,
                direction = -1
              ) +
              labs(title = title) +
              theme_void() +
              theme(
                legend.position = "inside",
                legend.position.inside = c(.5, .2),
                panel.grid = element_blank()
              )
          }
          huc_agg_data <- huc_shape |>
            left_join(ave_diff_huc, by = "huc") |>
            pivot_longer(c(mean_usgs, mean_tethys), names_to = "source")

          p_map_ave_huc <- plot_huc_map(
            huc_agg_data,
            "value",
            "Annual ave %s HUC %s Tethys %s vs. USGS water demand" |>
              sprintf(tethys_demand_category, h, demand_type)
          )
          p_map_ave_huc
          "figures/huc%02d-%s-%s-usgs-tethys.png" |>
            sprintf(h, tethys_demand_category, demand_type) |>
            ggsave(p_map_ave_huc, width = 20, height = 6)

          # p_map_ave_huc_log <- plot_huc_map(huc_agg_data, "value",
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
          huc_diff_agg_data <- huc_shape |>
            left_join(ave_diff_huc, by = "huc")

          plot_huc_map_diff <- function(
            data,
            title,
            diff_type = "diff",
            color_trans = "identity"
          ) {
            color_label <- sprintf(
              "Average annual\n%sdifference in\nwater %s\n[USGS-Tethys]\n(km^3)",
              ifelse(diff_type == "pdiff", "% ", ""),
              sprintf(demand_type)
            )
            ggplot(data, aes(fill = abs(!!as.name(paste0("mean_", diff_type))))) +
              geom_sf(linewidth = ifelse(h > 8, .001, .01)) +
              # scale_fill_viridis_c("Average difference\nin water demand\n[USGS-Tethys]\n(MGD)", option = "G") +
              # https://stackoverflow.com/questions/37482977/
              # what-is-a-good-palette-for-divergent-colors-in-r-or-can-viridis-and-magma-b
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
                legend.position = "inside",
                legend.position.inside = c(.9, .2),
                panel.grid = element_blank()
              )
          }

          p_map_ave_diff_huc <- plot_huc_map_diff(
            huc_diff_agg_data,
            "Annual ave %s HUC %s Tethys %s vs. USGS water demand" |>
              sprintf(tethys_demand_category, h, demand_type)
          )
          p_map_ave_diff_huc
          "figures/huc%02d-%s-%s-diff-usgs-tethys.png" |>
            sprintf(h, tethys_demand_category, demand_type) |>
            ggsave(p_map_ave_diff_huc, width = 10, height = 6)

          p_map_ave_pdiff_huc <- plot_huc_map_diff(
            huc_diff_agg_data,
            "Annual ave %s HUC %s Tethys %s vs. USGS water demand" |>
              sprintf(tethys_demand_category, h, demand_type),
            "pdiff"
          )
          p_map_ave_pdiff_huc
          "figures/huc%02d-%s-%s-pdiff-usgs-tethys.png" |>
            sprintf(h, tethys_demand_category, demand_type) |>
            ggsave(p_map_ave_pdiff_huc, width = 10, height = 6)

          # p_map_ave_diff_huc_log <- plot_huc_map_diff(
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
          cordf <- ave_diff_huc |>
            summarise(
              x = min(mean_usgs),
              y = max(mean_tethys),
              label = paste0("r=", cor(mean_tethys, mean_usgs) |> round(3))
            )
          p_scatter <- ave_diff_huc |>
            ggplot() +
            geom_point(aes(mean_usgs, mean_tethys)) +
            geom_abline(slope = 1) +
            geom_text(aes(x, y, label = label), data = cordf) +
            theme_minimal()
          p_scatter
          "figures/huc%02d-%s-%s-scatter-usgs-tethys.png" |>
            sprintf(h, tethys_demand_category, demand_type) |>
            ggsave(p_scatter, width = 6, height = 6)

          # p_scatter_log <- ave_diff_huc |> ggplot() +
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
          p_ave_diff_month_huc <- huc_shape |>
            left_join(ave_diff_monthly_huc, by = "huc") |>
            # filter(mean_diff > 0) |>
            ggplot(aes(fill = mean_diff)) +
            geom_sf(linewidth = 0.01) +
            facet_wrap(~month, nrow = 4) +
            scale_fill_scico(
              "Average difference\nin water %s\n[USGS-Tethys]\n(km^3)" |>
                sprintf(demand_type),
              palette = "roma",
              midpoint = 0
            ) +
            labs(
              title = "HUC %s monthly Tethys %s vs. USGS water demand" |>
                sprintf(h, demand_type)
            ) +
            theme_void()
          p_ave_diff_month_huc
          "figures/huc%02d-%s-%s-diff-monthly-usgs-tethys.png" |>
            sprintf(h, tethys_demand_category, demand_type) |>
            ggsave(p_ave_diff_month_huc, width = 10, height = 6)

          # stop()
          # if (h == 2) {
          #   p_boxplot <- demand_huc |> ggplot() +
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
      }
    }
  }
}
