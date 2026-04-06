from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / "wheat_output_structure.db"
SUPPLY_DB = ROOT / "SnD" / "supply" / "wheat" / "wheat_supply_factors.db"
SCENARIO_DB = ROOT / "SnD" / "scenarios" / "wheat" / "wheat_scenarios.db"
DRIVER_DB = ROOT / "SnD" / "price_drivers" / "wheat" / "wheat_price_drivers.db"
SUPPORT_DB = ROOT / "backend" / "data" / "wheat_model_support.db"
HISTORY_DB = ROOT / "agmarknet_history_local.db"
UPDATED_AT = datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS output_blocks (
            block_key TEXT PRIMARY KEY,
            block_name TEXT NOT NULL,
            description TEXT NOT NULL,
            primary_source_layer TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS balance_sheet_output (
            id TEXT PRIMARY KEY,
            marketing_year TEXT NOT NULL,
            row_type TEXT NOT NULL,
            opening_stock_mmt REAL,
            production_mmt REAL,
            imports_mmt REAL,
            food_use_mmt REAL,
            feed_use_mmt REAL,
            industrial_use_mmt REAL,
            exports_mmt REAL,
            total_use_mmt REAL,
            ending_stock_mmt REAL,
            stocks_to_use_ratio_pct REAL,
            source_name TEXT,
            source_url TEXT,
            method TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stocks_to_use_ratio_chart (
            id TEXT PRIMARY KEY,
            marketing_year TEXT NOT NULL,
            row_type TEXT NOT NULL,
            stocks_to_use_ratio_pct REAL NOT NULL,
            ending_stock_mmt REAL,
            total_use_mmt REAL,
            source_name TEXT,
            source_url TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS price_correlation_series (
            metric_month TEXT PRIMARY KEY,
            domestic_spot_price REAL NOT NULL,
            global_benchmark_price REAL,
            domestic_price_index REAL,
            global_price_index REAL,
            rolling_6m_correlation REAL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS risk_flags (
            id TEXT PRIMARY KEY,
            flag_month TEXT NOT NULL,
            flag_type TEXT NOT NULL,
            flag_key TEXT NOT NULL,
            severity TEXT NOT NULL,
            score REAL NOT NULL,
            headline TEXT NOT NULL,
            detail TEXT NOT NULL,
            source_layer TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scenario_summary (
            id TEXT PRIMARY KEY,
            target_marketing_year TEXT NOT NULL,
            anchor_month TEXT NOT NULL,
            scenario_key TEXT NOT NULL,
            scenario_name TEXT NOT NULL,
            price_low REAL NOT NULL,
            price_mid REAL NOT NULL,
            price_high REAL NOT NULL,
            implied_price_shift_pct REAL NOT NULL,
            implied_ending_stock_mmt REAL NOT NULL,
            implied_stocks_to_use_ratio_pct REAL NOT NULL,
            confidence TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def _load_balance_rows() -> list[tuple]:
    rows: list[tuple] = []
    with _connect(SUPPLY_DB) as conn:
        annual_rows = conn.execute("SELECT * FROM wheat_balance_sheet_annual ORDER BY marketing_year").fetchall()
        projection_rows = conn.execute("SELECT * FROM wheat_balance_sheet_projection ORDER BY marketing_year").fetchall()
    for row in annual_rows:
        rows.append(
            (
                str(uuid.uuid4()),
                row["marketing_year"],
                row["row_type"],
                row["opening_stock_mmt"],
                row["production_mmt"],
                row["imports_mmt"],
                row["food_use_mmt"],
                row["feed_use_mmt"],
                row["industrial_use_mmt"],
                row["exports_mmt"],
                row["total_use_mmt"],
                row["ending_stock_mmt"],
                row["stocks_to_use_ratio_pct"],
                row["source_name"],
                row["source_url"],
                row["method"],
                row["notes"],
                UPDATED_AT,
            )
        )
    for row in projection_rows:
        rows.append(
            (
                str(uuid.uuid4()),
                row["marketing_year"],
                "projection",
                row["opening_stock_mmt"],
                row["production_mmt"],
                row["imports_mmt"],
                row["food_use_mmt"],
                row["feed_use_mmt"],
                row["industrial_use_mmt"],
                row["exports_mmt"],
                row["total_use_mmt"],
                row["ending_stock_mmt"],
                row["stocks_to_use_ratio_pct"],
                "Projected Wheat balance sheet",
                None,
                row["projection_method"],
                row["notes"],
                UPDATED_AT,
            )
        )
    return rows


def _load_stu_rows() -> list[tuple]:
    rows: list[tuple] = []
    with _connect(SUPPLY_DB) as conn:
        for row in conn.execute(
            """
            SELECT marketing_year, row_type, stocks_to_use_ratio_pct, ending_stock_mmt, total_use_mmt, source_name, source_url
            FROM wheat_balance_sheet_annual
            ORDER BY marketing_year
            """
        ):
            rows.append(
                (
                    str(uuid.uuid4()),
                    row["marketing_year"],
                    row["row_type"],
                    row["stocks_to_use_ratio_pct"],
                    row["ending_stock_mmt"],
                    row["total_use_mmt"],
                    row["source_name"],
                    row["source_url"],
                    UPDATED_AT,
                )
            )
        for row in conn.execute(
            """
            SELECT marketing_year, stocks_to_use_ratio_pct, ending_stock_mmt, total_use_mmt
            FROM wheat_balance_sheet_projection
            ORDER BY marketing_year
            """
        ):
            rows.append(
                (
                    str(uuid.uuid4()),
                    row["marketing_year"],
                    "projection",
                    row["stocks_to_use_ratio_pct"],
                    row["ending_stock_mmt"],
                    row["total_use_mmt"],
                    "Projected Wheat balance sheet",
                    None,
                    UPDATED_AT,
                )
            )
    return rows


def _load_price_correlation_rows() -> list[tuple]:
    with _connect(HISTORY_DB) as conn:
        domestic = pd.read_sql_query(
            """
            SELECT substr(date, 1, 7) || '-01' AS metric_month,
                   AVG(CAST(modal_price AS REAL)) AS domestic_spot_price
            FROM market_price_data
            WHERE commodity = 'Wheat'
            GROUP BY substr(date, 1, 7)
            ORDER BY metric_month
            """,
            conn,
        )
    with _connect(SUPPORT_DB) as conn:
        benchmark = pd.read_sql_query(
            """
            SELECT benchmark_month AS metric_month, benchmark_average AS global_benchmark_price
            FROM global_wheat_benchmark_monthly
            ORDER BY benchmark_month
            """,
            conn,
        )

    merged = domestic.merge(benchmark, on="metric_month", how="inner")
    if merged.empty:
        return []
    merged["domestic_spot_price"] = pd.to_numeric(merged["domestic_spot_price"], errors="coerce")
    merged["global_benchmark_price"] = pd.to_numeric(merged["global_benchmark_price"], errors="coerce")
    merged = merged.dropna(subset=["domestic_spot_price", "global_benchmark_price"]).copy()
    merged["domestic_price_index"] = (merged["domestic_spot_price"] / merged["domestic_spot_price"].iloc[0]) * 100.0
    merged["global_price_index"] = (merged["global_benchmark_price"] / merged["global_benchmark_price"].iloc[0]) * 100.0
    merged["rolling_6m_correlation"] = (
        merged["domestic_spot_price"].rolling(6).corr(merged["global_benchmark_price"]).fillna(0.0)
    )

    return [
        (
            row.metric_month,
            round(float(row.domestic_spot_price), 6),
            round(float(row.global_benchmark_price), 6),
            round(float(row.domestic_price_index), 6),
            round(float(row.global_price_index), 6),
            round(float(row.rolling_6m_correlation), 6),
            "AGMARKNET + World Bank Pink Sheet",
            "https://agmarknet.gov.in/datewisespeccommdodityinput | https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx",
            UPDATED_AT,
        )
        for row in merged.itertuples(index=False)
    ]


def _severity_from_score(score: float) -> str:
    if score >= 85:
        return "high"
    if score >= 65:
        return "medium"
    return "low"


def _build_risk_flags() -> list[tuple]:
    rows: list[tuple] = []
    with _connect(DRIVER_DB) as conn:
        latest_driver = conn.execute(
            "SELECT * FROM driver_impact_score ORDER BY metric_month DESC LIMIT 1"
        ).fetchone()
    with _connect(SUPPLY_DB) as conn:
        latest_balance = conn.execute(
            "SELECT * FROM wheat_balance_sheet_projection ORDER BY marketing_year ASC LIMIT 1"
        ).fetchone()
    if latest_driver is None or latest_balance is None:
        return rows

    flag_month = latest_driver["metric_month"]
    driver_score = float(latest_driver["composite_score"])
    stu = float(latest_balance["stocks_to_use_ratio_pct"])
    ending_stock = float(latest_balance["ending_stock_mmt"])
    total_use = float(latest_balance["total_use_mmt"])
    bullish = json.loads(latest_driver["bullish_drivers_json"])
    bearish = json.loads(latest_driver["bearish_drivers_json"])

    rows.append(
        (
            str(uuid.uuid4()),
            flag_month,
            "weather_policy_trade",
            "driver_composite",
            _severity_from_score(driver_score),
            round(driver_score, 6),
            "Wheat driver pressure",
            f"Composite Wheat driver score is {driver_score:.2f}. Top bullish drivers: {', '.join(item['factor_name'] for item in bullish)}. Top bearish drivers: {', '.join(item['factor_name'] for item in bearish)}.",
            "wheat_price_drivers.db",
            UPDATED_AT,
        )
    )
    supply_stress_score = max(0.0, min(100.0, (20.0 - stu) * 5.0))
    rows.append(
        (
            str(uuid.uuid4()),
            flag_month,
            "supply",
            "stocks_to_use",
            _severity_from_score(supply_stress_score),
            round(supply_stress_score, 6),
            "Stocks-to-use risk",
            f"Projected STU is {stu:.2f}% with ending stock {ending_stock:.2f} MMT against total use {total_use:.2f} MMT.",
            "wheat_balance_sheet_projection",
            UPDATED_AT,
        )
    )
    trade_score = max(0.0, min(100.0, float(latest_driver["global_score"])))
    rows.append(
        (
            str(uuid.uuid4()),
            flag_month,
            "trade",
            "global_trade_pressure",
            _severity_from_score(trade_score),
            round(trade_score, 6),
            "Global trade pressure",
            f"Global driver bucket is {float(latest_driver['global_score']):.2f}, reflecting Black Sea and Russian export-policy context.",
            "wheat_price_drivers.db",
            UPDATED_AT,
        )
    )
    return rows


def _load_scenario_summary_rows() -> list[tuple]:
    with _connect(SCENARIO_DB) as conn:
        definitions = {
            row["scenario_key"]: row["scenario_name"]
            for row in conn.execute("SELECT scenario_key, scenario_name FROM scenario_definitions")
        }
        rows = conn.execute(
            """
            SELECT *
            FROM scenario_price_ranges
            ORDER BY scenario_key
            """
        ).fetchall()
    return [
        (
            str(uuid.uuid4()),
            row["target_marketing_year"],
            row["anchor_month"],
            row["scenario_key"],
            definitions.get(row["scenario_key"], row["scenario_key"]),
            row["projected_price_low"],
            row["projected_price_mid"],
            row["projected_price_high"],
            row["implied_price_shift_pct"],
            row["implied_ending_stock_mmt"],
            row["implied_stocks_to_use_ratio_pct"],
            row["confidence"],
            row["notes"],
            UPDATED_AT,
        )
        for row in rows
    ]


def build_db() -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_blocks = [
        ("balance_sheet_table", "Balance sheet table", "10-year historical + current + forecast annual Wheat S&D table.", "Step 4 balance-sheet tables", UPDATED_AT),
        ("stocks_to_use_ratio_chart", "Stocks-to-Use ratio chart", "Historical and projected stocks-to-use ratio series.", "Step 4 balance-sheet tables", UPDATED_AT),
        ("price_correlation", "Price correlation", "Domestic spot vs global wheat benchmark monthly relationship.", "AGMARKNET + global benchmark", UPDATED_AT),
        ("risk_flags", "Risk flags", "Latest weather, policy, trade, and supply-stress alert rows.", "Step 5 drivers + Step 6 data layer", UPDATED_AT),
        ("scenario_summary", "Scenario summary", "Bull / Base / Bear price ranges for the trading team.", "Step 7 scenario tables", UPDATED_AT),
    ]
    balance_rows = _load_balance_rows()
    stu_rows = _load_stu_rows()
    correlation_rows = _load_price_correlation_rows()
    risk_rows = _build_risk_flags()
    scenario_rows = _load_scenario_summary_rows()

    with _connect(OUTPUT_DB) as conn:
        _ensure_schema(conn)
        conn.executemany(
            """
            INSERT INTO output_blocks (block_key, block_name, description, primary_source_layer, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(block_key) DO UPDATE SET
                block_name=excluded.block_name,
                description=excluded.description,
                primary_source_layer=excluded.primary_source_layer,
                updated_at=excluded.updated_at
            """,
            output_blocks,
        )
        for table in [
            "balance_sheet_output",
            "stocks_to_use_ratio_chart",
            "price_correlation_series",
            "risk_flags",
            "scenario_summary",
        ]:
            conn.execute(f"DELETE FROM {table}")
        conn.executemany(
            """
            INSERT INTO balance_sheet_output
            (id, marketing_year, row_type, opening_stock_mmt, production_mmt, imports_mmt, food_use_mmt, feed_use_mmt, industrial_use_mmt, exports_mmt, total_use_mmt, ending_stock_mmt, stocks_to_use_ratio_pct, source_name, source_url, method, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            balance_rows,
        )
        conn.executemany(
            """
            INSERT INTO stocks_to_use_ratio_chart
            (id, marketing_year, row_type, stocks_to_use_ratio_pct, ending_stock_mmt, total_use_mmt, source_name, source_url, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            stu_rows,
        )
        conn.executemany(
            """
            INSERT INTO price_correlation_series
            (metric_month, domestic_spot_price, global_benchmark_price, domestic_price_index, global_price_index, rolling_6m_correlation, source_name, source_url, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            correlation_rows,
        )
        conn.executemany(
            """
            INSERT INTO risk_flags
            (id, flag_month, flag_type, flag_key, severity, score, headline, detail, source_layer, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            risk_rows,
        )
        conn.executemany(
            """
            INSERT INTO scenario_summary
            (id, target_marketing_year, anchor_month, scenario_key, scenario_name, price_low, price_mid, price_high, implied_price_shift_pct, implied_ending_stock_mmt, implied_stocks_to_use_ratio_pct, confidence, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            scenario_rows,
        )
        conn.commit()
        counts = {
            "output_blocks": conn.execute("SELECT COUNT(*) FROM output_blocks").fetchone()[0],
            "balance_sheet_output": conn.execute("SELECT COUNT(*) FROM balance_sheet_output").fetchone()[0],
            "stocks_to_use_ratio_chart": conn.execute("SELECT COUNT(*) FROM stocks_to_use_ratio_chart").fetchone()[0],
            "price_correlation_series": conn.execute("SELECT COUNT(*) FROM price_correlation_series").fetchone()[0],
            "risk_flags": conn.execute("SELECT COUNT(*) FROM risk_flags").fetchone()[0],
            "scenario_summary": conn.execute("SELECT COUNT(*) FROM scenario_summary").fetchone()[0],
        }
    return {
        "status": "success",
        "db_path": str(OUTPUT_DB),
        "counts": counts,
    }


if __name__ == "__main__":
    print(json.dumps(build_db(), indent=2))
