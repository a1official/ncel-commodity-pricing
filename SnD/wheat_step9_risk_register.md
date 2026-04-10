# Wheat Step 9 - Risk Register

DB:
- [wheat_risk_register.db](D:/ncel2/ncel-commodity-pricing/SnD/risk_register/wheat/wheat_risk_register.db)

Builder:
- [build_wheat_risk_register.py](D:/ncel2/ncel-commodity-pricing/SnD/risk_register/wheat/build_wheat_risk_register.py)

## Step 9 overview

| Item | Value |
|---|---|
| Step | `Document Step 9 - Risk Register` |
| Purpose | build a ranked Wheat risk register covering market, weather, geopolitical, policy, and stock-tightness risks |
| Monthly range | `2016-04-01` to `2026-03-01` |
| Risks implemented | `5` |
| Alert rule | `composite_risk_score >= 60` |

## Tables created

| Table | Purpose |
|---|---|
| `risk_definitions` | master list of Wheat risk types |
| `risk_model_reference` | model approach, source data, formula, and confidence by risk |
| `risk_monthly_metrics` | 10-year monthly risk metric backbone |
| `risk_register_history` | historical scored register snapshots |
| `risk_register_current` | current ranked risk register |
| `risk_alerts` | threshold-based risk alerts |

## Row counts

| Table | Rows |
|---|---:|
| `risk_definitions` | `5` |
| `risk_model_reference` | `5` |
| `risk_monthly_metrics` | `600` |
| `risk_register_history` | `600` |
| `risk_register_current` | `5` |
| `risk_alerts` | `272` |

## Risk definitions

| Risk Key | Risk Name | Category | Direction |
|---|---|---|---|
| `price_volatility` | `Price volatility` | `market` | `bullish_price_risk` |
| `weather_climate` | `Weather / climate` | `weather` | `bullish_price_risk` |
| `geopolitical_black_sea` | `Geopolitical / Black Sea` | `geopolitical` | `bullish_price_risk` |
| `policy_trade_restriction` | `Policy / trade restriction` | `policy` | `mixed_policy_risk` |
| `supply_stock_tightness` | `Supply / stock tightness` | `balance_sheet` | `bullish_price_risk` |

## Risk model reference

| Risk Key | Model Approach | Source Data | Confidence |
|---|---|---|---|
| `price_volatility` | `6-month rolling standard deviation of monthly returns on the wheat retail pressure index` | `Demand DB retail_price_cpi_wheat_pressure` | `medium` |
| `weather_climate` | `Temperature anomaly plus frost-risk composite` | `Drivers DB north_india_winter_temperature, frost_risk` | `medium` |
| `geopolitical_black_sea` | `Weighted geopolitical disruption composite` | `Drivers DB black_sea_corridor, russian_export_policy` | `high` |
| `policy_trade_restriction` | `Weighted India policy intervention composite` | `Drivers DB india_export_policy, msp` | `medium` |
| `supply_stock_tightness` | `Inverse stock-cover and delta stress composite` | `Supply DB opening_stock, total_demand_monthly, delta` | `high` |

## Current risk register

| Rank | Risk Key | As Of Month | Probability Score | Impact Score | Composite Risk Score | Severity |
|---|---|---|---:|---:|---:|---|
| `1` | `price_volatility` | `2026-03-01` | `90.7563` | `90.3782` | `90.6051` | `critical` |
| `2` | `weather_climate` | `2026-03-01` | `89.9160` | `87.4580` | `88.9328` | `critical` |
| `3` | `supply_stock_tightness` | `2026-03-01` | `62.8572` | `75.4286` | `67.8857` | `high` |
| `4` | `policy_trade_restriction` | `2026-03-01` | `61.3445` | `68.6722` | `64.2756` | `high` |
| `5` | `geopolitical_black_sea` | `2026-03-01` | `50.4202` | `66.2101` | `56.7362` | `moderate` |

## Summary

| Item | Status |
|---|---|
| Dedicated Wheat risk DB created | `Yes` |
| 10-year monthly risk history filled | `Yes` |
| Current ranked register available | `Yes` |
| Alert layer available | `Yes` |
| Advanced external models like GARCH / SPI / NDVI fully fetched | `No - approximated with existing local series` |
