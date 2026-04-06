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
OUTPUT_DB = OUTPUT_DIR / "wheat_scenarios.db"
SUPPLY_DB = ROOT / "SnD" / "supply" / "wheat" / "wheat_supply_factors.db"
DRIVER_DB = ROOT / "SnD" / "price_drivers" / "wheat" / "wheat_price_drivers.db"
BACKEND_ROOT = ROOT / "backend"
UPDATED_AT = datetime.now(UTC).isoformat().replace("+00:00", "Z")

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.wheat_ml_forecasting import WheatFeatureForecaster  # noqa: E402


SCENARIO_DEFINITIONS = [
    (
        "bull_tight_supply",
        "Bull (Tight Supply)",
        "bull",
        "Below-normal winter, lower acreage/yield, export strength, and tighter ending stocks.",
        "up",
        "Tight supply / higher price case for the trading team.",
    ),
    (
        "base_trend",
        "Base",
        "base",
        "Normal weather, stable policy, and trend-line demand.",
        "flat",
        "Most likely planning case using current balance-sheet and forecast information.",
    ),
    (
        "bear_surplus",
        "Bear (Surplus)",
        "bear",
        "Bumper crop, import pressure, and slower demand creating a looser balance sheet.",
        "down",
        "Surplus / softer price case for the trading team.",
    ),
]


SCENARIO_SHIFTS = {
    "bull_tight_supply": {
        "acreage_shift_pct": -4.0,
        "yield_shift_pct": -5.0,
        "imports_shift_pct": -10.0,
        "food_use_shift_pct": 1.0,
        "feed_use_shift_pct": 2.0,
        "industrial_use_shift_pct": 1.0,
        "exports_shift_pct": 20.0,
        "driver_bias_pct": 2.0,
        "range_risk_pct": 2.0,
    },
    "base_trend": {
        "acreage_shift_pct": 0.0,
        "yield_shift_pct": 0.0,
        "imports_shift_pct": 0.0,
        "food_use_shift_pct": 0.0,
        "feed_use_shift_pct": 0.0,
        "industrial_use_shift_pct": 0.0,
        "exports_shift_pct": 0.0,
        "driver_bias_pct": 0.0,
        "range_risk_pct": 0.0,
    },
    "bear_surplus": {
        "acreage_shift_pct": 3.0,
        "yield_shift_pct": 6.0,
        "imports_shift_pct": 25.0,
        "food_use_shift_pct": -1.0,
        "feed_use_shift_pct": -4.0,
        "industrial_use_shift_pct": -2.0,
        "exports_shift_pct": -25.0,
        "driver_bias_pct": -2.0,
        "range_risk_pct": 1.5,
    },
}


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS scenario_definitions (
            scenario_key TEXT PRIMARY KEY,
            scenario_name TEXT NOT NULL,
            scenario_type TEXT NOT NULL,
            description TEXT NOT NULL,
            price_direction TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS scenario_runs (
            run_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            target_marketing_year TEXT NOT NULL,
            anchor_month TEXT NOT NULL,
            base_anchor_price REAL NOT NULL,
            base_total_use_mmt REAL NOT NULL,
            base_ending_stock_mmt REAL NOT NULL,
            base_stocks_to_use_ratio_pct REAL NOT NULL,
            driver_context_json TEXT NOT NULL,
            method TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS scenario_assumptions (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            scenario_key TEXT NOT NULL,
            assumption_group TEXT NOT NULL,
            assumption_name TEXT NOT NULL,
            base_value REAL NOT NULL,
            scenario_value REAL NOT NULL,
            unit TEXT NOT NULL,
            shift_pct REAL NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scenario_price_ranges (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            scenario_key TEXT NOT NULL,
            target_marketing_year TEXT NOT NULL,
            anchor_month TEXT NOT NULL,
            anchor_price REAL NOT NULL,
            projected_price_low REAL NOT NULL,
            projected_price_mid REAL NOT NULL,
            projected_price_high REAL NOT NULL,
            implied_price_shift_pct REAL NOT NULL,
            implied_total_use_mmt REAL NOT NULL,
            implied_ending_stock_mmt REAL NOT NULL,
            implied_stocks_to_use_ratio_pct REAL NOT NULL,
            confidence TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def _load_base_balance() -> dict[str, Any]:
    with _connect(SUPPLY_DB) as conn:
        projection_row = conn.execute(
            """
            SELECT *
            FROM wheat_balance_sheet_projection
            ORDER BY marketing_year ASC
            LIMIT 1
            """
        ).fetchone()
    if projection_row is None:
        raise RuntimeError("No Wheat projection balance row found for scenario building.")
    return dict(projection_row)


def _load_driver_context(marketing_year: str) -> dict[str, Any]:
    with _connect(DRIVER_DB) as conn:
        annual_row = conn.execute(
            """
            SELECT *
            FROM driver_impact_score_annual
            WHERE marketing_year = ?
            """,
            (marketing_year,),
        ).fetchone()
        if annual_row is None:
            annual_row = conn.execute(
                """
                SELECT *
                FROM driver_impact_score_annual
                ORDER BY marketing_year DESC
                LIMIT 1
                """
            ).fetchone()
        latest_month = conn.execute(
            """
            SELECT *
            FROM driver_impact_score
            ORDER BY metric_month DESC
            LIMIT 1
            """
        ).fetchone()
    return {
        "annual": dict(annual_row) if annual_row is not None else {},
        "latest_month": dict(latest_month) if latest_month is not None else {},
    }


def _load_price_anchor() -> dict[str, Any]:
    forecast = WheatFeatureForecaster().forecast(horizon_days=42, simulations=200)
    daily = forecast["daily_forecast"][:30]
    if not daily:
        raise RuntimeError("No Wheat daily forecast available for scenario anchor price.")
    mid_prices = [float(item["p50_price"]) for item in daily]
    widths = [
        (float(item["p90_price"]) - float(item["p10_price"])) / max(float(item["p50_price"]), 1e-6) * 100.0
        for item in daily
    ]
    return {
        "anchor_month": daily[0]["date"][:7] + "-01",
        "anchor_price": sum(mid_prices) / len(mid_prices),
        "base_range_width_pct": sum(widths) / len(widths),
        "forecast_payload": forecast,
    }


def _scenario_note(scenario_type: str) -> str:
    if scenario_type == "bull":
        return "Tighter balance sheet and lower stocks-to-use imply a firmer wheat price range."
    if scenario_type == "bear":
        return "Looser balance sheet and larger carry imply a softer wheat price range."
    return "Base case follows the current projection with neutral balance-sheet assumptions."


def _build_run_payload() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    base_balance = _load_base_balance()
    driver_context = _load_driver_context(str(base_balance["marketing_year"]))
    price_anchor = _load_price_anchor()
    run_id = str(uuid.uuid4())
    return base_balance, driver_context, price_anchor, run_id


def _build_scenario_rows() -> tuple[list[tuple], list[tuple], tuple]:
    base_balance, driver_context, price_anchor, run_id = _build_run_payload()
    base_anchor_price = float(price_anchor["anchor_price"])
    base_width_pct = float(price_anchor["base_range_width_pct"])

    run_row = (
        run_id,
        UPDATED_AT,
        str(base_balance["marketing_year"]),
        str(price_anchor["anchor_month"]),
        round(base_anchor_price, 6),
        round(float(base_balance["total_use_mmt"]), 6),
        round(float(base_balance["ending_stock_mmt"]), 6),
        round(float(base_balance["stocks_to_use_ratio_pct"]), 6),
        json.dumps(driver_context),
        "balance_sheet_plus_driver_context_plus_30d_forecast_anchor",
        "Scenario engine uses the first Wheat projection year plus latest driver context and current 30-day forecast anchor.",
    )

    assumption_rows: list[tuple] = []
    price_rows: list[tuple] = []

    for scenario_key, scenario_name, scenario_type, _description, _direction, _notes in SCENARIO_DEFINITIONS:
        shifts = SCENARIO_SHIFTS[scenario_key]
        base_opening = float(base_balance["opening_stock_mmt"])
        base_acreage = float(base_balance["acreage_million_hectare"])
        base_yield = float(base_balance["yield_kg_per_hectare"])
        base_production = float(base_balance["production_mmt"])
        base_imports = float(base_balance["imports_mmt"])
        base_food = float(base_balance["food_use_mmt"])
        base_feed = float(base_balance["feed_use_mmt"])
        base_industrial = float(base_balance["industrial_use_mmt"])
        base_exports = float(base_balance["exports_mmt"])

        scenario_acreage = base_acreage * (1 + shifts["acreage_shift_pct"] / 100.0)
        scenario_yield = base_yield * (1 + shifts["yield_shift_pct"] / 100.0)
        production_multiplier = (scenario_acreage / max(base_acreage, 1e-6)) * (scenario_yield / max(base_yield, 1e-6))
        scenario_production = base_production * production_multiplier
        scenario_imports = base_imports * (1 + shifts["imports_shift_pct"] / 100.0)
        scenario_food = base_food * (1 + shifts["food_use_shift_pct"] / 100.0)
        scenario_feed = base_feed * (1 + shifts["feed_use_shift_pct"] / 100.0)
        scenario_industrial = base_industrial * (1 + shifts["industrial_use_shift_pct"] / 100.0)
        scenario_exports = base_exports * (1 + shifts["exports_shift_pct"] / 100.0)
        scenario_total_use = scenario_food + scenario_feed + scenario_industrial + scenario_exports
        scenario_ending_stock = base_opening + scenario_production + scenario_imports - scenario_total_use
        scenario_stu = (scenario_ending_stock / max(scenario_total_use, 1e-6)) * 100.0

        assumptions = [
            ("supply", "Opening stock", base_opening, base_opening, "MMT", 0.0, "Opening stock is inherited from the projected base row."),
            ("supply", "Acreage", base_acreage, scenario_acreage, "million_hectare", shifts["acreage_shift_pct"], "Scenario acreage shift applied to the projected Wheat area."),
            ("supply", "Yield", base_yield, scenario_yield, "kg_per_hectare", shifts["yield_shift_pct"], "Scenario yield shift applied to the projected Wheat yield."),
            ("supply", "Production", base_production, scenario_production, "MMT", ((scenario_production / max(base_production, 1e-6)) - 1.0) * 100.0, "Production responds to acreage and yield changes."),
            ("supply", "Imports", base_imports, scenario_imports, "MMT", shifts["imports_shift_pct"], "Import response under the scenario."),
            ("demand", "Food use", base_food, scenario_food, "MMT", shifts["food_use_shift_pct"], "Food demand shift under the scenario."),
            ("demand", "Feed use", base_feed, scenario_feed, "MMT", shifts["feed_use_shift_pct"], "Feed demand shift under the scenario."),
            ("demand", "Industrial use", base_industrial, scenario_industrial, "MMT", shifts["industrial_use_shift_pct"], "Industrial demand shift under the scenario."),
            ("demand", "Exports", base_exports, scenario_exports, "MMT", shifts["exports_shift_pct"], "Export-demand shift under the scenario."),
            ("balance", "Total use", float(base_balance["total_use_mmt"]), scenario_total_use, "MMT", ((scenario_total_use / max(float(base_balance["total_use_mmt"]), 1e-6)) - 1.0) * 100.0, "Total use implied by scenario demand assumptions."),
            ("balance", "Ending stock", float(base_balance["ending_stock_mmt"]), scenario_ending_stock, "MMT", ((scenario_ending_stock / max(float(base_balance["ending_stock_mmt"]), 1e-6)) - 1.0) * 100.0, "Ending stock implied by scenario."),
            ("balance", "Stocks-to-use", float(base_balance["stocks_to_use_ratio_pct"]), scenario_stu, "percent", ((scenario_stu / max(float(base_balance["stocks_to_use_ratio_pct"]), 1e-6)) - 1.0) * 100.0, "Stocks-to-use ratio implied by scenario."),
        ]

        for group, name, base_value, scenario_value, unit, shift_pct, notes in assumptions:
            assumption_rows.append(
                (
                    str(uuid.uuid4()),
                    run_id,
                    scenario_key,
                    group,
                    name,
                    round(base_value, 6),
                    round(scenario_value, 6),
                    unit,
                    round(float(shift_pct), 6),
                    notes,
                    UPDATED_AT,
                )
            )

        base_stu = float(base_balance["stocks_to_use_ratio_pct"])
        base_ending = float(base_balance["ending_stock_mmt"])
        tightness_pct = ((base_stu - scenario_stu) / max(base_stu, 1e-6)) * 100.0
        stock_change_pct = ((base_ending - scenario_ending_stock) / max(base_ending, 1e-6)) * 100.0
        use_change_pct = ((scenario_total_use - float(base_balance["total_use_mmt"])) / max(float(base_balance["total_use_mmt"]), 1e-6)) * 100.0
        price_shift_pct = max(
            -18.0,
            min(
                18.0,
                tightness_pct * 0.55 + stock_change_pct * 0.20 + use_change_pct * 0.25 + shifts["driver_bias_pct"],
            ),
        )
        scenario_mid = base_anchor_price * (1 + price_shift_pct / 100.0)
        half_range_pct = max(3.0, (base_width_pct * 0.45) + abs(price_shift_pct) * 0.25 + shifts["range_risk_pct"])
        scenario_low = scenario_mid * (1 - half_range_pct / 100.0)
        scenario_high = scenario_mid * (1 + half_range_pct / 100.0)

        price_rows.append(
            (
                str(uuid.uuid4()),
                run_id,
                scenario_key,
                str(base_balance["marketing_year"]),
                str(price_anchor["anchor_month"]),
                round(base_anchor_price, 6),
                round(scenario_low, 6),
                round(scenario_mid, 6),
                round(scenario_high, 6),
                round(price_shift_pct, 6),
                round(scenario_total_use, 6),
                round(scenario_ending_stock, 6),
                round(scenario_stu, 6),
                "medium",
                _scenario_note(scenario_type),
                UPDATED_AT,
            )
        )

    return assumption_rows, price_rows, run_row


def build_db() -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    assumption_rows, price_rows, run_row = _build_scenario_rows()
    with _connect(OUTPUT_DB) as conn:
        _ensure_schema(conn)
        conn.executemany(
            """
            INSERT INTO scenario_definitions
            (scenario_key, scenario_name, scenario_type, description, price_direction, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(scenario_key) DO UPDATE SET
                scenario_name=excluded.scenario_name,
                scenario_type=excluded.scenario_type,
                description=excluded.description,
                price_direction=excluded.price_direction,
                notes=excluded.notes
            """,
            SCENARIO_DEFINITIONS,
        )
        conn.execute("DELETE FROM scenario_runs")
        conn.execute("DELETE FROM scenario_assumptions")
        conn.execute("DELETE FROM scenario_price_ranges")
        conn.execute(
            """
            INSERT INTO scenario_runs
            (run_id, created_at, target_marketing_year, anchor_month, base_anchor_price, base_total_use_mmt, base_ending_stock_mmt, base_stocks_to_use_ratio_pct, driver_context_json, method, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            run_row,
        )
        conn.executemany(
            """
            INSERT INTO scenario_assumptions
            (id, run_id, scenario_key, assumption_group, assumption_name, base_value, scenario_value, unit, shift_pct, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            assumption_rows,
        )
        conn.executemany(
            """
            INSERT INTO scenario_price_ranges
            (id, run_id, scenario_key, target_marketing_year, anchor_month, anchor_price, projected_price_low, projected_price_mid, projected_price_high, implied_price_shift_pct, implied_total_use_mmt, implied_ending_stock_mmt, implied_stocks_to_use_ratio_pct, confidence, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            price_rows,
        )
        conn.commit()
        counts = {
            "scenario_definitions": conn.execute("SELECT COUNT(*) FROM scenario_definitions").fetchone()[0],
            "scenario_runs": conn.execute("SELECT COUNT(*) FROM scenario_runs").fetchone()[0],
            "scenario_assumptions": conn.execute("SELECT COUNT(*) FROM scenario_assumptions").fetchone()[0],
            "scenario_price_ranges": conn.execute("SELECT COUNT(*) FROM scenario_price_ranges").fetchone()[0],
        }
        latest_prices = [
            dict(row)
            for row in conn.execute(
                """
                SELECT scenario_key, target_marketing_year, anchor_month, projected_price_low, projected_price_mid, projected_price_high, implied_price_shift_pct
                FROM scenario_price_ranges
                ORDER BY scenario_key
                """
            ).fetchall()
        ]
    return {
        "status": "success",
        "db_path": str(OUTPUT_DB),
        "counts": counts,
        "latest_price_ranges": latest_prices,
    }


if __name__ == "__main__":
    print(json.dumps(build_db(), indent=2))
