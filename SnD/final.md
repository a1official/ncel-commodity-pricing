# Maize Live Data + Model Prediction Plan

## Objective
Build an automated pipeline where latest data is continuously ingested into DB tables and the model predicts updated forecasts reliably.

## 1) Ingestion Jobs
- Pull latest source data (APEDA, USDA, Agmarknet, IMD, etc.).
- Upsert into Maize tables (`maize_factor_monthly_values`, driver tables, and related source tables).
- Store ingestion run status in a `job_runs` table.

## 2) Feature Refresh Job
- Rebuild Step 4-8 derived tables after each successful ingestion.
- Recompute the model-ready feature table for the latest month.

## 3) Prediction Job (Daily/Weekly/Monthly)
- Load active trained model.
- Predict forecast horizons (for example `1m`, `3m`) plus scenario outputs.
- Persist results into `maize_forecast_output` and prediction history tables.

## 4) Scheduled Retraining
- Retrain monthly (or after sufficient new data accumulation).
- Compare candidate model with current champion using validation metrics.
- Promote candidate only if it outperforms the active model.
- Save model version, metrics, and metadata.

## 5) Versioning and Rollback
- Maintain a `model_registry` with `active_model_id`.
- Keep timestamped model artifacts; do not overwrite previous models.
- If a new model underperforms, switch active pointer back to prior model.

## 6) Quality Guards
- Validate freshness, missing values, row counts, and outliers before prediction.
- If validation fails, skip prediction publish and raise alert.

## 7) Orchestration
- Schedule with `cron`, Airflow, or Prefect.
- Recommended flow:
  1. ingest
  2. validate
  3. build features
  4. predict
  5. optional retrain
  6. publish

## 8) API and Dashboard Serving
- API always serves latest successful forecast run.
- Include model version and run timestamp in response.
- Dashboard reads latest scenario and forecast tables directly.

## 9) Recommended Next Build Items
1. Add `orchestrator` script for end-to-end run control.
2. Add `job_runs`, `data_quality_checks`, and `model_registry` operational tables.
3. Add alerting hooks (email/Slack) for failed ingestion or validation.
4. Add retrain policy config (minimum new rows, minimum metric gain).
5. Add backfill command for missed runs.
