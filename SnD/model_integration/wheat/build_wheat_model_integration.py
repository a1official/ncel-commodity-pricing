from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / "wheat_model_integration.db"
SUPPORT_DB = ROOT / "backend" / "data" / "wheat_model_support.db"
MODEL_METADATA_PATH = ROOT / "backend" / "data" / "wheat_price_model_metadata.json"
MODEL_PATH = ROOT / "backend" / "data" / "wheat_price_model.joblib"
DRIVER_DB = ROOT / "SnD" / "price_drivers" / "wheat" / "wheat_price_drivers.db"
SCENARIO_DB = ROOT / "SnD" / "scenarios" / "wheat" / "wheat_scenarios.db"
OUTPUT_STRUCTURE_DB = ROOT / "SnD" / "output" / "wheat" / "wheat_output_structure.db"
SUPPLY_DB = ROOT / "SnD" / "supply" / "wheat" / "wheat_supply_factors.db"
DEMAND_DB = ROOT / "SnD" / "demand" / "wheat" / "wheat_demand_monthly.db"
BACKEND_ROOT = ROOT / "backend"
UPDATED_AT = datetime.now(UTC).isoformat().replace("+00:00", "Z")

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.wheat_ml_forecasting import WheatFeatureForecaster  # noqa: E402


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS model_registry (
            model_key TEXT PRIMARY KEY,
            commodity TEXT NOT NULL,
            model_name TEXT NOT NULL,
            model_type TEXT NOT NULL,
            target_name TEXT NOT NULL,
            status TEXT NOT NULL,
            feature_db_path TEXT NOT NULL,
            model_path TEXT NOT NULL,
            metadata_path TEXT NOT NULL,
            trained_at TEXT,
            feature_count INTEGER NOT NULL,
            uses_driver_features INTEGER NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS feature_source_map (
            id TEXT PRIMARY KEY,
            model_key TEXT NOT NULL,
            feature_name TEXT NOT NULL,
            feature_group TEXT NOT NULL,
            source_step TEXT NOT NULL,
            source_db TEXT NOT NULL,
            source_table TEXT NOT NULL,
            source_field_or_factor TEXT NOT NULL,
            derivation_logic TEXT NOT NULL,
            included_in_model INTEGER NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS training_runs (
            run_id TEXT PRIMARY KEY,
            model_key TEXT NOT NULL,
            trained_at TEXT NOT NULL,
            train_rows INTEGER NOT NULL,
            test_rows INTEGER NOT NULL,
            train_end_date TEXT NOT NULL,
            test_end_date TEXT NOT NULL,
            training_min_date TEXT,
            training_max_date TEXT,
            state_count INTEGER NOT NULL,
            feature_count INTEGER NOT NULL,
            mae REAL NOT NULL,
            rmse REAL NOT NULL,
            mape REAL NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS forecast_integration_status (
            snapshot_id TEXT PRIMARY KEY,
            model_key TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            latest_date TEXT NOT NULL,
            current_weighted_price REAL NOT NULL,
            baseline_next_7d_avg_price REAL NOT NULL,
            predicted_next_7d_avg_price REAL NOT NULL,
            predicted_change_pct REAL NOT NULL,
            driver_signal_pct REAL NOT NULL,
            driver_adjustment_pct REAL NOT NULL,
            driver_features_embedded_in_model INTEGER NOT NULL,
            confidence INTEGER NOT NULL,
            projection_count INTEGER NOT NULL,
            state_prediction_count INTEGER NOT NULL,
            top_level_payload_keys TEXT NOT NULL,
            latest_context_keys TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS api_output_contract (
            contract_key TEXT PRIMARY KEY,
            model_key TEXT NOT NULL,
            payload_location TEXT NOT NULL,
            description TEXT NOT NULL,
            downstream_consumer TEXT NOT NULL,
            source_layer TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def _load_model_metadata() -> dict[str, Any]:
    return json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))


def _load_training_matrix_stats() -> dict[str, Any]:
    with _connect(SUPPORT_DB) as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS row_count,
                MIN(date) AS min_date,
                MAX(date) AS max_date,
                COUNT(DISTINCT state) AS state_count
            FROM wheat_training_matrix_daily
            """
        ).fetchone()
    return dict(row) if row is not None else {"row_count": 0, "min_date": None, "max_date": None, "state_count": 0}


def _feature_mapping(feature_name: str) -> dict[str, str]:
    if feature_name.startswith("state_"):
        return {
            "feature_group": "state_encoding",
            "source_step": "Step 9",
            "source_db": str(SUPPORT_DB),
            "source_table": "wheat_training_matrix_daily",
            "source_field_or_factor": feature_name,
            "derivation_logic": "One-hot encoded state identifier used by the daily Wheat model.",
            "notes": "Model encoding feature.",
        }
    if feature_name in {"year", "month", "day", "iso_week", "day_of_year", "quarter", "is_weekend", "month_sin", "month_cos", "day_of_year_sin", "day_of_year_cos"}:
        return {
            "feature_group": "calendar",
            "source_step": "Step 6",
            "source_db": str(SUPPORT_DB),
            "source_table": "wheat_feature_daily",
            "source_field_or_factor": feature_name,
            "derivation_logic": "Calendar decomposition and seasonality encoding from daily feature dates.",
            "notes": "Derived temporal feature.",
        }
    if feature_name in {"is_rabi_sowing_window", "is_rabi_growth_window", "is_rabi_harvest_window", "is_procurement_window"}:
        return {
            "feature_group": "seasonal_window",
            "source_step": "Step 6",
            "source_db": str(SUPPORT_DB),
            "source_table": "wheat_feature_daily",
            "source_field_or_factor": feature_name,
            "derivation_logic": "Seasonal crop-window flags derived from the Wheat crop calendar.",
            "notes": "Calendar rule feature.",
        }
    if feature_name.startswith("price_") or feature_name in {"modal_price", "normalized_price_per_kg"}:
        return {
            "feature_group": "spot_price",
            "source_step": "Step 6",
            "source_db": str(SUPPORT_DB),
            "source_table": "wheat_feature_daily",
            "source_field_or_factor": feature_name,
            "derivation_logic": "Daily AGMARKNET spot-price level, lag, or rolling statistic in the training matrix.",
            "notes": "Built from local mandi history.",
        }
    if feature_name.startswith("arrival_") or feature_name in {"market_count", "variety_count", "record_count"}:
        return {
            "feature_group": "market_activity",
            "source_step": "Step 6",
            "source_db": str(SUPPORT_DB),
            "source_table": "wheat_feature_daily",
            "source_field_or_factor": feature_name,
            "derivation_logic": "Daily arrivals and market-depth signals aggregated from mandi activity.",
            "notes": "Built from AGMARKNET daily market records.",
        }
    if feature_name in {
        "temperature_2m_mean",
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_sum",
        "rain_sum",
        "wind_speed_10m_max",
        "shortwave_radiation_sum",
        "et0_fao_evapotranspiration",
        "relative_humidity_2m_mean",
        "soil_moisture_0_to_7cm_mean",
        "soil_moisture_7_to_28cm_mean",
        "soil_temperature_0_to_7cm_mean",
        "precipitation_rolling_sum_7",
        "temp_rolling_mean_7",
        "humidity_rolling_mean_7",
        "soil_moisture_rolling_mean_7",
    }:
        return {
            "feature_group": "weather",
            "source_step": "Step 6",
            "source_db": str(SUPPORT_DB),
            "source_table": "wheat_feature_daily",
            "source_field_or_factor": feature_name,
            "derivation_logic": "Weather and soil conditions merged into the daily Wheat feature matrix.",
            "notes": "Open-Meteo derived feature.",
        }
    if feature_name in {"wheat_yield_kg_per_hectare", "wheat_production_million_tonnes", "wheat_area_million_hectare", "government_buffer_wheat_stock", "government_buffer_wheat_stock_norm", "wheat_central_pool_exports"}:
        return {
            "feature_group": "supply_demand_support",
            "source_step": "Step 2/3/4/6",
            "source_db": str(SUPPORT_DB),
            "source_table": "wheat_indicator_history",
            "source_field_or_factor": feature_name,
            "derivation_logic": "As-of join from indicator history into daily training rows.",
            "notes": "Support-series feature aligned to daily dates.",
        }
    if feature_name in {"cpi_inflation_rate", "policy_repo_rate"}:
        return {
            "feature_group": "macro_policy",
            "source_step": "Step 6",
            "source_db": str(SUPPORT_DB),
            "source_table": "wheat_indicator_history",
            "source_field_or_factor": feature_name,
            "derivation_logic": "As-of joined macro/policy support indicator used by the Wheat model.",
            "notes": "Macro support feature.",
        }
    if feature_name in {"global_wheat_benchmark_avg_usd_mt", "global_wheat_benchmark_srw_usd_mt", "global_wheat_benchmark_hrw_usd_mt"}:
        return {
            "feature_group": "global_price",
            "source_step": "Step 6",
            "source_db": str(SUPPORT_DB),
            "source_table": "global_wheat_benchmark_monthly",
            "source_field_or_factor": feature_name,
            "derivation_logic": "Monthly global Wheat benchmark joined to the daily training matrix by month.",
            "notes": "International benchmark feature.",
        }
    if feature_name in {"msp_inr_quintal", "cost_of_production_inr_quintal", "margin_over_cost_percent", "procurement_actual_lmt", "procurement_estimated_lmt", "progressive_area_sown_lakh_hectare", "final_area_previous_season_lakh_hectare"}:
        return {
            "feature_group": "support_signals",
            "source_step": "Step 5/6",
            "source_db": str(SUPPORT_DB),
            "source_table": "wheat_support_signals",
            "source_field_or_factor": feature_name,
            "derivation_logic": "As-of joined support signal carried into the daily training matrix.",
            "notes": "Policy or seasonal support signal.",
        }
    if feature_name.startswith("wheat_driver_"):
        return {
            "feature_group": "driver_scores",
            "source_step": "Step 5/6",
            "source_db": str(DRIVER_DB),
            "source_table": "driver_impact_score",
            "source_field_or_factor": feature_name,
            "derivation_logic": "Monthly Wheat driver score joined by month and embedded directly into model training.",
            "notes": "Driver features are embedded in the model.",
        }
    return {
        "feature_group": "other",
        "source_step": "Step 9",
        "source_db": str(SUPPORT_DB),
        "source_table": "wheat_training_matrix_daily",
        "source_field_or_factor": feature_name,
        "derivation_logic": "Present in the trained Wheat design matrix.",
        "notes": "Unclassified feature.",
    }


def _build_model_registry(metadata: dict[str, Any]) -> tuple:
    feature_columns = metadata.get("feature_columns", [])
    uses_driver_features = int(any(column.startswith("wheat_driver_") for column in feature_columns))
    return (
        "wheat_price_model_v1",
        "Wheat",
        "Wheat Daily Price Forecast Model",
        metadata.get("model_type", "unknown"),
        metadata.get("target", "target_next_7d_avg_price"),
        metadata.get("status", "unknown"),
        metadata.get("feature_db_path", str(SUPPORT_DB)),
        str(MODEL_PATH),
        str(MODEL_METADATA_PATH),
        metadata.get("trained_at"),
        len(feature_columns),
        uses_driver_features,
        "HistGradientBoostingRegressor trained on daily Wheat market, weather, support, benchmark, and driver features.",
        UPDATED_AT,
    )


def _build_feature_rows(metadata: dict[str, Any]) -> list[tuple]:
    rows: list[tuple] = []
    for feature_name in metadata.get("feature_columns", []):
        mapping = _feature_mapping(feature_name)
        rows.append(
            (
                str(uuid.uuid4()),
                "wheat_price_model_v1",
                feature_name,
                mapping["feature_group"],
                mapping["source_step"],
                mapping["source_db"],
                mapping["source_table"],
                mapping["source_field_or_factor"],
                mapping["derivation_logic"],
                1,
                mapping["notes"],
                UPDATED_AT,
            )
        )
    return rows


def _build_training_run(metadata: dict[str, Any], matrix_stats: dict[str, Any]) -> tuple:
    metrics = metadata.get("metrics", {})
    return (
        str(uuid.uuid4()),
        "wheat_price_model_v1",
        metadata.get("trained_at", UPDATED_AT),
        int(metadata.get("train_rows", 0)),
        int(metadata.get("test_rows", 0)),
        metadata.get("train_end_date", ""),
        metadata.get("test_end_date", ""),
        matrix_stats.get("min_date"),
        matrix_stats.get("max_date"),
        int(matrix_stats.get("state_count", 0)),
        len(metadata.get("feature_columns", [])),
        float(metrics.get("mae", 0.0)),
        float(metrics.get("rmse", 0.0)),
        float(metrics.get("mape", 0.0)),
        "Current active training run persisted from wheat_price_model_metadata.json and training matrix stats.",
        UPDATED_AT,
    )


def _build_forecast_snapshot() -> tuple:
    payload = WheatFeatureForecaster().forecast(horizon_days=42, simulations=200)
    latest_context = payload["latest_context"]
    return (
        str(uuid.uuid4()),
        "wheat_price_model_v1",
        payload.get("generated_at", UPDATED_AT),
        latest_context["latest_date"],
        float(latest_context["current_weighted_price"]),
        float(latest_context["baseline_next_7d_avg_price"]),
        float(latest_context["predicted_next_7d_avg_price"]),
        float(latest_context["predicted_change_pct"]),
        float(latest_context["driver_signal_pct"]),
        float(latest_context["driver_adjustment_pct"]),
        int(bool(latest_context["driver_features_embedded_in_model"])),
        int(payload.get("confidence", 0)),
        int(len(payload.get("projections", []))),
        int(len(payload.get("state_predictions", []))),
        json.dumps(list(payload.keys())),
        json.dumps(list(latest_context.keys())),
        "Live snapshot from WheatFeatureForecaster; used to document how the active model is integrated into downstream outputs.",
        UPDATED_AT,
    )


def _build_contract_rows() -> list[tuple]:
    return [
        (
            "forecast_status",
            "wheat_price_model_v1",
            "forecast.status",
            "Top-level forecast status for the Wheat model response.",
            "API / dashboard",
            "backend.app.services.wheat_ml_forecasting.WheatFeatureForecaster",
            UPDATED_AT,
        ),
        (
            "latest_context",
            "wheat_price_model_v1",
            "forecast.latest_context",
            "Current weighted price, next-7d prediction, change, and driver-embedding flags.",
            "API / analytics",
            "wheat_ml_forecasting payload",
            UPDATED_AT,
        ),
        (
            "driver_overlay",
            "wheat_price_model_v1",
            "forecast.driver_overlay",
            "Explainability layer showing current driver scores, bullish/bearish drivers, and signal strength.",
            "API / analytics / reporting",
            "wheat_price_drivers.db",
            UPDATED_AT,
        ),
        (
            "daily_forecast",
            "wheat_price_model_v1",
            "forecast.daily_forecast",
            "Day-wise p10/p50/p90 Wheat path used by charts and scenario anchoring.",
            "Forecast charts",
            "wheat_ml_forecasting Monte Carlo output",
            UPDATED_AT,
        ),
        (
            "state_predictions",
            "wheat_price_model_v1",
            "forecast.state_predictions",
            "Top state-level Wheat forecast slice for operational dashboards.",
            "Operational dashboard",
            "wheat_training_matrix_daily + forecast scoring",
            UPDATED_AT,
        ),
        (
            "scenario_anchor",
            "wheat_price_model_v1",
            "scenarios.anchor_price",
            "30-day forecast anchor feeding Step 7 price range generation.",
            "Scenario engine",
            str(SCENARIO_DB),
            UPDATED_AT,
        ),
        (
            "output_structure",
            "wheat_price_model_v1",
            "output.balance_sheet_output / output.scenario_summary",
            "Step 8 reporting tables that consume model-informed forecast and scenario layers.",
            "Dashboard / report",
            str(OUTPUT_STRUCTURE_DB),
            UPDATED_AT,
        ),
    ]


def build_wheat_model_integration() -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = _load_model_metadata()
    matrix_stats = _load_training_matrix_stats()

    with _connect(OUTPUT_DB) as conn:
        _ensure_schema(conn)
        conn.execute("DELETE FROM model_registry")
        conn.execute("DELETE FROM feature_source_map")
        conn.execute("DELETE FROM training_runs")
        conn.execute("DELETE FROM forecast_integration_status")
        conn.execute("DELETE FROM api_output_contract")

        conn.execute(
            """
            INSERT INTO model_registry (
                model_key, commodity, model_name, model_type, target_name, status, feature_db_path,
                model_path, metadata_path, trained_at, feature_count, uses_driver_features, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _build_model_registry(metadata),
        )
        conn.executemany(
            """
            INSERT INTO feature_source_map (
                id, model_key, feature_name, feature_group, source_step, source_db, source_table,
                source_field_or_factor, derivation_logic, included_in_model, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _build_feature_rows(metadata),
        )
        conn.execute(
            """
            INSERT INTO training_runs (
                run_id, model_key, trained_at, train_rows, test_rows, train_end_date, test_end_date,
                training_min_date, training_max_date, state_count, feature_count, mae, rmse, mape, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _build_training_run(metadata, matrix_stats),
        )
        conn.execute(
            """
            INSERT INTO forecast_integration_status (
                snapshot_id, model_key, generated_at, latest_date, current_weighted_price,
                baseline_next_7d_avg_price, predicted_next_7d_avg_price, predicted_change_pct,
                driver_signal_pct, driver_adjustment_pct, driver_features_embedded_in_model, confidence,
                projection_count, state_prediction_count, top_level_payload_keys, latest_context_keys,
                notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _build_forecast_snapshot(),
        )
        conn.executemany(
            """
            INSERT INTO api_output_contract (
                contract_key, model_key, payload_location, description, downstream_consumer, source_layer, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            _build_contract_rows(),
        )
        conn.commit()

        summary = {
            "db_path": str(OUTPUT_DB),
            "tables": {
                "model_registry": conn.execute("SELECT COUNT(*) FROM model_registry").fetchone()[0],
                "feature_source_map": conn.execute("SELECT COUNT(*) FROM feature_source_map").fetchone()[0],
                "training_runs": conn.execute("SELECT COUNT(*) FROM training_runs").fetchone()[0],
                "forecast_integration_status": conn.execute("SELECT COUNT(*) FROM forecast_integration_status").fetchone()[0],
                "api_output_contract": conn.execute("SELECT COUNT(*) FROM api_output_contract").fetchone()[0],
            },
        }
    return summary


if __name__ == "__main__":
    print(json.dumps(build_wheat_model_integration(), indent=2))
