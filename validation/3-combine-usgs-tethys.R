library(tidyverse)
library(sf)
library(ncdf4)
library(scico)

options(
  readr.show_progress = FALSE,
  readr.show_col_types = FALSE,
  pillar.width = 1000,
  dplyr.summarise.inform = FALSE
)

input_data_dir = 'data'

# unit conversions
km3_per_year_TO_mgd = 264172.05124 / 365
mgd_TO_km3_per_year = 1 / km3_per_year_TO_mgd
# mgd_to_km3_per_year = (264172.05 / (365 / 12))
km3_in_one_million_gallons = 3.785412e-06 # 1e6/264172052358.15

demand_categories = c("Irrigation", "Electricity", "Domestic")
demand_types = c("withdrawals", "consumption")

# units=MGD
usgs_public_supply_cu_wd = read_csv(
  "data/usgs_public_supply_consumption_huc12_monthly_2009-2020.csv"
) |>
  inner_join(
    read_csv("data/usgs_public_supply_withdrawal_huc12_monthly_2000-2020.csv"),
    by = join_by(datetime, huc12)
  )

usgs_irrigation_cu_wd = read_csv(
  "data/usgs_irrigation_consumption_huc12_monthly_2000-2020.csv"
) |>
  inner_join(
    read_csv("data/usgs_irrigation_withdrawal_huc12_monthly_2000-2020.csv"),
    by = join_by(datetime, huc12)
  )

usgs_thermoelectric_cu_wd = read_csv(
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
    huc_name = paste0("huc", h)

    message(huc_name)

    for (demand_type in demand_types) {
      message(demand_type)

      column = ifelse(
        demand_type == "withdrawals",
        "usgs_wd_mgd",
        "usgs_cu_mgd"
      )
      usgs_demand = if (tethys_demand_category == "Irrigation") {
        usgs_irrigation_cu_wd
      } else if (tethys_demand_category == "Domestic") {
        usgs_public_supply_cu_wd
      } else if (tethys_demand_category == "Electricity") {
        usgs_thermoelectric_cu_wd
      }

      cache_output_fn = "%s/huc%02d-%s-%s-usgs-tethys.csv" |>
        sprintf(input_data_dir, h, tethys_demand_category, demand_type)

      # if (file.exists(cache_output_fn)) {
      usgs_demand_huc = usgs_demand |>
        select(datetime, huc12, !!as.name(column)) |>
        rename(usgs_mgd = !!as.name(column)) |>
        mutate(year = year(datetime)) |>
        mutate(usgs_mgd = ifelse(is.na(usgs_mgd), 0, usgs_mgd)) |>
        mutate(usgs_km3 = usgs_mgd / (264172.05 / (365 / 12))) |>
        mutate(huc = substr(huc12, 1, h)) |>
        group_by(datetime, huc) |>
        # spatial average
        summarise(
          usgs_mgd = sum(usgs_mgd),
          usgs_km3 = sum(usgs_km3)
        )

      if (tethys_demand_category == 'Irrigation') {
        # loss_postfix = '_with_losses'
        loss_postfix = ''
      } else {
        loss_postfix = ''
      }

      tethys_demand_huc = "%s/tethys_%s_%s_huc%s%s.csv" |>
        sprintf(
          input_data_dir,
          tethys_demand_category,
          demand_type,
          h,
          loss_postfix
        ) |>
        read_csv() |>
        mutate(datetime = ymd(sprintf("%s-%s-01", year, month))) |>
        # rename(huc = as.name(!!huc_name)) |>
        select(
          datetime,
          huc,
          tethys_mgd = demand_mgd,
          tethys_km3 = demand_km3
        )

      demand_huc = usgs_demand_huc |>
        inner_join(tethys_demand_huc, by = join_by(datetime, huc)) |>
        mutate(
          # diff = usgs_km3_per_month - tethys_km3_per_month,
          diff = usgs_km3 - tethys_km3,
          pdiff = abs(usgs_km3 - tethys_km3) /
            ((usgs_km3 + tethys_km3) / 2) *
            100,
          pdiff = ifelse(is.na(pdiff), 0, pdiff),
          month = month(datetime)
        )

      demand_huc |> write_csv(cache_output_fn)
      # }
    }
  }
}
