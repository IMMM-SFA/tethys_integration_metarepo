library(tidyverse)
library(sf)
library(scico)

options(
  readr.show_progress = FALSE,
  readr.show_col_types = FALSE,
  pillar.width = 1000,
  dplyr.summarise.inform = FALSE
)

P = yaml::read_yaml("paths.yml")

huc12_shape <- P$huc12_shapefile |>
  st_read(quiet = TRUE) |>
  rename(huc = huc12) |>
  mutate(huc2 = substr(huc, 1, 2)) |>
  # only include conus huc 2's
  filter(huc2 %in% sprintf("%02d", 1:18)) #|>

# units=MGD
# pscuftot = public supply consumptive use fresh water total (surface + ground)
usgs_public_supply_cu <-
  P$usgs_public_supply_cu |>
  read_csv() |>
  mutate(datetime = ym(year_month)) |>
  select(-year_month) |>
  pivot_longer(-datetime, values_to = "usgs_cu_mgd", names_to = "huc12") |>
  mutate(huc12 = ifelse(nchar(huc12) == 11, paste0("0", huc12), huc12))

usgs_public_supply_cu |>
  write_csv("data/usgs_public_supply_consumption_huc12_monthly_2009-2020.csv")

# units=MGD
usgs_public_supply_wd <-
  P$usgs_public_supply_wd |>
  read_csv() |>
  mutate(datetime = ym(year_month)) |>
  select(-year_month) |>
  pivot_longer(-datetime, values_to = "usgs_wd_mgd", names_to = "huc12") |>
  mutate(huc12 = ifelse(nchar(huc12) == 11, paste0("0", huc12), huc12))

usgs_public_supply_wd |>
  write_csv("data/usgs_public_supply_withdrawal_huc12_monthly_2000-2020.csv")

# units=MGD
# irrcuftot = irrigation consumptive use fresh water total (surface + ground)
usgs_irrigation_cu <-
  P$usgs_irrigation_cu |>
  read_csv() |>
  mutate(datetime = ym(year_month)) |>
  select(-year_month) |>
  pivot_longer(-datetime, values_to = "usgs_cu_mgd", names_to = "huc12") |>
  mutate(huc12 = ifelse(nchar(huc12) == 11, paste0("0", huc12), huc12))

usgs_irrigation_cu |>
  write_csv("data/usgs_irrigation_consumption_huc12_monthly_2000-2020.csv")

# units=MGD
usgs_irrigation_wd <-
  P$usgs_irrigation_wd |>
  read_csv() |>
  mutate(datetime = ym(year_month)) |>
  select(-year_month) |>
  pivot_longer(-datetime, values_to = "usgs_wd_mgd", names_to = "huc12") |>
  mutate(huc12 = ifelse(nchar(huc12) == 11, paste0("0", huc12), huc12))

usgs_irrigation_wd |>
  write_csv("data/usgs_irrigation_withdrawal_huc12_monthly_2000-2020.csv")

# units=MGD
# tecuftot = thermoelectric consumptive use fresh water total (surface + ground)
usgs_thermoelectric_cu <-
  P$usgs_thermoelectric |>
  read_csv() |>
  mutate(datetime = ym(year_month), usgs_cu_mgd = tecuftot_mgd) |>
  select(datetime, huc12 = huc12_id, usgs_cu_mgd) |>
  # pivot_longer(-datetime, values_to = "usgs_cu_mgd", names_to = "huc12") |>
  mutate(huc12 = ifelse(nchar(huc12) == 11, paste0("0", huc12), huc12))

usgs_thermoelectric_cu |>
  write_csv("data/usgs_thermoelectric_consumption_huc12_monthly_2008-2020.csv")

# units=MGD
# tecuftot = thermoelectric consumptive use fresh water total (surface + ground)
usgs_thermoelectric_wd <-
  P$usgs_thermoelectric |>
  read_csv() |>
  mutate(datetime = ym(year_month), usgs_wd_mgd = tewdftot_mgd + tewdssw_mgd) |>
  select(datetime, huc12 = huc12_id, usgs_wd_mgd) |>
  # pivot_longer(-datetime, values_to = "usgs_cu_mgd", names_to = "huc12") |>
  mutate(huc12 = ifelse(nchar(huc12) == 11, paste0("0", huc12), huc12))

usgs_thermoelectric_wd |>
  write_csv("data/usgs_thermoelectric_withdrawal_huc12_monthly_2008-2020.csv")

# usgs_thermoelectric <- paste0(
#   "/Volumes/data/tethys/USGS-thermoelectric/galanter_and_others_2023/",
#   "4_model_results/published_monthly_thermoelectric_water_use_estimates_2008-2020.csv"
# ) |>
#   read_csv()

# usgs_thermoelectric_total <- usgs_thermoelectric |>
#   mutate(datetime = sprintf("%s-%02d-01", YEAR, Month)) |>
#   # filter(!str_detect(coolingType, "saline")) |>
#   filter(ModelType != "OS") |>
#   rename(huc12 = huc_12) |>
#   group_by(datetime, huc12) |>
#   summarise(usgs_cu_mgd = sum(cu_mgd), usgs_wd_mgd = sum(wd_mgd))

# usgs_thermoelectric_total |>
#   write_csv(
#     "data/usgs_thermoelectric_consumption_withdrawl_huc12_monthly_2008-2020.csv"
#   )

# tethys_electricity_subsectors = c('electricity_biomass',
#  'electricity_coal',
#  'electricity_gas',
#  'electricity_geothermal',
#  'electricity_nuclear',
#  'electricity_refined liquids',
#  'electricity_solar')

# usgs_thermoelectric_coal <- usgs_thermoelectric |>
#   filter(Plant.level_dom_fuel == "coal") |>
#   mutate(datetime = sprintf("%s-%02d-01", YEAR, Month)) |>
#   # filter(!str_detect(coolingType, "saline")) |>
#   filter(ModelType != "OS") |>
#   rename(huc12 = huc_12) |>
#   group_by(datetime, huc12) |>
#   summarise(usgs_cu_mgd = mean(cu_mgd), usgs_wd_mgd = mean(wd_mgd))

# usgs_thermoelectric_coal |>
#   write_csv(
#     "data/usgs_thermoelectric_coal_consumption_withdrawl_huc12_monthly_2008-2020.csv"
#   )

# usgs_thermoelectric_nuclear <- usgs_thermoelectric |>
#   filter(Plant.level_dom_fuel == "nuclear") |>
#   mutate(datetime = sprintf("%s-%02d-01", YEAR, Month)) |>
#   # filter(!str_detect(coolingType, "saline")) |>
#   filter(ModelType != "OS") |>
#   rename(huc12 = huc_12) |>
#   group_by(datetime, huc12) |>
#   summarise(usgs_cu_mgd = mean(cu_mgd), usgs_wd_mgd = mean(wd_mgd))

# usgs_thermoelectric_nuclear |>
#   write_csv(
#     "data/usgs_thermoelectric_nuclear_consumption_withdrawl_huc12_monthly_2008-2020.csv"
#   )

# usgs_thermoelectric_gas <- usgs_thermoelectric |>
#   filter(Plant.level_dom_fuel == "gas") |>
#   mutate(datetime = sprintf("%s-%02d-01", YEAR, Month)) |>
#   # filter(!str_detect(coolingType, "saline")) |>
#   filter(ModelType != "OS") |>
#   rename(huc12 = huc_12) |>
#   group_by(datetime, huc12) |>
#   summarise(usgs_cu_mgd = mean(cu_mgd), usgs_wd_mgd = mean(wd_mgd))

# usgs_thermoelectric_gas |>
#   write_csv(
#     "data/usgs_thermoelectric_gas_consumption_withdrawl_huc12_monthly_2008-2020.csv"
#   )
