from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.services.maize_ml_forecasting import MaizeFeatureForecaster
from app.services.rice_ml_forecasting import RiceFeatureForecaster
from app.services.wheat_ml_forecasting import WheatFeatureForecaster

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
SUPPLY_DEMAND_DB = DATA_DIR / "supply_demand_analytics.db"
_ANALYTICS_CACHE_TTL = timedelta(minutes=10)
_ANALYTICS_CACHE: dict[str, Any] = {
    "generated_at": None,
    "forecasts": None,
    "state_risks": None,
    "state_rows": None,
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class AnalyticsDashboardService:
    CROP_CONFIG: dict[str, dict[str, Any]] = {
        "Wheat": {
            "db_path": DATA_DIR / "wheat_model_support.db",
            "prefix": "wheat",
            "forecaster_cls": WheatFeatureForecaster,
            "arrival_unit_label": "30D arrivals (qtl)",
            "weather_label": "Temperature mean (C)",
            "scenario_focus": "procurement",
            "risk_profile": {
                "price_weight": 0.95,
                "temperature_trigger": 30.0,
                "temperature_weight": 1.35,
                "rain_weight": 0.55,
                "humidity_trigger": 54.0,
                "humidity_weight": 0.18,
                "market_penalty_weight": 3.8,
                "arrival_buffer_divisor": 650.0,
                "arrival_buffer_cap": 14.0,
                "arrival_buffer_weight": 1.0,
                "base_weight": 0.62,
            },
            "lens_notes": {
                "Supply Health": "Anchored by procurement, stocks, and arrival buffer in rabi-heavy states.",
                "Demand Pressure": "Driven by official demand, offtake pull, and tighter mandi liquidity.",
                "Weather Sensitivity": "Tracks heat stress more than excess rain for wheat belt conditions.",
                "Trade Exposure": "Less export-led than rice, but still affected by policy and release timing.",
                "Policy Cushion": "MSP, public stocks, and procurement create a stronger floor.",
                "Volatility Risk": "Based on forecast band width and the latest projected price move.",
            },
        },
        "Rice": {
            "db_path": DATA_DIR / "rice_model_support.db",
            "prefix": "rice",
            "forecaster_cls": RiceFeatureForecaster,
            "arrival_unit_label": "30D arrivals (qtl)",
            "weather_label": "Temperature mean (C)",
            "scenario_focus": "exports",
            "risk_profile": {
                "price_weight": 1.15,
                "temperature_trigger": 31.0,
                "temperature_weight": 0.95,
                "rain_weight": 1.45,
                "humidity_trigger": 60.0,
                "humidity_weight": 0.28,
                "market_penalty_weight": 3.0,
                "arrival_buffer_divisor": 700.0,
                "arrival_buffer_cap": 10.0,
                "arrival_buffer_weight": 0.75,
                "base_weight": 0.55,
            },
            "lens_notes": {
                "Supply Health": "Influenced by production, buffer stocks, and procurement coverage.",
                "Demand Pressure": "Export demand and domestic consumption leave less room for slack.",
                "Weather Sensitivity": "Rainfall and humidity matter more because of monsoon-linked rice zones.",
                "Trade Exposure": "Basmati and non-basmati exports materially shift domestic availability.",
                "Policy Cushion": "MSP and procurement help, but export pull can overwhelm them.",
                "Volatility Risk": "Higher when export-sensitive prices widen the forecast band.",
            },
        },
        "Maize": {
            "db_path": DATA_DIR / "maize_model_support.db",
            "prefix": "maize",
            "forecaster_cls": MaizeFeatureForecaster,
            "arrival_unit_label": "30D arrivals (qtl)",
            "weather_label": "Temperature mean (C)",
            "scenario_focus": "feed",
            "risk_profile": {
                "price_weight": 1.05,
                "temperature_trigger": 32.0,
                "temperature_weight": 1.5,
                "rain_weight": 0.9,
                "humidity_trigger": 58.0,
                "humidity_weight": 0.22,
                "market_penalty_weight": 4.1,
                "arrival_buffer_divisor": 900.0,
                "arrival_buffer_cap": 8.5,
                "arrival_buffer_weight": 0.65,
                "base_weight": 0.68,
            },
            "lens_notes": {
                "Supply Health": "Depends on harvest flow and thinner visible stock support than wheat or rice.",
                "Demand Pressure": "Feed and industrial pull can tighten the balance faster than expected.",
                "Weather Sensitivity": "Heat and uneven rainfall both matter in maize-heavy states.",
                "Trade Exposure": "Export and feed substitution can change maize balance quickly.",
                "Policy Cushion": "MSP exists, but public stock support is relatively limited.",
                "Volatility Risk": "Volatility rises quickly when arrivals thin and feed demand stays firm.",
            },
        },
    }

    def __init__(self) -> None:
        self.supply_demand_rows = self._load_supply_demand_rows()

    def _cache_is_fresh(self) -> bool:
        generated_at = _ANALYTICS_CACHE.get("generated_at")
        if not isinstance(generated_at, datetime):
            return False
        return datetime.utcnow() - generated_at < _ANALYTICS_CACHE_TTL

    def _load_cached_bundle(self) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
        if self._cache_is_fresh():
            forecasts = _ANALYTICS_CACHE.get("forecasts")
            state_risks = _ANALYTICS_CACHE.get("state_risks")
            state_rows = _ANALYTICS_CACHE.get("state_rows")
            if isinstance(forecasts, dict) and isinstance(state_risks, dict) and isinstance(state_rows, dict):
                return forecasts, state_risks, state_rows

        all_state_risks: dict[str, list[dict[str, Any]]] = {}
        all_forecasts: dict[str, dict[str, Any]] = {}
        all_state_rows: dict[str, list[dict[str, Any]]] = {}

        for crop_name, config in self.CROP_CONFIG.items():
            state_rows = self._fetch_latest_state_rows(config["db_path"], config["prefix"])
            forecaster = config["forecaster_cls"]()
            forecast = forecaster.forecast(horizon_days=42, simulations=160)
            all_forecasts[crop_name] = forecast
            all_state_rows[crop_name] = state_rows
            all_state_risks[crop_name] = self._build_state_risks(
                crop_name,
                state_rows,
                self.supply_demand_rows.get(crop_name, {}),
                forecast,
            )

        _ANALYTICS_CACHE["generated_at"] = datetime.utcnow()
        _ANALYTICS_CACHE["forecasts"] = all_forecasts
        _ANALYTICS_CACHE["state_risks"] = all_state_risks
        _ANALYTICS_CACHE["state_rows"] = all_state_rows
        return all_forecasts, all_state_risks, all_state_rows

    def _load_supply_demand_rows(self) -> dict[str, dict[str, Any]]:
        if not SUPPLY_DEMAND_DB.exists():
            return {}
        with sqlite3.connect(str(SUPPLY_DEMAND_DB)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT s.*
                FROM supply_demand_signals s
                JOIN (
                    SELECT crop, frequency, MAX(signal_date) AS max_signal_date
                    FROM supply_demand_signals
                    GROUP BY crop, frequency
                ) latest
                  ON latest.crop = s.crop
                 AND latest.frequency = s.frequency
                 AND latest.max_signal_date = s.signal_date
                """
            ).fetchall()
        return {str(row["crop"]): dict(row) for row in rows}

    def _fetch_latest_state_rows(self, db_path: Path, prefix: str) -> list[dict[str, Any]]:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            latest_state_date = conn.execute(
                f"SELECT MAX(date) FROM {prefix}_state_daily"
            ).fetchone()[0]
            latest_weather_date = conn.execute(
                "SELECT MAX(date) FROM weather_daily"
            ).fetchone()[0]
            rows = conn.execute(
                f"""
                SELECT
                    s.state,
                    s.date,
                    s.modal_price,
                    s.normalized_price_per_kg,
                    s.arrival_quantity,
                    s.market_count,
                    s.variety_count,
                    s.record_count,
                    w.temperature_2m_mean,
                    w.precipitation_sum,
                    w.rain_sum,
                    w.wind_speed_10m_max,
                    w.relative_humidity_2m_mean
                FROM {prefix}_state_daily s
                LEFT JOIN weather_daily w
                  ON w.state = s.state
                 AND w.date = ?
                WHERE s.date = ?
                ORDER BY s.arrival_quantity DESC, s.market_count DESC, s.state ASC
                """,
                (latest_weather_date, latest_state_date),
            ).fetchall()
        return [dict(row) for row in rows]

    def _build_risk_frame(self, crop: str, forecast: dict[str, Any], supply_row: dict[str, Any]) -> list[dict[str, Any]]:
        base_risk = _clamp(
            (_safe_float(supply_row.get("demand_score")) * 0.55)
            + ((100.0 - _safe_float(supply_row.get("supply_score"))) * 0.45)
        )
        frames: list[dict[str, Any]] = []
        for index, projection in enumerate(forecast.get("projections", [])[:6], start=1):
            price = _safe_float(projection.get("price"))
            lower = _safe_float(projection.get("lower"))
            upper = _safe_float(projection.get("upper"))
            band_pct = ((upper - lower) / price * 100.0) if price else 0.0
            probability = _clamp(base_risk + (index * 2.4) + (band_pct * 0.25))
            severity = _clamp((band_pct * 1.15) + abs(_safe_float(forecast["latest_context"].get("predicted_change_pct"))) * 1.8)
            frames.append(
                {
                    "label": projection.get("date") or projection.get("week") or f"P{index}",
                    "week": projection.get("week"),
                    "probability": round(probability, 2),
                    "severity": round(severity, 2),
                    "base_price": round(price, 4),
                    "lower": round(lower, 4),
                    "upper": round(upper, 4),
                }
            )
        return frames

    def _build_risk_formula(self, forecast: dict[str, Any], supply_row: dict[str, Any]) -> dict[str, Any]:
        demand_score = _safe_float(supply_row.get("demand_score"))
        supply_score = _safe_float(supply_row.get("supply_score"))
        base_risk = _clamp((demand_score * 0.55) + ((100.0 - supply_score) * 0.45))
        latest_context = forecast.get("latest_context", {})
        predicted_change_pct = _safe_float(latest_context.get("predicted_change_pct"))
        first_projection = (forecast.get("projections") or [{}])[0]
        price = _safe_float(first_projection.get("price"))
        lower = _safe_float(first_projection.get("lower"))
        upper = _safe_float(first_projection.get("upper"))
        band_pct = ((upper - lower) / price * 100.0) if price else 0.0
        return {
            "base_risk": round(base_risk, 2),
            "supply_score": round(supply_score, 2),
            "demand_score": round(demand_score, 2),
            "band_pct": round(band_pct, 2),
            "predicted_change_pct": round(predicted_change_pct, 2),
            "probability_formula": "clamp(base_risk + week_index*2.4 + band_pct*0.25)",
            "severity_formula": "clamp(band_pct*1.15 + abs(predicted_change_pct)*1.8)",
            "base_risk_formula": "clamp(demand_score*0.55 + (100-supply_score)*0.45)",
            "week_reference": str(first_projection.get('date') or first_projection.get('week') or ''),
        }

    def _build_state_risks(
        self,
        crop: str,
        state_rows: list[dict[str, Any]],
        supply_row: dict[str, Any],
        forecast: dict[str, Any],
    ) -> list[dict[str, Any]]:
        current_price = _safe_float(forecast.get("latest_context", {}).get("current_weighted_price"))
        profile = self.CROP_CONFIG[crop]["risk_profile"]
        base_risk = _clamp(
            (_safe_float(supply_row.get("demand_score")) * 0.55)
            + ((100.0 - _safe_float(supply_row.get("supply_score"))) * 0.45)
        )
        state_risks: list[dict[str, Any]] = []
        for row in state_rows:
            state_price = _safe_float(row.get("modal_price"))
            price_deviation_pct = abs(((state_price / current_price) - 1.0) * 100.0) if current_price else 0.0
            temperature = _safe_float(row.get("temperature_2m_mean"))
            rain = max(_safe_float(row.get("precipitation_sum")), _safe_float(row.get("rain_sum")))
            humidity = _safe_float(row.get("relative_humidity_2m_mean"))
            market_penalty = max(0.0, 4.0 - _safe_float(row.get("market_count")))
            arrival_buffer = min(
                profile["arrival_buffer_cap"],
                _safe_float(row.get("arrival_quantity")) / profile["arrival_buffer_divisor"],
            )
            risk_score = _clamp(
                (base_risk * profile["base_weight"])
                + (price_deviation_pct * profile["price_weight"])
                + max(0.0, temperature - profile["temperature_trigger"]) * profile["temperature_weight"]
                + min(14.0, rain * profile["rain_weight"])
                + max(0.0, humidity - profile["humidity_trigger"]) * profile["humidity_weight"]
                + (market_penalty * profile["market_penalty_weight"])
                - (arrival_buffer * profile["arrival_buffer_weight"])
            )
            state_risks.append(
                {
                    "state": row.get("state"),
                    "risk": round(risk_score, 2),
                    "modal_price": round(state_price, 4),
                    "arrival_quantity": round(_safe_float(row.get("arrival_quantity")), 4),
                    "market_count": int(_safe_float(row.get("market_count"))),
                    "temperature_2m_mean": round(temperature, 2),
                    "precipitation_sum": round(rain, 2),
                    "relative_humidity_2m_mean": round(humidity, 2),
                }
            )
        return state_risks

    def _build_heatmap(self, all_state_risks: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        selected_states: dict[str, dict[str, float]] = {}
        for crop, rows in all_state_risks.items():
            for row in rows[:8]:
                selected_states.setdefault(row["state"], {})
                selected_states[row["state"]][crop] = _safe_float(row["risk"])

        ranked_states = sorted(
            selected_states.items(),
            key=lambda item: sum(item[1].values()) / max(1, len(item[1])),
            reverse=True,
        )[:6]

        heatmap = []
        for state, crop_values in ranked_states:
            heatmap.append(
                {
                    "state": state,
                    "Wheat": round(crop_values.get("Wheat", 0.0), 2),
                    "Rice": round(crop_values.get("Rice", 0.0), 2),
                    "Maize": round(crop_values.get("Maize", 0.0), 2),
                }
            )
        return heatmap

    def _build_scenarios(
        self,
        crop: str,
        supply_row: dict[str, Any],
        forecast: dict[str, Any],
    ) -> list[dict[str, Any]]:
        focus = self.CROP_CONFIG[crop]["scenario_focus"]
        current_gap = _safe_float(supply_row.get("estimated_gap_million_tonnes"))
        supply = _safe_float(supply_row.get("estimated_supply_million_tonnes"))
        demand = _safe_float(supply_row.get("estimated_demand_million_tonnes"))
        wk1 = (forecast.get("projections") or [{}])[0]
        wk1_price = _safe_float(wk1.get("price"))
        band_pct = ((_safe_float(wk1.get("upper")) - _safe_float(wk1.get("lower"))) / wk1_price * 100.0) if wk1_price else 0.0

        if focus == "procurement":
            middle_title = "Procurement accelerates"
            middle_impact = "Government offtake rises and spot-market liquidity tightens."
            middle_price_shift = band_pct * 0.38
            middle_gap_shift = -(max(0.8, supply * 0.012))
        elif focus == "exports":
            middle_title = "Export demand jumps"
            middle_impact = "Basmati and non-basmati export pull reduces domestic room."
            middle_price_shift = band_pct * 0.44
            middle_gap_shift = -(max(1.2, demand * 0.018))
        else:
            middle_title = "Feed demand surges"
            middle_impact = "Feed buyers absorb more crop and nearby mandi pressure rises."
            middle_price_shift = band_pct * 0.41
            middle_gap_shift = -(max(0.7, demand * 0.02))

        scenarios = [
            {
                "title": "Weather stress intensifies",
                "impact": "Heat and rainfall deviations compress usable supply faster than baseline.",
                "price_shift_pct": round(max(1.2, band_pct * 0.62), 2),
                "gap_shift_million_tonnes": round(-(max(1.0, supply * 0.025)), 2),
                "severity": "High",
            },
            {
                "title": middle_title,
                "impact": middle_impact,
                "price_shift_pct": round(max(0.8, middle_price_shift), 2),
                "gap_shift_million_tonnes": round(middle_gap_shift, 2),
                "severity": "Medium",
            },
            {
                "title": "Logistics ease and stocks release",
                "impact": "Availability improves and pressure on mandi spreads softens.",
                "price_shift_pct": round(-max(0.7, band_pct * 0.33), 2),
                "gap_shift_million_tonnes": round(max(0.5, abs(current_gap) * 0.08), 2),
                "severity": "Supportive",
            },
        ]
        return scenarios

    def _build_geography(self, state_risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for row in state_risks[:6]:
            rows.append(
                {
                    "state": row["state"],
                    "arrival_quantity": round(_safe_float(row["arrival_quantity"]), 2),
                    "temperature_2m_mean": round(_safe_float(row["temperature_2m_mean"]), 2),
                    "risk": round(_safe_float(row["risk"]), 2),
                }
            )
        return rows

    def _build_commodity_lens(
        self,
        crop: str,
        supply_row: dict[str, Any],
        forecast: dict[str, Any],
        state_risks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        notes = self.CROP_CONFIG[crop]["lens_notes"]
        current_change = abs(_safe_float(forecast.get("latest_context", {}).get("predicted_change_pct")))
        avg_state_risk = sum(_safe_float(row.get("risk")) for row in state_risks[:6]) / max(1, len(state_risks[:6]))
        trade_exposure = _clamp(_safe_float(supply_row.get("demand_score")) * 0.7 + current_change * 4.0)
        policy_cushion = _clamp(_safe_float(supply_row.get("supply_score")) * 0.75)
        volatility_risk = _clamp(avg_state_risk * 0.8 + current_change * 6.0)
        weather_sensitivity = _clamp(
            sum(max(0.0, _safe_float(row.get("temperature_2m_mean")) - 30.0) * 4.0 for row in state_risks[:6]) / max(1, len(state_risks[:6]))
            + sum(_safe_float(row.get("precipitation_sum")) * 1.8 for row in state_risks[:6]) / max(1, len(state_risks[:6]))
        )
        return [
            {
                "metric": "Supply Health",
                "value": round(_clamp(_safe_float(supply_row.get("supply_score"))), 2),
                "fullMark": 100,
                "explanation": notes["Supply Health"],
            },
            {
                "metric": "Demand Pressure",
                "value": round(_clamp(_safe_float(supply_row.get("demand_score"))), 2),
                "fullMark": 100,
                "explanation": notes["Demand Pressure"],
            },
            {
                "metric": "Weather Sensitivity",
                "value": round(weather_sensitivity, 2),
                "fullMark": 100,
                "explanation": notes["Weather Sensitivity"],
            },
            {
                "metric": "Trade Exposure",
                "value": round(trade_exposure, 2),
                "fullMark": 100,
                "explanation": notes["Trade Exposure"],
            },
            {
                "metric": "Policy Cushion",
                "value": round(policy_cushion, 2),
                "fullMark": 100,
                "explanation": notes["Policy Cushion"],
            },
            {
                "metric": "Volatility Risk",
                "value": round(volatility_risk, 2),
                "fullMark": 100,
                "explanation": notes["Volatility Risk"],
            },
        ]

    def _build_alerts(self, crop: str, supply_row: dict[str, Any], forecast: dict[str, Any], state_risks: list[dict[str, Any]]) -> list[str]:
        top_state = state_risks[0]["state"] if state_risks else "the top-risk state"
        predicted_change = _safe_float(forecast.get("latest_context", {}).get("predicted_change_pct"))
        gap = _safe_float(supply_row.get("estimated_gap_million_tonnes"))
        demand_method = str(supply_row.get("demand_method", "proxy"))
        return [
            f"{crop} projected 7-day move is {predicted_change:+.2f}% from the current weighted mandi price.",
            f"{crop} supply-demand gap currently stands at {gap:+.2f} MnT in the unified analytics store.",
            f"{top_state} is the current highest-risk state in the live state screen for {crop}.",
            f"Demand basis for {crop} is {demand_method.replace('_', ' ')}.",
        ]

    def _risk_band_label(self, value: float) -> str:
        if value >= 66:
            return "High"
        if value >= 38:
            return "Medium"
        return "Low"

    def _build_calendar_outlook(
        self,
        forecasts: dict[str, dict[str, Any]],
        all_state_risks: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        rows = []
        projection_count = min(6, *(len((forecast.get("projections") or [])) for forecast in forecasts.values()))
        for index in range(projection_count):
            wheat_proj = forecasts["Wheat"]["projections"][index]
            rice_proj = forecasts["Rice"]["projections"][index]
            maize_proj = forecasts["Maize"]["projections"][index]
            wheat_risk = self._risk_band_label(
                sum(_safe_float(row.get("risk")) for row in all_state_risks["Wheat"][:6]) / max(1, len(all_state_risks["Wheat"][:6]))
                + index * 1.5
            )
            rice_risk = self._risk_band_label(
                sum(_safe_float(row.get("risk")) for row in all_state_risks["Rice"][:6]) / max(1, len(all_state_risks["Rice"][:6]))
                + index * 2.0
            )
            maize_risk = self._risk_band_label(
                sum(_safe_float(row.get("risk")) for row in all_state_risks["Maize"][:6]) / max(1, len(all_state_risks["Maize"][:6]))
                + index * 1.7
            )
            production_risk = self._risk_band_label(
                max(
                    sum(_safe_float(row.get("risk")) for row in all_state_risks["Wheat"][:4]) / max(1, len(all_state_risks["Wheat"][:4])),
                    sum(_safe_float(row.get("risk")) for row in all_state_risks["Rice"][:4]) / max(1, len(all_state_risks["Rice"][:4])),
                    sum(_safe_float(row.get("risk")) for row in all_state_risks["Maize"][:4]) / max(1, len(all_state_risks["Maize"][:4])),
                )
            )
            demand_risk = self._risk_band_label(
                max(
                    abs(_safe_float(forecasts["Wheat"]["latest_context"].get("predicted_change_pct"))) * 9.0,
                    abs(_safe_float(forecasts["Rice"]["latest_context"].get("predicted_change_pct"))) * 9.0,
                    abs(_safe_float(forecasts["Maize"]["latest_context"].get("predicted_change_pct"))) * 9.0,
                )
                + index * 1.8
            )
            rows.append(
                {
                    "month": wheat_proj.get("date", "")[5:7] + "/" + wheat_proj.get("date", "")[8:10] if wheat_proj.get("date") else wheat_proj.get("week"),
                    "wheat": wheat_risk,
                    "rice": rice_risk,
                    "maize": maize_risk,
                    "productionRisk": production_risk,
                    "demandRisk": demand_risk,
                }
            )
        return rows

    def _build_cross_crop_comparison(
        self,
        forecasts: dict[str, dict[str, Any]],
        supply_rows: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rows = []
        projection_count = min(6, *(len((forecast.get("projections") or [])) for forecast in forecasts.values()))
        base_supply = (
            _safe_float(supply_rows["Wheat"].get("estimated_supply_million_tonnes"))
            + _safe_float(supply_rows["Rice"].get("estimated_supply_million_tonnes"))
            + _safe_float(supply_rows["Maize"].get("estimated_supply_million_tonnes"))
        ) / 3.0
        base_demand = (
            _safe_float(supply_rows["Wheat"].get("estimated_demand_million_tonnes"))
            + _safe_float(supply_rows["Rice"].get("estimated_demand_million_tonnes"))
            + _safe_float(supply_rows["Maize"].get("estimated_demand_million_tonnes"))
        ) / 3.0
        current_prices = {
            crop: _safe_float(forecasts[crop]["latest_context"].get("current_weighted_price"), 1.0)
            for crop in forecasts
        }
        for index in range(projection_count):
            wheat_proj = forecasts["Wheat"]["projections"][index]
            rice_proj = forecasts["Rice"]["projections"][index]
            maize_proj = forecasts["Maize"]["projections"][index]
            projected_prices = {
                "Wheat": _safe_float(wheat_proj.get("price")),
                "Rice": _safe_float(rice_proj.get("price")),
                "Maize": _safe_float(maize_proj.get("price")),
            }
            avg_price_change_pct = sum(
                ((projected_prices[crop] / current_prices[crop]) - 1.0) * 100.0 if current_prices[crop] else 0.0
                for crop in projected_prices
            ) / 3.0
            supply_series_value = max(
                0.0,
                base_supply
                * (1.0 - (index * 0.0075))
                * (1.0 + min(0.03, max(-0.02, (-avg_price_change_pct * 0.0015)))),
            )
            demand_series_value = max(
                0.0,
                base_demand
                * (1.0 + (index * 0.0065))
                * (1.0 + min(0.035, max(-0.015, (-avg_price_change_pct * 0.0012)))),
            )
            rows.append(
                {
                    "month": wheat_proj.get("date", "")[5:7] + "/" + wheat_proj.get("date", "")[8:10] if wheat_proj.get("date") else wheat_proj.get("week"),
                    "wheat": round(_safe_float(wheat_proj.get("price")), 2),
                    "rice": round(_safe_float(rice_proj.get("price")), 2),
                    "maize": round(_safe_float(maize_proj.get("price")), 2),
                    "supply": round(supply_series_value, 2),
                    "demand": round(demand_series_value, 2),
                }
            )
        return rows

    def build(self, crop: str) -> dict[str, Any]:
        crop = crop.title()
        if crop not in self.CROP_CONFIG:
            raise ValueError(f"Unsupported crop: {crop}")

        all_forecasts, all_state_risks, all_state_rows = self._load_cached_bundle()

        selected_config = self.CROP_CONFIG[crop]
        selected_state_rows = all_state_rows.get(crop) or self._fetch_latest_state_rows(selected_config["db_path"], selected_config["prefix"])
        selected_forecast = all_forecasts[crop]
        selected_supply = self.supply_demand_rows.get(crop, {})

        return {
            "status": "success",
            "commodity": crop,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "commodity_lens": self._build_commodity_lens(crop, selected_supply, selected_forecast, all_state_risks[crop]),
            "risk_frame": self._build_risk_frame(crop, selected_forecast, selected_supply),
            "risk_formula": self._build_risk_formula(selected_forecast, selected_supply),
            "risk_heatmap": self._build_heatmap(all_state_risks),
            "scenarios": self._build_scenarios(crop, selected_supply, selected_forecast),
            "geography": self._build_geography(all_state_risks[crop]),
            "alerts": self._build_alerts(crop, selected_supply, selected_forecast, all_state_risks[crop]),
            "calendar_outlook": self._build_calendar_outlook(all_forecasts, all_state_risks),
            "cross_crop_comparison": self._build_cross_crop_comparison(all_forecasts, self.supply_demand_rows),
            "risk_legend": [
                {"label": "Price deviation", "detail": "How far a state is from the national weighted mandi price."},
                {"label": "Weather stress", "detail": "Heat, rain, and humidity weights tuned by crop."},
                {"label": "Market depth", "detail": "Fewer active markets increase local fragility."},
                {"label": "Arrival buffer", "detail": "Higher arrivals reduce near-term state risk."},
                {"label": "Supply-demand base", "detail": "Unified crop-level supply and demand scores anchor all risk rows."},
            ],
            "latest_context": selected_forecast.get("latest_context", {}),
            "supply_demand": selected_supply,
            "source_summary": {
                "supply_demand": json.loads(selected_supply["source_summary"]) if selected_supply.get("source_summary") else {},
                "state_snapshot_date": selected_state_rows[0]["date"] if selected_state_rows else None,
                "forecast_model": selected_forecast.get("model"),
            },
        }
