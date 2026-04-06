from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from app.services.wheat_forecasting import WheatMonteCarloForecaster


FEATURE_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "wheat_model_support.db"
ROOT_HISTORY_DB_PATH = Path(__file__).resolve().parents[3] / "agmarknet_history_local.db"
LEGACY_HISTORY_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "agmarknet_history_local.db"
MODEL_DIR = Path(__file__).resolve().parents[2] / "data"
MODEL_PATH = MODEL_DIR / "wheat_price_model.joblib"
MODEL_METADATA_PATH = MODEL_DIR / "wheat_price_model_metadata.json"
WHEAT_DRIVER_DB_PATH = Path(__file__).resolve().parents[3] / "SnD" / "price_drivers" / "wheat" / "wheat_price_drivers.db"

EXCLUDED_COLUMNS = {
    "date",
    "created_at",
    "target_next_day_price",
    "target_next_7d_avg_price",
}
WHEAT_DRIVER_FEATURE_COLUMNS = {
    "wheat_driver_composite_score",
    "wheat_driver_domestic_score",
    "wheat_driver_weather_score",
    "wheat_driver_global_score",
    "wheat_driver_policy_score",
    "wheat_driver_price_adjustment_pct",
}
MODEL_DROPPED_FEATURE_COLUMNS = {
    "wheat_export_quantity_monthly",
    "wheat_import_quantity_monthly",
    "wheat_export_value_inr_crore_monthly",
    "wheat_import_value_inr_crore_monthly",
    "wheat_export_concentration_hhi",
    "wheat_import_concentration_hhi",
    "wheat_export_seasonality_share_pct",
    "wheat_risk_price_volatility_score",
    "wheat_risk_geopolitical_black_sea_score",
    "wheat_risk_policy_trade_restriction_score",
    "wheat_risk_supply_stock_tightness_score",
}


@dataclass
class WheatModelConfig:
    max_iter: int = 350
    learning_rate: float = 0.05
    max_depth: int = 6
    min_samples_leaf: int = 30
    l2_regularization: float = 0.05
    random_state: int = 42


def _resolve_history_db_path() -> str:
    if ROOT_HISTORY_DB_PATH.exists():
        return str(ROOT_HISTORY_DB_PATH)
    return str(LEGACY_HISTORY_DB_PATH)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _sanitize_for_json(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {key: _sanitize_for_json(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_sanitize_for_json(item) for item in payload]
    if isinstance(payload, tuple):
        return [_sanitize_for_json(item) for item in payload]
    if isinstance(payload, float):
        return payload if math.isfinite(payload) else 0.0
    return payload


class WheatFeatureForecaster:
    def __init__(
        self,
        feature_db_path: str | None = None,
        model_path: str | None = None,
        metadata_path: str | None = None,
    ) -> None:
        self.feature_db_path = feature_db_path or str(FEATURE_DB_PATH)
        self.model_path = model_path or str(MODEL_PATH)
        self.metadata_path = metadata_path or str(MODEL_METADATA_PATH)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.feature_db_path)

    def _load_training_frame(self) -> pd.DataFrame:
        with self._connect() as conn:
            frame = pd.read_sql_query(
                """
                SELECT *
                FROM wheat_training_matrix_daily
                ORDER BY date, state
                """,
                conn,
            )
        if frame.empty:
            raise ValueError("wheat_training_matrix_daily is empty. Build the training matrix first.")
        frame["date"] = pd.to_datetime(frame["date"])
        return frame

    @staticmethod
    def _prepare_features(frame: pd.DataFrame, feature_columns: list[str] | None = None) -> pd.DataFrame:
        working = frame.copy()
        working["state"] = working["state"].astype(str)
        base_columns = [
            column
            for column in working.columns
            if column not in EXCLUDED_COLUMNS and column not in MODEL_DROPPED_FEATURE_COLUMNS
        ]
        design = pd.get_dummies(working[base_columns], columns=["state"])
        if feature_columns is None:
            return design
        for column in feature_columns:
            if column not in design.columns:
                design[column] = 0.0
        return design[feature_columns]

    def train(self) -> dict[str, Any]:
        frame = self._load_training_frame()
        usable = frame.dropna(subset=["target_next_7d_avg_price"]).copy()
        if usable.empty:
            raise ValueError("No training rows with target_next_7d_avg_price available.")

        unique_dates = sorted(usable["date"].drop_duplicates().tolist())
        split_index = max(1, int(len(unique_dates) * 0.8))
        train_cutoff = unique_dates[split_index - 1]

        train_frame = usable[usable["date"] <= train_cutoff].copy()
        test_frame = usable[usable["date"] > train_cutoff].copy()
        if test_frame.empty:
            test_frame = train_frame.tail(min(len(train_frame), 500)).copy()

        feature_columns = None
        X_train = self._prepare_features(train_frame)
        feature_columns = list(X_train.columns)
        X_test = self._prepare_features(test_frame, feature_columns)
        y_train = train_frame["target_next_7d_avg_price"].astype(float)
        y_test = test_frame["target_next_7d_avg_price"].astype(float)

        config = WheatModelConfig()
        model = HistGradientBoostingRegressor(
            loss="squared_error",
            learning_rate=config.learning_rate,
            max_iter=config.max_iter,
            max_depth=config.max_depth,
            min_samples_leaf=config.min_samples_leaf,
            l2_regularization=config.l2_regularization,
            random_state=config.random_state,
        )
        model.fit(X_train, y_train)

        predictions = model.predict(X_test)
        mae = float(mean_absolute_error(y_test, predictions))
        rmse = float(math.sqrt(mean_squared_error(y_test, predictions)))
        mape = float(np.mean(np.abs((y_test - predictions) / np.clip(np.abs(y_test), 1e-6, None))) * 100)

        metadata = {
            "status": "trained",
            "trained_at": datetime.utcnow().isoformat() + "Z",
            "feature_db_path": self.feature_db_path,
            "model_type": "HistGradientBoostingRegressor",
            "target": "target_next_7d_avg_price",
            "feature_columns": feature_columns,
            "train_rows": int(len(train_frame)),
            "test_rows": int(len(test_frame)),
            "train_end_date": pd.Timestamp(train_frame["date"].max()).date().isoformat(),
            "test_end_date": pd.Timestamp(test_frame["date"].max()).date().isoformat(),
            "metrics": {
                "mae": round(mae, 4),
                "rmse": round(rmse, 4),
                "mape": round(mape, 4),
            },
        }

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": model, "feature_columns": feature_columns}, self.model_path)
        Path(self.metadata_path).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return metadata

    def _load_bundle(self) -> tuple[HistGradientBoostingRegressor, dict[str, Any]]:
        if not Path(self.model_path).exists() or not Path(self.metadata_path).exists():
            self.train()
        bundle = joblib.load(self.model_path)
        metadata = json.loads(Path(self.metadata_path).read_text(encoding="utf-8"))
        return bundle["model"], metadata

    def _load_driver_overlay(self, latest_date: pd.Timestamp) -> dict[str, Any]:
        if not WHEAT_DRIVER_DB_PATH.exists():
            return {
                "status": "unavailable",
                "metric_month": latest_date.to_period("M").to_timestamp().date().isoformat(),
                "composite_score": 50.0,
                "implied_price_adjustment_pct": 0.0,
                "bucket_scores": {"domestic": 50.0, "weather": 50.0, "global": 50.0, "policy": 50.0},
                "bullish_drivers": [],
                "bearish_drivers": [],
                "drivers": [],
            }

        metric_month = latest_date.to_period("M").to_timestamp().date().isoformat()
        with sqlite3.connect(str(WHEAT_DRIVER_DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            impact_row = conn.execute(
                """
                SELECT *
                FROM driver_impact_score
                WHERE metric_month <= ?
                ORDER BY metric_month DESC
                LIMIT 1
                """,
                (metric_month,),
            ).fetchone()
            driver_rows = conn.execute(
                """
                SELECT
                    d.factor_key,
                    d.factor_name,
                    d.driver_bucket,
                    r.source_website,
                    r.formula,
                    r.confidence AS reference_confidence,
                    s.monthly_availability,
                    s.load_mode,
                    v.metric_month,
                    v.value,
                    v.unit,
                    v.source_name,
                    v.source_url,
                    v.method,
                    v.confidence,
                    v.notes
                FROM factor_monthly_values v
                JOIN factor_definitions d ON d.factor_key = v.factor_key
                LEFT JOIN driver_reference r ON r.factor_key = v.factor_key
                LEFT JOIN factor_status s ON s.factor_key = v.factor_key
                WHERE v.metric_month = ?
                ORDER BY d.driver_bucket, d.factor_name
                """,
                (impact_row["metric_month"] if impact_row else metric_month,),
            ).fetchall()

        if impact_row is None:
            return {
                "status": "unavailable",
                "metric_month": metric_month,
                "composite_score": 50.0,
                "implied_price_adjustment_pct": 0.0,
                "bucket_scores": {"domestic": 50.0, "weather": 50.0, "global": 50.0, "policy": 50.0},
                "bullish_drivers": [],
                "bearish_drivers": [],
                "drivers": [],
            }

        return {
            "status": "ready",
            "metric_month": impact_row["metric_month"],
            "marketing_year": impact_row["marketing_year"],
            "composite_score": round(_safe_float(impact_row["composite_score"], 50.0), 4),
            "implied_price_adjustment_pct": round(_safe_float(impact_row["implied_price_adjustment_pct"], 0.0), 4),
            "bucket_scores": {
                "domestic": round(_safe_float(impact_row["domestic_score"], 50.0), 4),
                "weather": round(_safe_float(impact_row["weather_score"], 50.0), 4),
                "global": round(_safe_float(impact_row["global_score"], 50.0), 4),
                "policy": round(_safe_float(impact_row["policy_score"], 50.0), 4),
            },
            "bullish_drivers": _sanitize_for_json(json.loads(impact_row["bullish_drivers_json"])),
            "bearish_drivers": _sanitize_for_json(json.loads(impact_row["bearish_drivers_json"])),
            "notes": impact_row["notes"],
            "drivers": [
                {
                    "factor_key": row["factor_key"],
                    "factor_name": row["factor_name"],
                    "bucket": row["driver_bucket"],
                    "metric_month": row["metric_month"],
                    "value": round(_safe_float(row["value"]), 4),
                    "unit": row["unit"],
                    "source_name": row["source_name"],
                    "source_url": row["source_url"] or row["source_website"],
                    "source_website": row["source_website"],
                    "formula": row["formula"],
                    "confidence": row["reference_confidence"] or row["confidence"],
                    "monthly_availability": row["monthly_availability"],
                    "load_mode": row["load_mode"],
                    "method": row["method"],
                    "notes": row["notes"],
                }
                for row in driver_rows
            ],
        }

    def _latest_state_frame(self) -> pd.DataFrame:
        frame = self._load_training_frame()
        latest_date = frame["date"].max()
        latest = frame[frame["date"] == latest_date].copy()
        if latest.empty:
            raise ValueError("No latest state frame available for forecasting.")
        return latest.sort_values("state")

    def _load_indicator_history(self) -> pd.DataFrame:
        with self._connect() as conn:
            columns = pd.read_sql_query("PRAGMA table_info(wheat_indicator_history)", conn)
            available = set(columns["name"].tolist()) if not columns.empty else set()
            date_column = "date" if "date" in available else "indicator_date"
            period_column = "period" if "period" in available else "period_label"
            source_column = "source" if "source" in available else "source_name"
            select_columns = ["indicator_name", f"{date_column} AS date", "value"]
            if "indicator_key" in available:
                select_columns.insert(1, "indicator_key")
            if period_column in available:
                select_columns.append(f"{period_column} AS period")
            if "unit" in available:
                select_columns.append("unit")
            if source_column in available:
                select_columns.append(f"{source_column} AS source")
            frame = pd.read_sql_query(
                f"""
                SELECT {", ".join(select_columns)}
                FROM wheat_indicator_history
                ORDER BY date ASC
                """,
                conn,
            )
        if frame.empty:
            return frame
        frame["date"] = pd.to_datetime(frame["date"])
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        if "period" not in frame.columns:
            frame["period"] = frame["date"].dt.year.astype(str)
        if "unit" not in frame.columns:
            frame["unit"] = None
        if "source" not in frame.columns:
            frame["source"] = None
        if "indicator_key" not in frame.columns:
            frame["indicator_key"] = frame["indicator_name"]
        return frame.dropna(subset=["date", "value"])

    @staticmethod
    def _weighted_average(values: pd.Series, weights: pd.Series) -> float:
        safe_weights = pd.to_numeric(weights, errors="coerce").fillna(0.0).clip(lower=0.0)
        if float(safe_weights.sum()) > 0:
            return float(np.average(values, weights=safe_weights))
        return float(pd.to_numeric(values, errors="coerce").mean())

    def _build_dashboard_signals(self, frame: pd.DataFrame, latest: pd.DataFrame) -> dict[str, Any]:
        working = frame.copy()
        working["arrival_quantity"] = pd.to_numeric(working["arrival_quantity"], errors="coerce").fillna(0.0)

        def weighted_group(column: str) -> pd.Series:
            return working.groupby("date").apply(
                lambda group: self._weighted_average(group[column], group["arrival_quantity"])
            )

        market_daily = pd.DataFrame(
            {
                "date": sorted(working["date"].drop_duplicates()),
            }
        )
        market_daily["modal_price"] = weighted_group("modal_price").values
        market_daily["arrival_quantity"] = working.groupby("date")["arrival_quantity"].sum().values
        market_daily["market_count"] = working.groupby("date")["market_count"].sum().values
        market_daily["state_count"] = working.groupby("date")["state"].nunique().values
        market_daily["variety_count"] = working.groupby("date")["variety_count"].sum().values

        weather_daily = pd.DataFrame({"date": market_daily["date"]})
        weather_daily["temperature_2m_mean"] = weighted_group("temperature_2m_mean").values
        weather_daily["precipitation_sum"] = weighted_group("precipitation_sum").values
        weather_daily["soil_moisture_0_to_7cm_mean"] = weighted_group("soil_moisture_0_to_7cm_mean").values
        weather_daily["relative_humidity_2m_mean"] = weighted_group("relative_humidity_2m_mean").values

        indicators = self._load_indicator_history()
        indicator_names = [
            "wheat_yield_kg_per_hectare",
            "wheat_production",
            "wheat_area",
            "cpi_inflation_rate",
            "policy_repo_rate",
            "government_buffer_wheat_stock",
            "wheat_central_pool_exports",
        ]
        indicator_payload = {}
        for name in indicator_names:
            subset = indicators[indicators["indicator_key"] == name].tail(12)
            indicator_payload[name] = [
                {
                    "date": pd.Timestamp(row["date"]).date().isoformat(),
                    "period": row["period"],
                    "value": round(float(row["value"]), 4),
                    "unit": row["unit"],
                    "source": row["source"],
                }
                for _, row in subset.iterrows()
            ]

        latest_snapshot = latest.copy()
        latest_snapshot["arrival_quantity"] = pd.to_numeric(latest_snapshot["arrival_quantity"], errors="coerce").fillna(0.0)
        snapshot = {
            "msp_inr_quintal": round(_safe_float(self._weighted_average(latest_snapshot["msp_inr_quintal"], latest_snapshot["arrival_quantity"])), 4),
            "cost_of_production_inr_quintal": round(
                _safe_float(self._weighted_average(latest_snapshot["cost_of_production_inr_quintal"], latest_snapshot["arrival_quantity"])), 4
            ),
            "margin_over_cost_percent": round(
                _safe_float(self._weighted_average(latest_snapshot["margin_over_cost_percent"], latest_snapshot["arrival_quantity"])), 4
            ),
            "global_wheat_benchmark_avg_usd_mt": round(
                _safe_float(self._weighted_average(latest_snapshot["global_wheat_benchmark_avg_usd_mt"], latest_snapshot["arrival_quantity"])), 4
            ),
            "government_buffer_wheat_stock": round(
                _safe_float(self._weighted_average(latest_snapshot["government_buffer_wheat_stock"], latest_snapshot["arrival_quantity"])), 4
            ),
            "procurement_actual_lmt": round(
                _safe_float(self._weighted_average(latest_snapshot["procurement_actual_lmt"], latest_snapshot["arrival_quantity"])), 4
            ),
            "policy_repo_rate": round(
                _safe_float(self._weighted_average(latest_snapshot["policy_repo_rate"], latest_snapshot["arrival_quantity"])), 4
            ),
            "cpi_inflation_rate": round(
                _safe_float(self._weighted_average(latest_snapshot["cpi_inflation_rate"], latest_snapshot["arrival_quantity"])), 4
            ),
        }

        return {
            "recent_market": [
                {
                    "date": pd.Timestamp(row["date"]).date().isoformat(),
                    "modal_price": round(_safe_float(row["modal_price"]), 4),
                    "arrival_quantity": round(_safe_float(row["arrival_quantity"]), 4),
                    "market_count": int(_safe_float(row["market_count"])),
                    "state_count": int(_safe_float(row["state_count"])),
                    "variety_count": int(_safe_float(row["variety_count"])),
                }
                for _, row in market_daily.tail(60).iterrows()
            ],
            "recent_weather": [
                {
                    "date": pd.Timestamp(row["date"]).date().isoformat(),
                    "temperature_2m_mean": round(_safe_float(row["temperature_2m_mean"]), 4),
                    "precipitation_sum": round(_safe_float(row["precipitation_sum"]), 4),
                    "soil_moisture_0_to_7cm_mean": round(_safe_float(row["soil_moisture_0_to_7cm_mean"]), 4),
                    "relative_humidity_2m_mean": round(_safe_float(row["relative_humidity_2m_mean"]), 4),
                }
                for _, row in weather_daily.tail(60).iterrows()
            ],
            "indicator_history": indicator_payload,
            "snapshot": snapshot,
        }

    @staticmethod
    def _build_ml_anchored_simulation(
        current_price: float,
        target_day7_price: float,
        horizon_days: int,
        simulations: int,
    ) -> dict[str, Any]:
        monte_carlo_source = WheatMonteCarloForecaster(db_path=_resolve_history_db_path())
        daily_series = monte_carlo_source._load_daily_series(max(240, horizon_days + 30))
        returns = daily_series["log_return"].dropna()
        if returns.empty:
            raise ValueError("Not enough wheat history to estimate volatility for Monte Carlo.")

        sigma = float(max(returns.std(ddof=1), 1e-6))
        target_horizon = min(7, max(1, horizon_days))
        safe_current = max(float(current_price), 1e-6)
        safe_target = max(float(target_day7_price), 1e-6)
        drift = math.log(safe_target / safe_current) / target_horizon

        rng = np.random.default_rng(42)
        shocks = rng.normal(loc=drift, scale=sigma, size=(simulations, horizon_days))
        cumulative = np.cumsum(shocks, axis=1)
        paths = safe_current * np.exp(cumulative)

        p10 = np.percentile(paths, 10, axis=0)
        p50 = np.percentile(paths, 50, axis=0)
        p90 = np.percentile(paths, 90, axis=0)
        mean_path = np.mean(paths, axis=0)
        last_date = pd.Timestamp(daily_series.iloc[-1]["date"]).date()
        forecast_dates = [last_date + timedelta(days=offset) for offset in range(1, horizon_days + 1)]

        return {
            "drift": drift,
            "volatility": sigma,
            "daily_forecast": [
                {
                    "date": forecast_dates[idx].isoformat(),
                    "mean_price": round(float(mean_path[idx]), 4),
                    "p10_price": round(float(p10[idx]), 4),
                    "p50_price": round(float(p50[idx]), 4),
                    "p90_price": round(float(p90[idx]), 4),
                }
                for idx in range(horizon_days)
            ],
        }

    def forecast(self, horizon_days: int = 42, simulations: int = 2000) -> dict[str, Any]:
        model, metadata = self._load_bundle()
        frame = self._load_training_frame()
        latest_date = frame["date"].max()
        latest = frame[frame["date"] == latest_date].copy().sort_values("state")
        design = self._prepare_features(latest, metadata["feature_columns"])
        predictions = model.predict(design)
        latest["predicted_next_7d_avg_price"] = predictions

        national_current_price = self._weighted_average(latest["modal_price"], latest["arrival_quantity"])
        national_predicted_price = self._weighted_average(
            latest["predicted_next_7d_avg_price"],
            latest["arrival_quantity"],
        )
        driver_overlay = self._load_driver_overlay(pd.Timestamp(latest_date))
        model_has_driver_features = bool(WHEAT_DRIVER_FEATURE_COLUMNS.intersection(set(metadata.get("feature_columns", []))))
        raw_driver_adjustment_pct = _safe_float(driver_overlay.get("implied_price_adjustment_pct"), 0.0)
        driver_adjustment_pct = 0.0 if model_has_driver_features else raw_driver_adjustment_pct
        driver_multiplier = 1.0 + (driver_adjustment_pct / 100.0)
        adjusted_predicted_price = national_predicted_price * driver_multiplier
        latest["driver_adjusted_next_7d_avg_price"] = latest["predicted_next_7d_avg_price"] * driver_multiplier

        implied_change = (
            ((national_predicted_price - national_current_price) / national_current_price) * 100
            if national_current_price
            else 0.0
        )
        adjusted_implied_change = (
            ((adjusted_predicted_price - national_current_price) / national_current_price) * 100
            if national_current_price
            else 0.0
        )

        monte_carlo = self._build_ml_anchored_simulation(
            current_price=national_current_price,
            target_day7_price=adjusted_predicted_price,
            horizon_days=horizon_days,
            simulations=simulations,
        )
        daily_forecast = monte_carlo["daily_forecast"]
        weekly_days = [7, 14, 21, 28, 35, 42]
        weekly_points = [point for idx, point in enumerate(daily_forecast, start=1) if idx in weekly_days]

        projections = []
        for index, point in enumerate(weekly_points, start=1):
            projections.append(
                {
                    "week": f"WK {index}",
                    "date": point["date"],
                    "price": round(float(point["p50_price"]), 4),
                    "lower": round(float(point["p10_price"]), 4),
                    "upper": round(float(point["p90_price"]), 4),
                }
            )

        top_states = latest.sort_values("arrival_quantity", ascending=False).head(5)[
            ["state", "modal_price", "predicted_next_7d_avg_price", "driver_adjusted_next_7d_avg_price", "arrival_quantity"]
        ]
        top_states_payload = [
            {
                "state": row["state"],
                "current_price": round(float(row["modal_price"]), 4),
                "baseline_next_7d_avg_price": round(float(row["predicted_next_7d_avg_price"]), 4),
                "predicted_next_7d_avg_price": round(float(row["driver_adjusted_next_7d_avg_price"]), 4),
                "arrival_quantity": round(float(row["arrival_quantity"]), 4),
            }
            for _, row in top_states.iterrows()
        ]

        mape = float(metadata["metrics"]["mape"])
        confidence = max(58, min(93, round(96 - min(mape, 30))))
        reasons = [
            f"Feature model trained on {metadata['train_rows']} Wheat state-day rows with {len(metadata['feature_columns'])} engineered features.",
            f"Validation error is MAPE {metadata['metrics']['mape']}% and RMSE {metadata['metrics']['rmse']}.",
            f"Baseline ML implied 7-day move is {implied_change:+.2f}% from the current weighted mandi price.",
            (
                f"Wheat driver scores are embedded directly in the trained feature set; latest driver signal is {raw_driver_adjustment_pct:+.2f}% and is already reflected in the baseline ML forecast."
                if model_has_driver_features
                else f"Wheat driver overlay contributes {driver_adjustment_pct:+.2f}% based on domestic, weather, global, and policy driver scores."
            ),
            (
                "Forward path and uncertainty are generated by a Monte Carlo simulation whose drift is calibrated to the ML forecast that already contains driver features."
                if model_has_driver_features
                else "Forward path and uncertainty are generated by a Monte Carlo simulation whose drift is calibrated to the driver-adjusted 7-day forecast."
            ),
        ]
        dashboard_signals = self._build_dashboard_signals(frame, latest)

        payload = {
            "status": "success",
            "commodity": "Wheat",
            "model": "HistGradientBoosting + MonteCarlo",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "training": metadata,
            "latest_context": {
                "latest_date": pd.Timestamp(latest["date"].max()).date().isoformat(),
                "current_weighted_price": round(float(national_current_price), 4),
                "baseline_next_7d_avg_price": round(float(national_predicted_price), 4),
                "predicted_next_7d_avg_price": round(float(adjusted_predicted_price), 4),
                "predicted_change_pct": round(float(adjusted_implied_change), 4),
                "baseline_predicted_change_pct": round(float(implied_change), 4),
                "driver_adjustment_pct": round(float(driver_adjustment_pct), 4),
                "driver_signal_pct": round(float(raw_driver_adjustment_pct), 4),
                "driver_features_embedded_in_model": model_has_driver_features,
                "state_count": int(len(latest)),
            },
            "confidence": confidence,
            "intelligence_reasons": reasons,
            "projections": projections,
            "state_predictions": top_states_payload,
            "uncertainty": {
                "drift": round(float(monte_carlo["drift"]), 6),
                "volatility": round(float(monte_carlo["volatility"]), 6),
                "day_42_p10": projections[-1]["lower"] if projections else None,
                "day_42_p50": projections[-1]["price"] if projections else None,
                "day_42_p90": projections[-1]["upper"] if projections else None,
            },
            "driver_overlay": driver_overlay,
            "daily_forecast": daily_forecast,
            "dashboard_signals": dashboard_signals,
        }
        return _sanitize_for_json(payload)
