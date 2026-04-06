# Wheat Step 1 To Step 9 Flow

```text
+---------------------------------------------------------------+
| Step 1: Define Framework                                      |
| Geography, Horizon, Frequency, Crop Year, HS Code             |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
| Step 2: Build Supply Side                                     |
| DB: wheat_supply_factors.db                                   |
| Tables: factor_definitions, factor_values,                    |
| factor_monthly_values, factor_status, wheat_balance_sheet_*   |
| Formula: Total Availability = Opening Stock + Production      |
|          + Imports                                            |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
| Step 3: Build Demand Side                                     |
| DB: wheat_demand_monthly.db                                   |
| Tables: factor_definitions, factor_monthly_values,            |
| factor_status, source_inventory                               |
| Formula: Total Demand = Domestic Consumption + Exports        |
|          + Feed + Seed + Industrial + Private Stock Build     |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
| Step 4: Calculate Balance Sheet                               |
| Uses: Supply DB + Demand DB                                   |
| Formula: Ending Stock = Opening Stock + Production + Imports  |
|          - Total Use                                          |
| Formula: STU = Ending Stock / Total Use x 100                 |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
| Step 5: Identify Price Drivers                                |
| DB: wheat_price_drivers.db                                    |
| Tables: factor_monthly_values, driver_reference,              |
| driver_impact_score, driver_impact_score_annual               |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
| Step 6: Data Collection Plan                                  |
| Sources: prices, arrivals, weather, stocks, trade, benchmark, |
| support signals, sowing, procurement                          |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
| Step 7: Build Scenarios                                       |
| DB: wheat_scenarios.db                                        |
| Tables: scenario_definitions, scenario_runs,                  |
| scenario_assumptions, scenario_price_ranges                   |
| Logic: Bull / Base / Bear mapped to price ranges              |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
| Step 8: Output Structure                                      |
| DB: wheat_output_structure.db                                 |
| Tables: balance_sheet_output, STU chart,                      |
| price_correlation_series, risk_flags, scenario_summary        |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
| Step 9: Model Integration                                     |
| DB: wheat_model_integration.db                                |
| Tables: model_registry, feature_source_map, training_runs,    |
| forecast_integration_status, api_output_contract              |
| Logic: Daily Wheat ML model with embedded driver scores       |
+---------------------------------------------------------------+
```

## Related Files

- [Blueprint](D:/ncel2/ncel-commodity-pricing/SnD/blueprint.md)
- [Supply DB](D:/ncel2/ncel-commodity-pricing/SnD/supply/wheat/wheat_supply_factors.db)
- [Demand DB](D:/ncel2/ncel-commodity-pricing/SnD/demand/wheat/wheat_demand_monthly.db)
- [Price Drivers DB](D:/ncel2/ncel-commodity-pricing/SnD/price_drivers/wheat/wheat_price_drivers.db)
- [Scenarios DB](D:/ncel2/ncel-commodity-pricing/SnD/scenarios/wheat/wheat_scenarios.db)
- [Output DB](D:/ncel2/ncel-commodity-pricing/SnD/output/wheat/wheat_output_structure.db)
- [Model Integration DB](D:/ncel2/ncel-commodity-pricing/SnD/model_integration/wheat/wheat_model_integration.db)
