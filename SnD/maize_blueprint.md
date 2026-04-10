# Maize Blueprint

This document starts the Maize S&D framework in the same structured way as Wheat and will be extended step by step as the Maize system is built out.

## Step 1 - Define Framework First

Before loading any Maize data, the framework is locked so that every later DB, formula, and reporting table follows the same conventions.

## Step 1 overview

| Decision | Maize | Why it matters |
|---|---|---|
| `Commodity` | `Maize / Corn` | keeps the framework explicit for trade mapping, reporting, and model scope |
| `Geography` | `India + Global (US, Brazil, Argentina, Ukraine)` | captures the domestic Maize balance plus the global exporters and benchmark influences that move Indian prices |
| `Time horizon` | `Historical (10 years) + Current season + 1-year forecast` | gives enough history for structural analysis while keeping the forward window practical |
| `Frequency` | `Annual + Monthly` | annual crop-year balances anchor the system while monthly updates support market tracking |
| `Crop year` | `Kharif-dominant cycle, reported as Oct-Sep, with rabi treated as a secondary seasonal layer` | reflects how Indian Maize supply actually arrives and how domestic availability evolves through the year |
| `HS code` | `1005` | ensures imports, exports, and customs-linked trade analysis stay mapped to the correct Maize code |

## Step 1 framework rules

| Rule | Definition |
|---|---|
| `Primary India balance frame` | use crop-year logic anchored to the kharif-dominant Maize cycle |
| `Monthly reporting frame` | store month-level observations in `YYYY-MM-01` format for clean joins across DBs |
| `Global comparison set` | default external producer/exporter group is `US, Brazil, Argentina, Ukraine` |
| `Forecast style` | keep the first Maize version aligned to `1-year forward` reporting so it stays comparable with Wheat |
| `Trade mapping` | all Maize trade pulls should map back to `HS 1005` |
| `Output philosophy` | build the Maize stack in the same order as Wheat so the final reporting and ML layers remain comparable |

## Step 1 outputs we will build toward

| Future Step | Intended Maize Output |
|---|---|
| `Step 2` | 6W commodity profile and supply-side foundation |
| `Step 3` | demand-side framework with feed, poultry cycle, industrial use, exports, and substitution context |
| `Step 4` | annual balance sheet and stocks-to-use ratio |
| `Step 5` | Maize price-driver framework |
| `Step 6` | source collection plan |
| `Step 7` | bilateral trade-flow analysis |
| `Step 8` | Bull / Base / Bear scenarios |
| `Step 9` | risk register |
| `Step 10` | dashboard and report output structure |
| `Step 11` | model integration |

## Step 1 short summary

| Item | Status |
|---|---|
| `Commodity defined` | `Done` |
| `Geography defined` | `Done` |
| `Time horizon defined` | `Done` |
| `Frequency defined` | `Done` |
| `Crop-year logic defined` | `Done` |
| `HS code defined` | `Done` |

## Next recommended step

Build `Step 2 - 6W Commodity Profile` and carry that into the existing Maize supply layer with:

- key Maize-producing states
- product and grade context
- seasonal crop calendar
- key actors and demand users
- acreage, yield, production, stocks, and imports
- global exporter context led by the US and Brazil

# Step 2 - 6W Commodity Profile

This section captures the Maize 6W commodity profile layer that sits ahead of the supply-demand build.

## Maize 6W profile workspace

- Folder: [D:/ncel2/ncel-commodity-pricing/SnD/profile/maize](D:/ncel2/ncel-commodity-pricing/SnD/profile/maize)
- DB: [D:/ncel2/ncel-commodity-pricing/SnD/profile/maize/maize_6w_profile.db](D:/ncel2/ncel-commodity-pricing/SnD/profile/maize/maize_6w_profile.db)
- Builder: [D:/ncel2/ncel-commodity-pricing/SnD/profile/maize/build_maize_6w_profile.py](D:/ncel2/ncel-commodity-pricing/SnD/profile/maize/build_maize_6w_profile.py)

## Tables created

| Table | Purpose |
|---|---|
| `maize_source_inventory` | source register for the Maize profile layer |
| `maize_commodity_master` | Maize master row |
| `maize_hs_code_register` | HS code reference |
| `maize_crop_year_calendar` | crop-year and demand-cycle calendar |
| `maize_six_w_output` | document-aligned Where / What / When / How Much / Why / Whom output |
| `maize_national_trend_10y` | 10-year Maize area, production, yield, and MSP trend |
| `maize_state_production_map` | core-state Maize production map |
| `maize_harvest_calendar` | sowing and harvest windows by state and season |
| `maize_key_player_register` | key institutions and market actors |

## Current table counts

| Table | Rows |
|---|---:|
| `maize_source_inventory` | `5` |
| `maize_commodity_master` | `1` |
| `maize_hs_code_register` | `1` |
| `maize_crop_year_calendar` | `7` |
| `maize_six_w_output` | `6` |
| `maize_national_trend_10y` | `36` |
| `maize_state_production_map` | `6` |
| `maize_harvest_calendar` | `12` |
| `maize_key_player_register` | `6` |

## Requested extracts from profile DB

### First 10 rows from `maize_national_trend_10y`

| Metric Date | Marketing Year | Metric Name | Value | Unit | Source |
|---|---|---|---:|---|---|
| `2016-03-31` | `2015-16` | `Maize gross area` | `8.8` | `million_hectare` | `Economic Survey Statistical Appendix` |
| `2016-03-31` | `2015-16` | `Maize production` | `22.6` | `million_tonnes` | `Economic Survey Statistical Appendix` |
| `2016-03-31` | `2015-16` | `Maize yield per hectare` | `2563.0` | `kg_per_hectare` | `Economic Survey Statistical Appendix` |
| `2017-03-31` | `2016-17` | `Maize gross area` | `9.6` | `million_hectare` | `Economic Survey Statistical Appendix` |
| `2017-03-31` | `2016-17` | `Maize production` | `25.9` | `million_tonnes` | `Economic Survey Statistical Appendix` |
| `2017-03-31` | `2016-17` | `Maize yield per hectare` | `2689.0` | `kg_per_hectare` | `Economic Survey Statistical Appendix` |
| `2018-03-31` | `2017-18` | `Maize gross area` | `9.4` | `million_hectare` | `Economic Survey Statistical Appendix` |
| `2018-03-31` | `2017-18` | `Maize production` | `28.8` | `million_tonnes` | `Economic Survey Statistical Appendix` |
| `2018-03-31` | `2017-18` | `Maize yield per hectare` | `3065.0` | `kg_per_hectare` | `Economic Survey Statistical Appendix` |
| `2019-03-31` | `2018-19` | `Maize gross area` | `9.0` | `million_hectare` | `Economic Survey Statistical Appendix` |

### Full `maize_crop_year_calendar`

| Calendar Type | Stage Name | Start Month | End Month | Geography Scope | Notes |
|---|---|---:|---:|---|---|
| `demand_cycle` | `Poultry feed demand cycle` | `1` | `12` | `India feed belt` | `Feed demand is continuous but varies with poultry placement and price spreads.` |
| `crop_stage` | `Rabi harvest` | `2` | `4` | `Rabi Maize pockets` | `Secondary harvest window that smooths supply after kharif.` |
| `crop_stage` | `Kharif sowing` | `6` | `7` | `India Maize belt` | `Monsoon-linked sowing window for the dominant Maize crop.` |
| `crop_stage` | `Kharif vegetative and grain-fill` | `8` | `9` | `India Maize belt` | `Weather-sensitive crop development period.` |
| `crop_stage` | `Kharif harvest and arrivals` | `9` | `1` | `India Maize belt` | `Main domestic arrival window.` |
| `marketing_year` | `India Maize crop year` | `10` | `9` | `India` | `Oct-Sep crop-year view aligned to kharif-dominant Maize availability.` |
| `crop_stage` | `Rabi sowing` | `10` | `12` | `Rabi Maize pockets` | `Secondary seasonal crop in states like Bihar and Telangana.` |

## 6W output

| Dimension | Item Value |
|---|---|
| `Where` | `Karnataka; Madhya Pradesh; Maharashtra; Bihar; Telangana; Rajasthan; Andhra Pradesh; Uttar Pradesh` |
| `What` | `Feed maize; industrial maize; starch and processing-grade maize; poultry-linked demand crop` |
| `When` | `Kharif sowing Jun-Jul; kharif harvest and arrivals Sep-Jan; rabi harvest Feb-Apr; Brazil safrinha and US crop cycles shape global price timing` |
| `How Much` | `Area (million hectare), production (million tonnes), yield (kg/ha), imports, exports, MSP` |
| `Why` | `Poultry feed demand; monsoon distribution; kharif acreage; US corn crop; Brazil safrinha crop; export policy; ethanol and industrial demand signals` |
| `Whom` | `Farmers; feed millers; poultry integrators; starch industry; ethanol-linked buyers; traders; exporters and importers` |

## Step 2 short summary

| Item | Status |
|---|---|
| `Maize profile DB created` | `Done` |
| `6W output loaded` | `Done` |
| `10-year Maize trend loaded` | `Done` |
| `State map loaded` | `Done` |
| `Harvest calendar loaded` | `Done` |
| `Key player register loaded` | `Done` |

# Step 2 — Build Supply Side

This section sets up the Maize supply-side workspace and the initial supply factor dictionary, using the same DB pattern as Wheat.

## Maize supply workspace

- Folder: [D:\ncel2\ncel-commodity-pricing\SnD\supply\maize](D:/ncel2/ncel-commodity-pricing/SnD/supply/maize)
- DB: [D:\ncel2\ncel-commodity-pricing\SnD\supply\maize\maize_supply_factors.db](D:/ncel2/ncel-commodity-pricing/SnD/supply/maize/maize_supply_factors.db)
- Builder: [D:\ncel2\ncel-commodity-pricing\SnD\supply\maize\build_maize_supply_store.py](D:/ncel2/ncel-commodity-pricing/SnD/supply/maize/build_maize_supply_store.py)

## Tables created

| Table | Purpose |
|---|---|
| `maize_factor_definitions` | Maize supply factor dictionary |
| `maize_source_inventory` | source websites and cadence |
| `maize_factor_status` | planned monthly/source status for each factor |
| `maize_factor_values` | future annual or point-value storage |
| `maize_factor_monthly_values` | future monthly Maize supply panel |

## Current table counts

| Table | Rows |
|---|---:|
| `maize_factor_definitions` | `11` |
| `maize_source_inventory` | `6` |
| `maize_factor_status` | `11` |
| `maize_factor_values` | `48` |
| `maize_factor_monthly_values` | `2040` |

## Maize supply factors

| Factor | Group | Monthly Status | Data From | Data To | Rows | Source | Method |
|---|---|---|---|---|---:|---|---|
| `Acreage (sown area)` | `area` | `annual_only` | `2016-04-01` | `2026-03-01` | `120` | `Economic Survey Statistical Appendix + current snapshot` | `annual_hold_constant_monthly` |
| `Yield per hectare` | `yield` | `annual_only` | `2016-04-01` | `2026-03-01` | `120` | `Economic Survey Statistical Appendix + current snapshot` | `annual_hold_constant_monthly` |
| `Domestic production` | `production` | `annual_only` | `2016-04-01` | `2026-03-01` | `120` | `Economic Survey Statistical Appendix + current snapshot` | `annual_production_to_monthly_harvest_release_proxy` |
| `Opening stocks` | `stock` | `mixed` | `2016-04-01` | `2026-03-01` | `120` | `Local supply-demand analytics store + USDA current carry-over point` | `annual_opening_to_closing_stock_interpolation` |
| `Imports` | `trade` | `mixed` | `2016-04-01` | `2026-03-01` | `120` | `Local supply-demand analytics store / USDA import point` | `annual_imports_to_monthly_uniform_proxy` |
| `Buffer stock` | `stock` | `mixed` | `2016-04-01` | `2026-03-01` | `120` | `Same local stock backbone as opening stock` | `annual_opening_to_closing_stock_interpolation` |
| `USDA global production by country` | `global_production` | `partial` | `2016-04-01` | `2026-03-01` | `480` | `USDA WASDE March 2026 local text snapshot` | `usda_marketing_year_hold_constant_monthly`, older `backfilled_from_2023_24_usda_snapshot` |
| `Major producer crop conditions` | `crop_condition` | `curated` | `2016-04-01` | `2026-03-01` | `480` | `Curated global maize crop-condition profiles` | `recurring_monthly_crop_condition_profile` |
| `Brazil safrinha harvest calendar` | `calendar` | `curated` | `2016-04-01` | `2026-03-01` | `120` | `Curated Brazil safrinha harvest calendar` | `recurring_monthly_harvest_calendar` |
| `Global exporter harvest calendar` | `calendar` | `curated` | `2016-04-01` | `2026-03-01` | `120` | `Curated global maize exporter harvest calendar` | `recurring_monthly_harvest_calendar` |
| `Total availability` | `derived` | `derived` | `2016-04-01` | `2026-03-01` | `120` | `derived inside Maize supply store` | `opening_stock_plus_domestic_production_plus_imports` |

## Key supply formula

`Total Availability = Opening Stock + Domestic Production + Imports`

## Step 2 short summary

| Item | Status |
|---|---|
| `Maize supply folder created` | `Done` |
| `Maize supply DB created` | `Done` |
| `Supply factor dictionary seeded` | `Done` |
| `Monthly Maize supply data loaded` | `Done` |

# Step 3 - Build Demand Side

This section captures the initial Maize demand monthly panel, loaded using the same structure as Wheat demand.

## Maize demand workspace

- Folder: [D:/ncel2/ncel-commodity-pricing/SnD/demand/maize](D:/ncel2/ncel-commodity-pricing/SnD/demand/maize)
- DB: [D:/ncel2/ncel-commodity-pricing/SnD/demand/maize/maize_demand_monthly.db](D:/ncel2/ncel-commodity-pricing/SnD/demand/maize/maize_demand_monthly.db)
- Builder: [D:/ncel2/ncel-commodity-pricing/SnD/demand/maize/build_maize_demand_store.py](D:/ncel2/ncel-commodity-pricing/SnD/demand/maize/build_maize_demand_store.py)

## Tables created

| Table | Purpose |
|---|---|
| `maize_factor_definitions` | Maize demand factor dictionary |
| `maize_source_inventory` | source websites and cadence |
| `maize_factor_status` | monthly/source status of each demand factor |
| `maize_factor_monthly_values` | monthly demand panel used for analysis and model features |

## Current table counts

| Table | Rows |
|---|---:|
| `maize_factor_definitions` | `12` |
| `maize_source_inventory` | `5` |
| `maize_factor_status` | `12` |
| `maize_factor_monthly_values` | `1440` |

## Demand factor coverage (loaded)

| Factor | Monthly Status | Data From | Data To | Rows |
|---|---|---|---|---:|
| `Domestic other use` | `not_found_cleanly` | `2016-04-01` | `2026-03-01` | `120` |
| `Ethanol demand signal` | `curated` | `2016-04-01` | `2026-03-01` | `120` |
| `Exports` | `partially_available` | `2016-04-01` | `2026-03-01` | `120` |
| `Feed use` | `mixed` | `2016-04-01` | `2026-03-01` | `120` |
| `Industrial use` | `not_found_cleanly` | `2016-04-01` | `2026-03-01` | `120` |
| `Policy changes` | `curated` | `2016-04-01` | `2026-03-01` | `120` |
| `Population / consumption trend` | `annual_only` | `2016-04-01` | `2026-03-01` | `120` |
| `Poultry demand cycle` | `curated` | `2016-04-01` | `2026-03-01` | `120` |
| `Retail / mandi price pressure` | `available` | `2016-04-01` | `2026-03-01` | `120` |
| `Seed use` | `not_found_cleanly` | `2016-04-01` | `2026-03-01` | `120` |
| `Substitution effect` | `available` | `2016-04-01` | `2026-03-01` | `120` |
| `Total demand monthly` | `derived` | `2016-04-01` | `2026-03-01` | `120` |

## First 10 sample rows from `maize_factor_monthly_values`

| Factor | Metric Month | Value | Unit | Method |
|---|---|---:|---|---|
| `Domestic other use` | `2016-04-01` | `0.513985` | `million_tonnes` | `annual_total_demand_to_monthly_other_proxy` |
| `Domestic other use` | `2016-05-01` | `0.513985` | `million_tonnes` | `annual_total_demand_to_monthly_other_proxy` |
| `Domestic other use` | `2016-06-01` | `0.513985` | `million_tonnes` | `annual_total_demand_to_monthly_other_proxy` |
| `Domestic other use` | `2016-07-01` | `0.526676` | `million_tonnes` | `annual_total_demand_to_monthly_other_proxy` |
| `Domestic other use` | `2016-08-01` | `0.533022` | `million_tonnes` | `annual_total_demand_to_monthly_other_proxy` |
| `Domestic other use` | `2016-09-01` | `0.533022` | `million_tonnes` | `annual_total_demand_to_monthly_other_proxy` |
| `Domestic other use` | `2016-10-01` | `0.545713` | `million_tonnes` | `annual_total_demand_to_monthly_other_proxy` |
| `Domestic other use` | `2016-11-01` | `0.558404` | `million_tonnes` | `annual_total_demand_to_monthly_other_proxy` |
| `Domestic other use` | `2016-12-01` | `0.558404` | `million_tonnes` | `annual_total_demand_to_monthly_other_proxy` |
| `Domestic other use` | `2017-01-01` | `0.520331` | `million_tonnes` | `annual_total_demand_to_monthly_other_proxy` |

## Step 2 detailed supply factors with sources and formulas

| Supply Factor | Group | Source Name | Source Type | Source Link | Monthly Check | Data From | Data To | Rows | Formula / Method |
|---|---|---|---|---|---|---|---|---:|---|
| `Acreage (sown area)` | `area` | `Economic Survey Statistical Appendix` | `pdf` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `annual_hold_constant_monthly` |
| `Yield per hectare` | `yield` | `Economic Survey Statistical Appendix` | `pdf` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `annual_hold_constant_monthly` |
| `Domestic production` | `production` | `Economic Survey Statistical Appendix` | `pdf` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `annual_production_to_monthly_harvest_release_proxy` |
| `Opening stocks` | `stock` | `USDA PSD / WASDE references` | `web` | [USDA PSD](https://apps.fas.usda.gov/psdonline/app/index.html#/app/home), [USDA WASDE](https://www.usda.gov/oce/commodity/wasde) | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `annual_opening_to_closing_stock_interpolation` |
| `Imports` | `trade` | `USDA PSD / APEDA trade context` | `web/pdf` | [USDA PSD](https://apps.fas.usda.gov/psdonline/app/index.html#/app/home), [APEDA](https://apeda.gov.in/) | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `annual_imports_to_monthly_uniform_proxy` |
| `Buffer stock` | `stock` | `USDA PSD / WASDE references` | `web` | [USDA PSD](https://apps.fas.usda.gov/psdonline/app/index.html#/app/home), [USDA WASDE](https://www.usda.gov/oce/commodity/wasde) | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `annual_opening_to_closing_stock_interpolation` |
| `USDA global production by country` | `global_production` | `USDA WASDE` | `pdf/web` | [USDA WASDE](https://www.usda.gov/oce/commodity/wasde) | `Yes (120 months x 4 countries)` | `2016-04-01` | `2026-03-01` | `480` | `usda_marketing_year_hold_constant_monthly`, `backfilled_from_2023_24_usda_snapshot` |
| `Major producer crop conditions` | `crop_condition` | `Curated global maize crop-condition profile` | `curated monthly` | [USDA](https://www.usda.gov/) | `Yes (120 months x 4 countries)` | `2016-04-01` | `2026-03-01` | `480` | `recurring_monthly_crop_condition_profile` |
| `Brazil safrinha harvest calendar` | `calendar` | `Curated Brazil safrinha harvest calendar` | `curated seasonal` | [FAO](https://www.fao.org/) | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `recurring_monthly_harvest_calendar` |
| `Global exporter harvest calendar` | `calendar` | `Curated global maize exporter harvest calendar` | `curated seasonal` | [FAO](https://www.fao.org/) | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `recurring_monthly_harvest_calendar` |
| `Total availability` | `derived` | `Derived from supply components` | `derived` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf), [USDA PSD](https://apps.fas.usda.gov/psdonline/app/index.html#/app/home) | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `opening_stock_plus_domestic_production_plus_imports` |

### Step 2 annual-to-monthly formulas

| Factor | Annual to Monthly Formula |
|---|---|
| `Acreage (sown area)` | `MonthlyAcreage(m) = AnnualAcreage(marketing_year)` |
| `Yield per hectare` | `MonthlyYield(m) = AnnualYield(marketing_year)` |
| `Domestic production` | `MonthlyProduction(m) = AnnualProduction(marketing_year) x ProductionReleaseWeight(m)` |
| `Opening stocks` | `MonthlyOpeningStock(m) = Opening + t x (Closing - Opening)` where `t` is month position in crop year |
| `Imports` | `MonthlyImports(m) = AnnualImports(marketing_year) x ImportWeight(m)` |
| `Buffer stock` | `MonthlyBufferStock(m) = Opening + t x (Closing - Opening)` |
| `USDA global production by country` | `MonthlyGlobalProduction(country,m) = AnnualUSDAProduction(country,marketing_year)` |
| `Total availability` | `TotalAvailability(m) = OpeningStock(m) + DomesticProduction(m) + Imports(m)` |

### Step 2 conversion weights used

| Month | Production Release Weight | Import Weight |
|---|---:|---:|
| `Jan` | `0.05` | `0.083333` |
| `Feb` | `0.03` | `0.083333` |
| `Mar` | `0.01` | `0.083333` |
| `Apr` | `0.03` | `0.083333` |
| `May` | `0.05` | `0.083333` |
| `Jun` | `0.08` | `0.083333` |
| `Jul` | `0.09` | `0.083333` |
| `Aug` | `0.09` | `0.083333` |
| `Sep` | `0.14` | `0.083333` |
| `Oct` | `0.18` | `0.083333` |
| `Nov` | `0.16` | `0.083333` |
| `Dec` | `0.09` | `0.083333` |

## Step 3 detailed demand factors with sources and formulas

| Demand Factor | Source Name | Source Type | Source Link | Monthly Status | Monthly Check | Data From | Data To | Rows | Formula / Method |
|---|---|---|---|---|---|---|---|---:|---|
| `Feed use` | `Economic Survey + APEDA + derived allocation` | `pdf/web + derived` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf), [APEDA](https://apeda.gov.in/) | `mixed` | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `annual_total_demand_to_monthly_feed_proxy` |
| `Industrial use` | `Economic Survey + derived allocation` | `pdf + derived` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `not_found_cleanly` | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `annual_total_demand_to_monthly_industrial_proxy` |
| `Exports` | `APEDA Product Page + proxy` | `web/pdf` | [APEDA](https://apeda.gov.in/) | `partially_available` | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `annual_exports_to_monthly_proxy` |
| `Seed use` | `Derived sowing proxy` | `derived + crop calendar context` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `not_found_cleanly` | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `annual_seed_to_monthly_sowing_proxy` |
| `Domestic other use` | `Economic Survey + APEDA + residual demand logic` | `pdf/web + derived` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf), [APEDA](https://apeda.gov.in/) | `not_found_cleanly` | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `annual_total_demand_to_monthly_other_proxy` |
| `Poultry demand cycle` | `Curated profile (internal assumptions)` | `curated` | [APEDA](https://apeda.gov.in/), [USDA](https://www.usda.gov/) | `curated` | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `curated_monthly_poultry_cycle` |
| `Ethanol demand signal` | `Curated profile (internal assumptions)` | `curated` | [Ministry of Petroleum and Natural Gas](https://mopng.gov.in/), [NITI Aayog](https://www.niti.gov.in/) | `curated` | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `curated_step_signal` |
| `Policy changes` | `Curated policy event profile` | `curated` | [DGFT](https://www.dgft.gov.in/CP/), [APEDA](https://apeda.gov.in/) | `curated` | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `curated_event_series` |
| `Population / consumption trend` | `World population reference` | `api/web` | [World Bank Population](https://data.worldbank.org/indicator/SP.POP.TOTL) | `annual_only` | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `annual_population_to_monthly_interpolation` |
| `Retail / mandi price pressure` | `National mandi price references` | `web` | [Agmarknet](https://agmarknet.gov.in/) | `available` | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `monthly_national_maize_price_index` |
| `Substitution effect` | `Maize vs Wheat mandi price references` | `web` | [Agmarknet](https://agmarknet.gov.in/) | `available` | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `monthly_maize_vs_wheat_ratio_index` |
| `Total demand monthly` | `Derived from demand components` | `derived` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf), [APEDA](https://apeda.gov.in/) | `derived` | `Yes (120/120 months)` | `2016-04-01` | `2026-03-01` | `120` | `feed_plus_industrial_plus_exports_plus_seed_plus_domestic_other_use` |

### Step 3 annual-to-monthly formulas

| Factor | Annual to Monthly Formula |
|---|---|
| `Feed use` | `FeedMonthly(m) = FeedAnnual(marketing_year) x FeedWeight(m)` |
| `Industrial use` | `IndustrialMonthly(m) = IndustrialAnnual(marketing_year) x IndustrialWeight(m)` |
| `Exports` | `ExportsMonthly(m) = ExportsAnnual(marketing_year) x ExportWeight(m)` |
| `Seed use` | `SeedMonthly(m) = SeedAnnual(marketing_year) x SeedWeight(m)` |
| `Domestic other use` | `OtherMonthly(m) = OtherAnnual(marketing_year) x OtherWeight(m)` |
| `Population / consumption trend` | `PopulationMonthly(m) = AnnualPopulation(y) + frac(m) x (AnnualPopulation(y+1) - AnnualPopulation(y))` |
| `Total demand monthly` | `TotalDemandMonthly(m) = FeedMonthly(m) + IndustrialMonthly(m) + ExportsMonthly(m) + SeedMonthly(m) + OtherMonthly(m)` |

### Step 3 annual demand split used before monthly weighting

| Component | Formula |
|---|---|
| `Total annual demand` | `OpeningStock + AnnualProduction + AnnualImports - EndingStock` |
| `Feed annual` | `0.58 x TotalAnnualDemand` |
| `Industrial annual` | `0.12 x TotalAnnualDemand` |
| `Seed annual` | `0.04 x AnnualProduction` |
| `Exports annual` | `APEDA override if available else max(0.20, 0.015 x AnnualProduction)` |
| `Domestic other annual` | `TotalAnnualDemand - FeedAnnual - IndustrialAnnual - SeedAnnual - ExportsAnnual` |

### Step 3 monthly weights used for annual-to-monthly conversion

| Month | Feed Weight | Other Weight | Export Weight | Seed Weight | Industrial Weight |
|---|---:|---:|---:|---:|---:|
| `Jan` | `0.086` | `0.082` | `0.09` | `0.01` | `0.083333` |
| `Feb` | `0.084` | `0.081` | `0.09` | `0.01` | `0.083333` |
| `Mar` | `0.082` | `0.081` | `0.08` | `0.01` | `0.083333` |
| `Apr` | `0.079` | `0.081` | `0.07` | `0.02` | `0.083333` |
| `May` | `0.079` | `0.081` | `0.07` | `0.04` | `0.083333` |
| `Jun` | `0.079` | `0.081` | `0.07` | `0.19` | `0.083333` |
| `Jul` | `0.082` | `0.083` | `0.07` | `0.22` | `0.083333` |
| `Aug` | `0.084` | `0.084` | `0.07` | `0.08` | `0.083333` |
| `Sep` | `0.084` | `0.084` | `0.08` | `0.03` | `0.083333` |
| `Oct` | `0.086` | `0.086` | `0.10` | `0.16` | `0.083333` |
| `Nov` | `0.087` | `0.088` | `0.11` | `0.16` | `0.083333` |
| `Dec` | `0.088` | `0.088` | `0.10` | `0.07` | `0.083333` |

# Step 4 - Build Maize Balance Sheet and Stocks-to-Use

This step integrates Maize supply and demand monthly panels into a unified balance sheet for monthly and crop-year analytics.

## Step 4 workspace

- Folder: [D:/ncel2/ncel-commodity-pricing/SnD/balance/maize](D:/ncel2/ncel-commodity-pricing/SnD/balance/maize)
- DB: [D:/ncel2/ncel-commodity-pricing/SnD/balance/maize/maize_balance_sheet.db](D:/ncel2/ncel-commodity-pricing/SnD/balance/maize/maize_balance_sheet.db)
- Builder: [D:/ncel2/ncel-commodity-pricing/SnD/balance/maize/build_maize_balance_sheet.py](D:/ncel2/ncel-commodity-pricing/SnD/balance/maize/build_maize_balance_sheet.py)

## Tables created

| Table | Purpose |
|---|---|
| `maize_balance_monthly` | Integrated monthly balance from supply and demand |
| `maize_balance_annual` | Oct-Sep crop-year aggregated balance |
| `maize_stocks_to_use` | Crop-year ending-stock to demand ratio |

## Current table counts and range

| Table | Rows | Range / Note |
|---|---:|---|
| `maize_balance_monthly` | `120` | `2016-04-01` to `2026-03-01` |
| `maize_balance_annual` | `11` | `2015/16` to `2025/26` (includes edge partial years) |
| `maize_stocks_to_use` | `11` | `2015/16` to `2025/26` |

## Crop-year completeness

| Metric | Value |
|---|---:|
| `Full crop years (12 months)` | `9` |
| `Partial crop years` | `2` |
| `Crop-year convention` | `Oct-Sep` |

## Step 4 formulas used

| Metric | Formula |
|---|---|
| `Total availability (monthly)` | `OpeningStock + DomesticProduction + Imports` |
| `Delta (monthly)` | `TotalAvailability - TotalDemandMonthly` |
| `Crop-year stocks-to-use ratio` | `EndingStock / TotalDemand` |
| `Crop-year stocks-to-use %` | `(EndingStock / TotalDemand) x 100` |

## Step 4 source links

| Step 4 Data Component | Pulled From | Source Link |
|---|---|---|
| `Opening stock (monthly)` | `Maize Supply Step 2 (opening_stock)` | [USDA PSD](https://apps.fas.usda.gov/psdonline/app/index.html#/app/home), [USDA WASDE](https://www.usda.gov/oce/commodity/wasde) |
| `Domestic production (monthly)` | `Maize Supply Step 2 (domestic_production)` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) |
| `Imports (monthly)` | `Maize Supply Step 2 (imports)` | [USDA PSD](https://apps.fas.usda.gov/psdonline/app/index.html#/app/home), [APEDA](https://apeda.gov.in/) |
| `Total demand monthly` | `Maize Demand Step 3 (total_demand_monthly)` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf), [APEDA](https://apeda.gov.in/) |
| `Retail/mandi demand signal inputs` | `Maize Demand Step 3 features` | [Agmarknet](https://agmarknet.gov.in/) |
| `Population trend input` | `Maize Demand Step 3 feature` | [World Bank Population](https://data.worldbank.org/indicator/SP.POP.TOTL) |
| `Global crop context used in supply layer` | `Maize Supply Step 2 features` | [USDA](https://www.usda.gov/), [FAO](https://www.fao.org/) |

## Step 4 derived metric mapping

| Step 4 Derived Metric | Formula | Derived From |
|---|---|---|
| `Total availability` | `opening_stock + domestic_production + imports` | `Step 2 supply monthly factors` |
| `Delta` | `total_availability - total_demand_monthly` | `Step 2 + Step 3 monthly factors` |
| `Stocks-to-use ratio` | `ending_stock / total_demand` | `Step 4 annual rollup` |
| `Stocks-to-use %` | `(ending_stock / total_demand) * 100` | `Step 4 annual rollup` |

## Step 4 short status

| Item | Status |
|---|---|
| `Balance DB created` | `Done` |
| `Monthly balance loaded` | `Done` |
| `Annual crop-year rollup loaded` | `Done` |
| `Stocks-to-use loaded` | `Done` |
| `Validation (range + counts)` | `Done` |

# Step 5 - Plan: Identify Maize Price Drivers

## Step 5 implementation plan

| Phase | Step 5 Plan (Maize Price Drivers) | Output |
|---|---|---|
| `1` | Define driver framework buckets | `Domestic`, `Global`, `Weather`, `Policy`, `Market-micro` |
| `2` | List candidate drivers from current Maize S&D setup | Draft driver inventory |
| `3` | Map each driver to measurable signal | `existing_factor_key` or `new_feature_required` |
| `4` | Define driver direction logic | `bullish if up`, `bearish if up`, or `regime-dependent` |
| `5` | Define update frequency and lag | `daily/weekly/monthly/seasonal` + expected lag |
| `6` | Attach source links | External source URLs per driver |
| `7` | Score importance | `High / Medium / Low` impact |
| `8` | Create Step 5 output tables | Driver master table + gap table |
| `9` | Validate against model-readiness | Ensure every critical driver has a data coverage path |
| `10` | Update blueprint | Add finalized Step 5 section to `maize_blueprint.md` |

## Step 5 deliverable templates

| Step 5 Deliverable Table | Columns |
|---|---|
| `Driver Master` | `Driver | Category | Commodity | Signal/Proxy | Direction | Frequency | Data From | Data To | Status | Source` |
| `Driver-to-Factor Mapping` | `Driver | Existing Factor? | Factor Key | Transformation | Notes` |
| `Data Gaps` | `Driver | Missing Piece | Proposed Source | Backfill Rule | Priority` |

## Step 5 acceptance criteria

| Acceptance Criteria | Pass Condition |
|---|---|
| `Coverage` | All major Maize price drivers represented (`domestic + global + weather + policy`) |
| `Measurability` | Each driver mapped to a numeric signal or explicit gap |
| `Traceability` | Every driver has source links |
| `Actionability` | Clear status: `ready`, `partial`, or `needs_new_data` |
| `Documentation` | Step 5 tables added to `maize_blueprint.md` |

## Step 5 implementation status

| Item | Details |
|---|---|
| `Folder` | `D:\ncel2\ncel-commodity-pricing\SnD\price_drivers\maize` |
| `Builder` | `build_maize_price_drivers.py` |
| `DB` | `maize_price_drivers.db` |
| `Monthly range` | `2016-04-01` to `2026-03-01` |
| `Status` | `Implemented` |

## Step 5 tables created (Maize-specific names)

| Table | Purpose | Rows |
|---|---|---:|
| `maize_driver_definitions` | driver dictionary | `9` |
| `maize_driver_source_inventory` | source registry | `6` |
| `maize_driver_status` | monthly status + load modes | `9` |
| `maize_driver_reference` | driver-wise formula/reference notes | `9` |
| `maize_driver_monthly_values` | monthly driver panel | `1080` |
| `maize_driver_impact_score` | monthly composite impact score | `120` |

## Step 5 driver master (implemented)

| Driver | Category | Signal/Proxy | Monthly Status | Data From | Data To | Rows | Source Link | Method |
|---|---|---|---|---|---|---:|---|---|
| `MSP (Maize)` | `Domestic` | `msp_maize` | `annual_only` | `2016-04-01` | `2026-03-01` | `120` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `annual_msp_to_monthly_step_series` |
| `Kharif arrival intensity` | `Domestic` | `kharif_arrival_intensity` | `available` | `2016-04-01` | `2026-03-01` | `120` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `normalize_domestic_production_to_index_100` |
| `Poultry demand cycle` | `Domestic` | `poultry_demand_cycle` | `available` | `2016-04-01` | `2026-03-01` | `120` | [APEDA](https://apeda.gov.in/) | `load_from_demand_factor_monthly_values` |
| `US corn crop outlook` | `Global` | `us_corn_crop_outlook` | `partial` | `2016-04-01` | `2026-03-01` | `120` | [USDA WASDE](https://www.usda.gov/oce/commodity/wasde) | `normalize_usda_us_production_to_index_100` |
| `Brazil safrinha pressure` | `Global` | `brazil_safrinha_pressure` | `available` | `2016-04-01` | `2026-03-01` | `120` | [FAO](https://www.fao.org/) | `load_from_supply_calendar_series` |
| `Monsoon distribution risk` | `Weather` | `monsoon_distribution_risk` | `curated` | `2016-04-01` | `2026-03-01` | `120` | [IMD](https://mausam.imd.gov.in/) | `curated_recurring_monthly_profile` |
| `Export policy restriction` | `Policy` | `export_policy_restriction` | `curated` | `2016-04-01` | `2026-03-01` | `120` | [DGFT](https://www.dgft.gov.in/CP/) | `load_from_demand_policy_changes_series` |
| `Ethanol blending push` | `Policy` | `ethanol_blending_push` | `available` | `2016-04-01` | `2026-03-01` | `120` | [Ministry of Petroleum and Natural Gas](https://mopng.gov.in/) | `load_from_ethanol_demand_signal_series` |
| `Substitution vs wheat` | `Market` | `substitution_vs_wheat` | `available` | `2016-04-01` | `2026-03-01` | `120` | [Agmarknet](https://agmarknet.gov.in/) | `load_from_substitution_effect_series` |

## Step 5 composite scoring formulas

| Metric | Formula |
|---|---|
| `Driver contribution` | `z_score(driver) * direction * weight` |
| `Composite score` | `50 + 20 * sum(driver_contributions)` (clamped `0..100`) |
| `Bucket score` | `50 + 35 * sum(bucket_contributions)` (clamped `0..100`) |
| `Implied price adjustment %` | `1.2 * sum(driver_contributions)` (clamped `-4..+4`) |

## Step 5 sample rows

### Sample rows from `maize_driver_monthly_values`

| Driver Key | Metric Month | Value | Unit | Source | Method |
|---|---|---:|---|---|---|
| `brazil_safrinha_pressure` | `2016-04-01` | `42.0` | `index_100` | [FAO](https://www.fao.org/) | `load_from_supply_calendar_series` |
| `ethanol_blending_push` | `2016-04-01` | `35.0` | `index_100` | [Ministry of Petroleum and Natural Gas](https://mopng.gov.in/) | `load_from_ethanol_demand_signal_series` |
| `export_policy_restriction` | `2016-04-01` | `0.0` | `policy_index` | [DGFT](https://www.dgft.gov.in/CP/) | `load_from_demand_policy_changes_series` |
| `kharif_arrival_intensity` | `2016-04-01` | `27.496314` | `index_100` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `normalize_domestic_production_to_index_100` |
| `monsoon_distribution_risk` | `2016-04-01` | `22.0` | `index_100` | [IMD](https://mausam.imd.gov.in/) | `curated_recurring_monthly_profile` |
| `msp_maize` | `2016-04-01` | `2400.0` | `INR/quintal` | [Economic Survey Statistical Appendix](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `annual_msp_to_monthly_step_series` |
| `poultry_demand_cycle` | `2016-04-01` | `97.0` | `index_100` | [APEDA](https://apeda.gov.in/) | `load_from_demand_factor_monthly_values` |
| `substitution_vs_wheat` | `2016-04-01` | `100.0` | `index_100` | [Agmarknet](https://agmarknet.gov.in/) | `load_from_substitution_effect_series` |
| `us_corn_crop_outlook` | `2016-04-01` | `99.203914` | `index_100` | [USDA WASDE](https://www.usda.gov/oce/commodity/wasde) | `normalize_usda_us_production_to_index_100` |
| `brazil_safrinha_pressure` | `2016-05-01` | `68.0` | `index_100` | [FAO](https://www.fao.org/) | `load_from_supply_calendar_series` |

### Sample rows from `maize_driver_impact_score`

| Metric Month | Composite | Domestic | Global | Weather | Policy | Market | Implied Price Adj % |
|---|---:|---:|---:|---:|---:|---:|---:|
| `2016-04-01` | `49.685073` | `53.847164` | `51.062429` | `46.273311` | `48.265974` | `50.0` | `-0.018896` |
| `2016-05-01` | `48.123999` | `50.991231` | `48.294126` | `49.165667` | `48.265974` | `50.0` | `-0.11256` |
| `2016-06-01` | `50.357536` | `51.893056` | `45.738769` | `54.727889` | `48.265974` | `50.0` | `0.021452` |
| `2016-07-01` | `53.54373` | `55.650813` | `44.886984` | `57.397756` | `48.265974` | `50.0` | `0.212624` |
| `2016-08-01` | `55.823634` | `58.614084` | `46.803501` | `56.507801` | `48.265974` | `50.0` | `0.349418` |

### Sample rows from `maize_driver_definitions`

| Driver Key | Driver Name | Bucket | Unit |
|---|---|---|---|
| `brazil_safrinha_pressure` | `Brazil safrinha pressure` | `Global` | `index_100` |
| `ethanol_blending_push` | `Ethanol blending push` | `Policy` | `index_100` |
| `export_policy_restriction` | `Export policy restriction` | `Policy` | `policy_index` |
| `kharif_arrival_intensity` | `Kharif arrival intensity` | `Domestic` | `index_100` |
| `monsoon_distribution_risk` | `Monsoon distribution risk` | `Weather` | `index_100` |
| `msp_maize` | `MSP (Maize)` | `Domestic` | `INR/quintal` |
| `poultry_demand_cycle` | `Poultry demand cycle` | `Domestic` | `index_100` |
| `substitution_vs_wheat` | `Substitution vs wheat` | `Market` | `index_100` |
| `us_corn_crop_outlook` | `US corn crop outlook` | `Global` | `index_100` |

# Step 6 - Data Collection Plan (Maize)

This step operationalizes Maize data sourcing, refresh cadence, QA rules, and target-table mapping across Steps 2-5.

## Step 6 workspace

- Folder: [D:/ncel2/ncel-commodity-pricing/SnD/data_plan/maize](D:/ncel2/ncel-commodity-pricing/SnD/data_plan/maize)
- Builder: [D:/ncel2/ncel-commodity-pricing/SnD/data_plan/maize/build_maize_data_collection_plan.py](D:/ncel2/ncel-commodity-pricing/SnD/data_plan/maize/build_maize_data_collection_plan.py)
- DB: [D:/ncel2/ncel-commodity-pricing/SnD/data_plan/maize/maize_data_collection_plan.db](D:/ncel2/ncel-commodity-pricing/SnD/data_plan/maize/maize_data_collection_plan.db)

## Step 6 tables created (Maize-specific)

| Table | Purpose | Rows |
|---|---|---:|
| `maize_data_points` | data-point inventory | `19` |
| `maize_data_sources` | external source registry | `10` |
| `maize_collection_plan` | end-to-end collection plan | `19` |
| `maize_collection_status_log` | run/status log | `19` |

## Step 6 status summary

| Status | Count |
|---|---:|
| `loaded` | `17` |
| `partial` | `2` |
| `missing` | `0` |

## Step 6 source inventory

| Source Name | Source Type | Cadence | Link |
|---|---|---|---|
| `Economic Survey Statistical Appendix` | `pdf` | `annual` | [Economic Survey](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) |
| `USDA PSD` | `web` | `monthly` | [USDA PSD](https://apps.fas.usda.gov/psdonline/app/index.html#/app/home) |
| `USDA WASDE` | `pdf/web` | `monthly` | [USDA WASDE](https://www.usda.gov/oce/commodity/wasde) |
| `APEDA` | `web/pdf` | `monthly` | [APEDA](https://apeda.gov.in/) |
| `Agmarknet` | `web` | `daily` | [Agmarknet](https://agmarknet.gov.in/) |
| `India Meteorological Department` | `web` | `weekly/seasonal` | [IMD](https://mausam.imd.gov.in/) |
| `DGFT` | `web` | `event-driven` | [DGFT](https://www.dgft.gov.in/CP/) |
| `World Bank Population` | `api/web` | `annual` | [World Bank Population](https://data.worldbank.org/indicator/SP.POP.TOTL) |
| `Ministry of Petroleum and Natural Gas` | `web` | `policy updates` | [MoPNG](https://mopng.gov.in/) |
| `FAO` | `web` | `seasonal` | [FAO](https://www.fao.org/) |

## Step 6 sample collection-plan rows

| Data Key | Data Name | Source Name | Source Link | Status | Data From | Data To | Target Table | Method |
|---|---|---|---|---|---|---|---|---|
| `india_area` | `India maize area` | `Economic Survey Statistical Appendix` | [Economic Survey](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `loaded` | `2016-04-01` | `2026-03-01` | `maize_factor_monthly_values` | `annual_to_monthly_hold_constant` |
| `india_yield` | `India maize yield` | `Economic Survey Statistical Appendix` | [Economic Survey](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `loaded` | `2016-04-01` | `2026-03-01` | `maize_factor_monthly_values` | `annual_to_monthly_hold_constant` |
| `india_production` | `India maize production` | `Economic Survey Statistical Appendix` | [Economic Survey](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `loaded` | `2016-04-01` | `2026-03-01` | `maize_factor_monthly_values` | `annual_to_monthly_harvest_weights` |
| `india_opening_stock` | `India opening stock` | `USDA PSD` | [USDA PSD](https://apps.fas.usda.gov/psdonline/app/index.html#/app/home) | `loaded` | `2016-04-01` | `2026-03-01` | `maize_factor_monthly_values` | `annual_stock_interpolation` |
| `india_imports` | `India maize imports` | `APEDA` | [APEDA](https://apeda.gov.in/) | `partial` | `2016-04-01` | `2026-03-01` | `maize_factor_monthly_values` | `annual_to_monthly_uniform_proxy` |
| `global_us_corn_production` | `US corn production` | `USDA WASDE` | [USDA WASDE](https://www.usda.gov/oce/commodity/wasde) | `loaded` | `2016-04-01` | `2026-03-01` | `maize_factor_monthly_values` | `marketing_year_hold_constant` |
| `global_brazil_safrinha` | `Brazil safrinha harvest intensity` | `FAO` | [FAO](https://www.fao.org/) | `loaded` | `2016-04-01` | `2026-03-01` | `maize_factor_monthly_values` | `curated_seasonal_profile` |
| `feed_use` | `Maize feed use` | `Economic Survey Statistical Appendix` | [Economic Survey](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `loaded` | `2016-04-01` | `2026-03-01` | `maize_factor_monthly_values` | `annual_to_monthly_feed_weights` |
| `poultry_cycle` | `Poultry demand cycle` | `APEDA` | [APEDA](https://apeda.gov.in/) | `loaded` | `2016-04-01` | `2026-03-01` | `maize_factor_monthly_values` | `curated_monthly_profile` |
| `industrial_use` | `Maize industrial use` | `Economic Survey Statistical Appendix` | [Economic Survey](https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf) | `loaded` | `2016-04-01` | `2026-03-01` | `maize_factor_monthly_values` | `annual_to_monthly_proxy` |

## Step 6 short status

| Item | Status |
|---|---|
| `Step 6 DB created` | `Done` |
| `Source inventory loaded` | `Done` |
| `Collection plan loaded` | `Done` |
| `Status log seeded` | `Done` |
| `Blueprint updated` | `Done` |

# Step 7 - Build Scenarios (Maize)

This step converts the Step 4 balance and Step 5 driver scores into Bull/Base/Bear scenario outputs and scenario-wise price ranges.

## Step 7 workspace

- Folder: [D:/ncel2/ncel-commodity-pricing/SnD/scenarios/maize](D:/ncel2/ncel-commodity-pricing/SnD/scenarios/maize)
- Builder: [D:/ncel2/ncel-commodity-pricing/SnD/scenarios/maize/build_maize_scenarios.py](D:/ncel2/ncel-commodity-pricing/SnD/scenarios/maize/build_maize_scenarios.py)
- DB: [D:/ncel2/ncel-commodity-pricing/SnD/scenarios/maize/maize_scenarios.db](D:/ncel2/ncel-commodity-pricing/SnD/scenarios/maize/maize_scenarios.db)

## Step 7 tables created (Maize-specific)

| Table | Purpose | Rows |
|---|---|---:|
| `maize_scenario_definitions` | scenario master | `3` |
| `maize_scenario_assumptions` | scenario shock assumptions | `21` |
| `maize_scenario_monthly_output` | scenario monthly S&D + price index output | `360` |
| `maize_scenario_annual_output` | scenario annual crop-year output | `33` |
| `maize_scenario_price_range` | scenario crop-year price bands | `33` |

## Step 7 monthly coverage

| Metric | Value |
|---|---|
| `Date from` | `2016-04-01` |
| `Date to` | `2026-03-01` |
| `Scenarios` | `bull_tight_supply`, `base_normal`, `bear_surplus` |

## Step 7 scenario assumptions (implemented)

| Variable | Bull (Tight Supply) | Base | Bear (Surplus) |
|---|---:|---:|---:|
| `production_shock_pct` | `-0.06` | `0.00` | `+0.06` |
| `imports_shock_pct` | `-0.10` | `0.00` | `+0.10` |
| `demand_shock_pct` | `+0.04` | `0.00` | `-0.04` |
| `policy_shock_index` | `+8` | `0` | `-8` |
| `weather_shock_index` | `+10` | `0` | `-10` |
| `global_shock_index` | `+6` | `0` | `-6` |
| `band_width` | `0.08` | `0.06` | `0.08` |

## Step 7 formulas used

| Metric | Formula |
|---|---|
| `Availability(s,m)` | `Opening + Production*(1+production_shock) + Imports*(1+imports_shock)` |
| `Demand(s,m)` | `BaseDemand*(1+demand_shock)` |
| `Delta(s,m)` | `Availability - Demand` |
| `EndingStock(s,m)` | `Opening + Production' + Imports' - Demand'` |
| `STU proxy(s,m)` | `EndingStock / Demand` |
| `DriverAdj(s,m)` | `BaseComposite + 0.35*policy_shock + 0.35*weather_shock + 0.30*global_shock` |
| `ImpliedPriceIndex(s,m)` | `100 + 0.45*tightness_term + 0.20*stu_inverse + 0.35*driver_term` (clamped `60..180`) |
| `Price band` | `low = mid*(1-band_width)`, `high = mid*(1+band_width)` |

## Step 7 scenario ordering check

| Scenario | Avg `price_mid` |
|---|---:|
| `bull_tight_supply` | `82.2558` |
| `base_normal` | `76.0766` |
| `bear_surplus` | `71.5391` |

## Step 7 sample price-range rows

| Scenario | Crop Year | Price Low | Price Mid | Price High |
|---|---|---:|---:|---:|
| `base_normal` | `2015/16` | `60.831633` | `64.714504` | `68.597374` |
| `bear_surplus` | `2015/16` | `57.270863` | `62.250938` | `67.231013` |
| `bull_tight_supply` | `2015/16` | `63.314481` | `68.820088` | `74.325695` |
| `base_normal` | `2016/17` | `66.28889` | `70.520096` | `74.751302` |
| `bear_surplus` | `2016/17` | `61.521915` | `66.871647` | `72.221379` |
| `bull_tight_supply` | `2016/17` | `70.170489` | `76.272271` | `82.374053` |

## Step 7 short status

| Item | Status |
|---|---|
| `Scenario engine built` | `Done` |
| `Bull/Base/Bear assumptions loaded` | `Done` |
| `Monthly scenario outputs loaded` | `Done` |
| `Annual scenario outputs loaded` | `Done` |
| `Price-range table loaded` | `Done` |

# Step 8 - Output Structure (Maize Dashboard/Report)

This step publishes dashboard-ready and report-ready Maize outputs from Steps 4, 5, and 7.

## Step 8 workspace

- Folder: [D:/ncel2/ncel-commodity-pricing/SnD/output/maize](D:/ncel2/ncel-commodity-pricing/SnD/output/maize)
- Builder: [D:/ncel2/ncel-commodity-pricing/SnD/output/maize/build_maize_output_structure.py](D:/ncel2/ncel-commodity-pricing/SnD/output/maize/build_maize_output_structure.py)
- DB: [D:/ncel2/ncel-commodity-pricing/SnD/output/maize/maize_output_structure.db](D:/ncel2/ncel-commodity-pricing/SnD/output/maize/maize_output_structure.db)

## Step 8 output tables created (Maize-specific)

| Table | Purpose | Rows |
|---|---|---:|
| `maize_output_blocks` | output block registry | `6` |
| `maize_output_balance_sheet` | balance-sheet output (10y monthly) | `120` |
| `maize_output_stocks_to_use_chart` | crop-year STU chart dataset | `11` |
| `maize_output_price_correlation` | domestic vs global proxy correlation dataset | `120` |
| `maize_output_risk_flags` | latest risk alerts | `3` |
| `maize_output_scenario_summary` | Bull/Base/Bear scenario price bands | `33` |
| `maize_output_snapshot` | latest regime snapshot row | `1` |

## Step 8 date coverage

| Dataset | Data From | Data To |
|---|---|---|
| `maize_output_balance_sheet` | `2016-04-01` | `2026-03-01` |
| `maize_output_price_correlation` | `2016-04-01` | `2026-03-01` |

## Step 8 output mapping

| Output Block | Primary Source | Description |
|---|---|---|
| `Balance sheet table` | `Step 4 balance` | monthly availability, demand, delta, ending stock simulation |
| `Stocks-to-Use ratio chart` | `Step 4 balance` | crop-year STU ratio and classification |
| `Price correlation` | `Step 3 demand + Step 5 drivers` | domestic price-pressure index vs global corn outlook proxy |
| `Risk flags` | `Step 5 + Step 7` | weather/policy/trade/tightness alerts |
| `Scenario summary` | `Step 7 scenarios` | crop-year Bull/Base/Bear price ranges |
| `Snapshot` | `Step 5 + Step 7` | current regime and suggested base range |

## Step 8 formulas used

| Metric | Formula |
|---|---|
| `ending_stock_sim` | `opening_stock + production + imports - total_demand` |
| `rolling_corr_3m` | `corr(last 3 months of domestic_index, global_proxy_index)` |
| `rolling_corr_6m` | `corr(last 6 months of domestic_index, global_proxy_index)` |
| `risk_score(balance_tightness)` | `max(0, min(100, (20 - stu_pct) * 4))` |
| `risk_score(trade_global)` | `max(0, min(100, 50 + (-delta) * 2))` |

## Step 8 sample scenario summary rows

| Scenario | Crop Year | Price Low | Price Mid | Price High |
|---|---|---:|---:|---:|
| `base_normal` | `2015/16` | `60.831633` | `64.714504` | `68.597374` |
| `bear_surplus` | `2015/16` | `57.270863` | `62.250938` | `67.231013` |
| `bull_tight_supply` | `2015/16` | `63.314481` | `68.820088` | `74.325695` |
| `base_normal` | `2016/17` | `66.28889` | `70.520096` | `74.751302` |
| `bear_surplus` | `2016/17` | `61.521915` | `66.871647` | `72.221379` |
| `bull_tight_supply` | `2016/17` | `70.170489` | `76.272271` | `82.374053` |

## Step 8 sample risk flags

| Metric Month | Risk Type | Severity | Risk Score |
|---|---|---|---:|
| `2026-03-01` | `balance_tightness` | `high` | `100.0` |
| `2026-03-01` | `trade_global` | `low` | `51.168242` |
| `2026-03-01` | `weather_policy` | `low` | `50.296687` |

## Step 8 short status

| Item | Status |
|---|---|
| `Output structure DB created` | `Done` |
| `Balance output loaded` | `Done` |
| `STU chart dataset loaded` | `Done` |
| `Correlation dataset loaded` | `Done` |
| `Risk flags loaded` | `Done` |
| `Scenario summary loaded` | `Done` |
| `Snapshot loaded` | `Done` |

# Step 9 - Model Integration (Maize)

This step integrates a trainable monthly Maize forecasting model on top of Step 8 output tables and Step 7 scenario mappings.

## Step 9 workspace

- Folder: [D:/ncel2/ncel-commodity-pricing/SnD/model_integration/maize](D:/ncel2/ncel-commodity-pricing/SnD/model_integration/maize)
- Builder: [D:/ncel2/ncel-commodity-pricing/SnD/model_integration/maize/build_maize_model_integration.py](D:/ncel2/ncel-commodity-pricing/SnD/model_integration/maize/build_maize_model_integration.py)
- Predictor: [D:/ncel2/ncel-commodity-pricing/SnD/model_integration/maize/predict_maize_price.py](D:/ncel2/ncel-commodity-pricing/SnD/model_integration/maize/predict_maize_price.py)
- DB: [D:/ncel2/ncel-commodity-pricing/SnD/model_integration/maize/maize_model_integration.db](D:/ncel2/ncel-commodity-pricing/SnD/model_integration/maize/maize_model_integration.db)
- Artifacts: `D:\ncel2\ncel-commodity-pricing\SnD\model_integration\maize\models\maize_price_model.joblib`, `D:\ncel2\ncel-commodity-pricing\SnD\model_integration\maize\models\maize_price_model_metadata.json`

## Step 9 tables created (Maize-specific)

| Table | Purpose | Rows |
|---|---|---:|
| `maize_model_runs` | run registry and split windows | `1` |
| `maize_model_metrics` | model-wise train/val/test metrics | `9` |
| `maize_feature_importance` | champion model feature ranking | `27` |
| `maize_predictions_monthly` | month-wise actual vs predicted (next month) | `113` |
| `maize_forecast_output` | scenario-wise forecast output | `3` |

## Step 9 run summary

| Field | Value |
|---|---|
| `run_id` | `maize-run-20260409111621` |
| `champion_model` | `linear` |
| `horizon` | `1m` |
| `train window` | `2016-10-01` to `2022-12-01` |
| `validation window` | `2023-01-01` to `2024-12-01` |
| `test window` | `2025-01-01` to `2026-02-01` |
| `feature_count` | `27` |
| `status` | `completed` |

## Step 9 model metrics

| Model | Split | MAE | RMSE | MAPE | Directional Accuracy (%) |
|---|---|---:|---:|---:|---:|
| `linear` | `train` | `0.000000` | `0.000000` | `0.000000` | `100.000000` |
| `linear` | `val` | `2.935275` | `4.732474` | `2.729453` | `66.666667` |
| `linear` | `test` | `8.847453` | `11.577948` | `10.200178` | `64.285714` |
| `ridge` | `train` | `0.000000` | `0.000000` | `0.000000` | `100.000000` |
| `ridge` | `val` | `2.935275` | `4.732474` | `2.729453` | `66.666667` |
| `ridge` | `test` | `8.847453` | `11.577948` | `10.200178` | `64.285714` |
| `rf` | `train` | `0.000000` | `0.000000` | `0.000000` | `100.000000` |
| `rf` | `val` | `2.935275` | `4.732474` | `2.729453` | `66.666667` |
| `rf` | `test` | `8.847453` | `11.577948` | `10.200178` | `64.285714` |

## Step 9 scenario forecast output (latest)

| Forecast Month | Scenario | Forecast Price Index | Low | High | Confidence |
|---|---|---:|---:|---:|---|
| `2026-03-01` | `base_normal` | `100.000000` | `94.000000` | `106.000000` | `medium` |
| `2026-03-01` | `bear_surplus` | `93.907812` | `86.395187` | `101.420437` | `medium` |
| `2026-03-01` | `bull_tight_supply` | `105.782807` | `97.320182` | `114.245431` | `medium` |

## Step 9 feature set (groups)

| Feature Group | Examples |
|---|---|
| `Balance/Supply` | `opening_stock`, `production`, `imports`, `total_availability`, `delta`, `ending_stock_sim` |
| `Demand` | `poultry_demand_cycle`, `ethanol_signal`, `substitution_effect`, `retail_price_pressure` |
| `Drivers` | `driver_composite`, `driver_domestic`, `driver_global`, `driver_weather`, `driver_policy`, `driver_market` |
| `Market link` | `global_price_proxy_index`, `rolling_corr_3m`, `rolling_corr_6m` |
| `Time/Lag` | `month_num`, `month_sin`, `month_cos`, `price_lag_1`, `price_lag_3`, `price_lag_6`, `delta_lag_1` |

## Step 9 short status

| Item | Status |
|---|---|
| `Model integration DB created` | `Done` |
| `Feature store assembly` | `Done` |
| `Train/val/test pipeline` | `Done` |
| `Model comparison + champion selection` | `Done` |
| `Predictions table` | `Done` |
| `Scenario forecast table` | `Done` |
| `Model artifacts saved` | `Done` |

# Step 10 - Operationalization and Monitoring (Maize)

This step adds a runnable operational pipeline with retry, checkpoint/resume, DQ gating, model registry updates, and publish logging.

## Step 10 workspace

- Folder: [D:/ncel2/ncel-commodity-pricing/SnD/ops/maize](D:/ncel2/ncel-commodity-pricing/SnD/ops/maize)
- Orchestrator: [D:/ncel2/ncel-commodity-pricing/SnD/ops/maize/run_maize_pipeline.py](D:/ncel2/ncel-commodity-pricing/SnD/ops/maize/run_maize_pipeline.py)
- Ops DB: [D:/ncel2/ncel-commodity-pricing/SnD/ops/maize/maize_ops.db](D:/ncel2/ncel-commodity-pricing/SnD/ops/maize/maize_ops.db)

## Step 10 orchestration flow

| Order | Step Name | Purpose |
|---|---|---|
| `1` | `ingest_sources` | ingestion placeholder hook for future live connectors |
| `2` | `build_supply` | rebuild Step 2 supply layer |
| `3` | `build_demand` | rebuild Step 3 demand layer |
| `4` | `build_balance` | rebuild Step 4 balance layer |
| `5` | `build_drivers` | rebuild Step 5 drivers layer |
| `6` | `build_data_plan` | rebuild Step 6 data-plan layer |
| `7` | `build_scenarios` | rebuild Step 7 scenario layer |
| `8` | `build_output` | rebuild Step 8 output layer |
| `9` | `build_model` | rebuild Step 9 model-integration layer |
| `10` | `dq_gate + publish` | run critical checks, publish only on pass |

## Step 10 retry and checkpoint behavior

| Item | Configured Behavior |
|---|---|
| `Retries per step` | `3` (configurable via `--max-retries`) |
| `Backoff` | `2s -> 4s -> 8s` |
| `Checkpoint key` | one checkpoint per `run_id + step_name` in `maize_job_steps` |
| `Resume` | `--resume-run-id <id>` skips already completed steps |
| `Publish gate` | publish blocked if critical DQ checks fail |

## Step 10 ops tables (Maize-specific)

| Table | Purpose | Current Rows |
|---|---|---:|
| `maize_job_runs` | run-level audit log | `2` |
| `maize_job_steps` | step-level checkpoint and retries | `18` |
| `maize_data_quality_checks` | DQ results by run | `20` |
| `maize_model_registry` | active model tracking | `1` |
| `maize_publish_log` | publish history | `2` |
| `maize_alert_log` | alert records | `0` |

## Step 10 latest successful run

| Field | Value |
|---|---|
| `run_id` | `maize-ops-20260409113816-cd1fcf` |
| `status` | `completed` |
| `started_at` | `2026-04-09T11:38:16.467981Z` |
| `ended_at` | `2026-04-09T11:38:21.346090Z` |
| `triggered_by` | `manual` |
| `publish_note` | `Published forecast_month=2026-03-01, scenario_count=3` |

## Step 10 latest run step status

| Step | Status | Attempts |
|---|---|---:|
| `ingest_sources` | `completed` | `1` |
| `build_supply` | `completed` | `1` |
| `build_demand` | `completed` | `1` |
| `build_balance` | `completed` | `1` |
| `build_drivers` | `completed` | `1` |
| `build_data_plan` | `completed` | `1` |
| `build_scenarios` | `completed` | `1` |
| `build_output` | `completed` | `1` |
| `build_model` | `completed` | `1` |

## Step 10 DQ gate summary (latest run)

| Result | Count |
|---|---:|
| `pass` | `10` |
| `fail` | `0` |

## Step 10 active model registry

| model_id | run_id | status | val_mae | val_rmse |
|---|---|---|---:|---:|
| `maize-run-20260409113821` | `maize-ops-20260409113816-cd1fcf` | `active` | `2.935275` | `4.732474` |

## Step 10 run commands

| Purpose | Command |
|---|---|
| `Run full pipeline` | `python D:\ncel2\ncel-commodity-pricing\SnD\ops\maize\run_maize_pipeline.py --triggered-by manual` |
| `Resume failed run` | `python D:\ncel2\ncel-commodity-pricing\SnD\ops\maize\run_maize_pipeline.py --resume-run-id <RUN_ID> --triggered-by manual` |
| `Change retry count` | `python D:\ncel2\ncel-commodity-pricing\SnD\ops\maize\run_maize_pipeline.py --max-retries 5 --triggered-by scheduler` |

## Step 10 short status

| Item | Status |
|---|---|
| `Orchestrator implemented` | `Done` |
| `Retry + checkpoint implemented` | `Done` |
| `DQ gate implemented` | `Done` |
| `Publish log implemented` | `Done` |
| `Model registry implemented` | `Done` |
| `End-to-end run validated` | `Done` |

