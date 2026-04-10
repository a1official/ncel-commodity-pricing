from __future__ import annotations

import math
import sqlite3
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import pstdev


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / "wheat_risk_register.db"
DEMAND_DB = ROOT / "SnD" / "demand" / "wheat" / "wheat_demand_monthly.db"
SUPPLY_DB = ROOT / "SnD" / "supply" / "wheat" / "wheat_supply_factors.db"
DRIVERS_DB = ROOT / "SnD" / "price_drivers" / "wheat" / "wheat_price_drivers.db"
UPDATED_AT = datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass
class MonthlyPoint:
    month: str
    marketing_year: str
    value: float


RISK_DEFINITIONS = [
    (
        "price_volatility",
        "Price volatility",
        "market",
        "Tracks unstable wheat price behavior and rising month-on-month shock risk.",
        "High volatility makes pricing harder for the trading team and often signals regime change.",
        "bullish_price_risk",
    ),
    (
        "weather_climate",
        "Weather / climate",
        "weather",
        "Combines winter temperature anomaly and frost stress in the North India wheat belt.",
        "Weather stress can damage yield and quality, tightening domestic supply.",
        "bullish_price_risk",
    ),
    (
        "geopolitical_black_sea",
        "Geopolitical / Black Sea",
        "geopolitical",
        "Captures Black Sea disruption and Russian export policy pressure.",
        "Global wheat trade shocks quickly transmit into domestic price expectations.",
        "bullish_price_risk",
    ),
    (
        "policy_trade_restriction",
        "Policy / trade restriction",
        "policy",
        "Captures India wheat policy intervention risk through export restrictions and state market controls.",
        "Domestic policy shocks can abruptly change local availability and price behavior.",
        "mixed_policy_risk",
    ),
    (
        "supply_stock_tightness",
        "Supply / stock tightness",
        "balance_sheet",
        "Measures stock cover and monthly balance tightness using opening stock, total availability, and delta.",
        "Low stock cover and negative balance pressure raise the probability of domestic supply stress.",
        "bullish_price_risk",
    ),
]

MODEL_REFERENCE = [
    (
        "price_volatility",
        "6-month rolling standard deviation of monthly returns on the wheat retail pressure index.",
        "SnD.demand.wheat.factor_monthly_values -> retail_price_cpi_wheat_pressure",
        "return_t = ln(price_index_t / price_index_t-1); volatility = stdev(last_6_returns) * 100",
        "medium",
    ),
    (
        "weather_climate",
        "Temperature anomaly plus frost-risk composite.",
        "SnD.price_drivers.wheat.factor_monthly_values -> north_india_winter_temperature, frost_risk",
        "weather_raw = 0.6 * positive_temp_anomaly_score + 0.4 * frost_risk_score",
        "medium",
    ),
    (
        "geopolitical_black_sea",
        "Weighted geopolitical disruption composite.",
        "SnD.price_drivers.wheat.factor_monthly_values -> black_sea_corridor, russian_export_policy",
        "geo_raw = 0.6 * black_sea_corridor + 0.4 * russian_export_policy",
        "high",
    ),
    (
        "policy_trade_restriction",
        "Weighted India policy intervention composite.",
        "SnD.price_drivers.wheat.factor_monthly_values -> india_export_policy, msp",
        "policy_raw = 0.8 * india_export_policy + 0.2 * msp_change_score",
        "medium",
    ),
    (
        "supply_stock_tightness",
        "Inverse stock-cover and delta stress composite.",
        "SnD.supply.wheat.factor_monthly_values -> opening_stock, total_demand_monthly, delta",
        "tightness_raw = 0.6 * inverse_delta_score + 0.4 * inverse_stock_cover_score",
        "high",
    ),
]


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS risk_definitions (
            risk_key TEXT PRIMARY KEY,
            risk_name TEXT NOT NULL,
            risk_category TEXT NOT NULL,
            description TEXT NOT NULL,
            why_it_matters TEXT NOT NULL,
            direction TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS risk_model_reference (
            risk_key TEXT PRIMARY KEY,
            model_approach TEXT NOT NULL,
            source_data TEXT NOT NULL,
            formula_logic TEXT NOT NULL,
            confidence TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS risk_monthly_metrics (
            id TEXT PRIMARY KEY,
            risk_key TEXT NOT NULL,
            metric_month TEXT NOT NULL,
            marketing_year TEXT NOT NULL,
            raw_value REAL NOT NULL,
            normalized_score REAL NOT NULL,
            severity TEXT NOT NULL,
            source_name TEXT NOT NULL,
            method TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS risk_register_history (
            id TEXT PRIMARY KEY,
            risk_key TEXT NOT NULL,
            metric_month TEXT NOT NULL,
            marketing_year TEXT NOT NULL,
            probability_score REAL NOT NULL,
            impact_score REAL NOT NULL,
            composite_risk_score REAL NOT NULL,
            severity TEXT NOT NULL,
            rank_in_month INTEGER NOT NULL,
            direction TEXT NOT NULL,
            source_summary TEXT NOT NULL,
            watch_items TEXT NOT NULL,
            mitigation_note TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS risk_register_current (
            risk_key TEXT PRIMARY KEY,
            as_of_month TEXT NOT NULL,
            marketing_year TEXT NOT NULL,
            probability_score REAL NOT NULL,
            impact_score REAL NOT NULL,
            composite_risk_score REAL NOT NULL,
            severity TEXT NOT NULL,
            rank_in_month INTEGER NOT NULL,
            direction TEXT NOT NULL,
            source_summary TEXT NOT NULL,
            watch_items TEXT NOT NULL,
            mitigation_note TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS risk_alerts (
            id TEXT PRIMARY KEY,
            risk_key TEXT NOT NULL,
            metric_month TEXT NOT NULL,
            marketing_year TEXT NOT NULL,
            alert_level TEXT NOT NULL,
            composite_risk_score REAL NOT NULL,
            message TEXT NOT NULL,
            trigger_rule TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def wipe_tables(conn: sqlite3.Connection) -> None:
    for table in (
        "risk_definitions",
        "risk_model_reference",
        "risk_monthly_metrics",
        "risk_register_history",
        "risk_register_current",
        "risk_alerts",
    ):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()


def load_factor_series(db_path: Path, factor_key: str) -> list[MonthlyPoint]:
    conn = connect(db_path)
    rows = conn.execute(
        """
        SELECT metric_month, marketing_year, value
        FROM factor_monthly_values
        WHERE factor_key = ?
        ORDER BY metric_month
        """,
        (factor_key,),
    ).fetchall()
    conn.close()
    return [MonthlyPoint(row["metric_month"], row["marketing_year"], float(row["value"])) for row in rows]


def series_map(series: list[MonthlyPoint]) -> dict[str, MonthlyPoint]:
    return {point.month: point for point in series}


def month_bucket(month_str: str) -> int:
    return int(month_str[5:7])


def compute_percent_rank(values: list[float], invert: bool = False) -> list[float]:
    indexed = list(enumerate(values))
    indexed.sort(key=lambda item: item[1], reverse=invert)
    if len(indexed) == 1:
        return [50.0]
    result = [0.0] * len(values)
    for rank, (idx, _value) in enumerate(indexed):
        result[idx] = round(rank / (len(indexed) - 1) * 100.0, 4)
    return result


def severity_from_score(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "moderate"
    return "low"


def impact_score(normalized_score: float, baseline: float) -> float:
    return round(0.5 * normalized_score + 0.5 * baseline, 4)


def build_price_volatility(price_index: list[MonthlyPoint]) -> list[dict]:
    raw_values = []
    months = []
    marketing_years = []
    returns: list[float] = []
    for idx, point in enumerate(price_index):
        if idx == 0:
            monthly_return = 0.0
        else:
            prev = price_index[idx - 1].value
            monthly_return = math.log(point.value / prev) if prev > 0 and point.value > 0 else 0.0
        returns.append(monthly_return)
        window = returns[max(0, idx - 5) : idx + 1]
        vol = pstdev(window) * 100 if len(window) > 1 else 0.0
        raw_values.append(round(vol, 6))
        months.append(point.month)
        marketing_years.append(point.marketing_year)
    norm_scores = compute_percent_rank(raw_values)
    rows = []
    for month, marketing_year, raw, norm in zip(months, marketing_years, raw_values, norm_scores):
        rows.append(
            {
                "risk_key": "price_volatility",
                "metric_month": month,
                "marketing_year": marketing_year,
                "raw_value": raw,
                "normalized_score": norm,
                "severity": severity_from_score(norm),
                "source_name": "Wheat retail pressure monthly index",
                "method": "rolling_6m_stddev_of_log_returns",
                "notes": "Built from the monthly wheat retail pressure index stored in the demand DB.",
            }
        )
    return rows


def build_weather_climate(temperature: list[MonthlyPoint], frost: list[MonthlyPoint]) -> list[dict]:
    temp_by_month = defaultdict(list)
    for point in temperature:
        temp_by_month[month_bucket(point.month)].append(point.value)
    temp_normals = {month: sum(vals) / len(vals) for month, vals in temp_by_month.items()}

    raw_values = []
    months = []
    marketing_years = []
    for temp_point, frost_point in zip(temperature, frost):
        anomaly = max(0.0, temp_point.value - temp_normals[month_bucket(temp_point.month)])
        raw = round(0.6 * anomaly * 10 + 0.4 * frost_point.value, 6)
        raw_values.append(raw)
        months.append(temp_point.month)
        marketing_years.append(temp_point.marketing_year)
    norm_scores = compute_percent_rank(raw_values)
    rows = []
    for month, marketing_year, raw, norm in zip(months, marketing_years, raw_values, norm_scores):
        rows.append(
            {
                "risk_key": "weather_climate",
                "metric_month": month,
                "marketing_year": marketing_year,
                "raw_value": raw,
                "normalized_score": norm,
                "severity": severity_from_score(norm),
                "source_name": "North India weather driver composite",
                "method": "temperature_anomaly_plus_frost_composite",
                "notes": "Positive winter temperature anomaly and frost risk are both treated as supply stress.",
            }
        )
    return rows


def build_geopolitical(black_sea: list[MonthlyPoint], russian_policy: list[MonthlyPoint]) -> list[dict]:
    rows = []
    for bs_point, ru_point in zip(black_sea, russian_policy):
        raw = round(0.6 * bs_point.value + 0.4 * ru_point.value, 6)
        rows.append(
            {
                "risk_key": "geopolitical_black_sea",
                "metric_month": bs_point.month,
                "marketing_year": bs_point.marketing_year,
                "raw_value": raw,
                "source_name": "Black Sea and Russian export policy drivers",
                "method": "weighted_event_risk_composite",
                "notes": "Higher geopolitical disruption is bullish risk for wheat prices.",
            }
        )
    raw_values = [row["raw_value"] for row in rows]
    norm_scores = compute_percent_rank(raw_values)
    for row, norm in zip(rows, norm_scores):
        row["normalized_score"] = norm
        row["severity"] = severity_from_score(norm)
    return rows


def build_policy_trade(india_policy: list[MonthlyPoint], msp: list[MonthlyPoint]) -> list[dict]:
    msp_changes = [0.0]
    for idx in range(1, len(msp)):
        prev = msp[idx - 1].value
        curr = msp[idx].value
        msp_changes.append(((curr - prev) / prev * 100) if prev else 0.0)
    msp_change_scores = compute_percent_rank([max(0.0, value) for value in msp_changes])
    rows = []
    for policy_point, msp_point, msp_score in zip(india_policy, msp, msp_change_scores):
        raw = round(0.8 * policy_point.value + 0.2 * msp_score, 6)
        rows.append(
            {
                "risk_key": "policy_trade_restriction",
                "metric_month": policy_point.month,
                "marketing_year": policy_point.marketing_year,
                "raw_value": raw,
                "source_name": "India wheat policy and MSP composite",
                "method": "india_policy_plus_msp_change_composite",
                "notes": "Captures policy intervention intensity, with MSP change used as a secondary policy signal.",
            }
        )
    raw_values = [row["raw_value"] for row in rows]
    norm_scores = compute_percent_rank(raw_values)
    for row, norm in zip(rows, norm_scores):
        row["normalized_score"] = norm
        row["severity"] = severity_from_score(norm)
    return rows


def build_supply_tightness(opening_stock: list[MonthlyPoint], total_demand: list[MonthlyPoint], delta: list[MonthlyPoint]) -> list[dict]:
    stock_cover_values = []
    delta_values = []
    for stock_point, demand_point, delta_point in zip(opening_stock, total_demand, delta):
        stock_cover_values.append(stock_point.value / demand_point.value if demand_point.value else 0.0)
        delta_values.append(delta_point.value)
    inverse_stock_cover_scores = compute_percent_rank(stock_cover_values, invert=True)
    inverse_delta_scores = compute_percent_rank(delta_values, invert=True)
    rows = []
    for stock_point, demand_point, delta_point, stock_score, delta_score in zip(
        opening_stock, total_demand, delta, inverse_stock_cover_scores, inverse_delta_scores
    ):
        raw = round(0.6 * delta_score + 0.4 * stock_score, 6)
        rows.append(
            {
                "risk_key": "supply_stock_tightness",
                "metric_month": stock_point.month,
                "marketing_year": stock_point.marketing_year,
                "raw_value": raw,
                "normalized_score": raw,
                "severity": severity_from_score(raw),
                "source_name": "Wheat balance tightness composite",
                "method": "inverse_delta_plus_inverse_stock_cover",
                "notes": "Higher risk means tighter balance and weaker stock cover.",
            }
        )
    return rows


def history_rows(monthly_metrics: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    impact_baselines = {
        "price_volatility": 90.0,
        "weather_climate": 85.0,
        "geopolitical_black_sea": 82.0,
        "policy_trade_restriction": 76.0,
        "supply_stock_tightness": 88.0,
    }
    source_summaries = {
        "price_volatility": "Demand-side wheat retail pressure index",
        "weather_climate": "North India weather drivers",
        "geopolitical_black_sea": "Black Sea and Russian export policy drivers",
        "policy_trade_restriction": "India wheat policy and MSP signals",
        "supply_stock_tightness": "Supply-side opening stock, total demand, and delta",
    }
    watch_items = {
        "price_volatility": "Watch rolling return volatility and regime shift in spot pricing.",
        "weather_climate": "Watch winter temperature anomaly and frost stress in the wheat belt.",
        "geopolitical_black_sea": "Watch corridor disruption, sanctions, and export restriction headlines.",
        "policy_trade_restriction": "Watch export controls, OMSS actions, and intervention pricing signals.",
        "supply_stock_tightness": "Watch stock cover, delta deterioration, and low-availability months.",
    }
    mitigation_notes = {
        "price_volatility": "Use tighter hedging bands and shorter re-pricing cadence.",
        "weather_climate": "Track daily weather updates and refresh yield-risk assumptions.",
        "geopolitical_black_sea": "Monitor benchmark spreads and global tender activity closely.",
        "policy_trade_restriction": "Stress test domestic policy shocks against demand and stock assumptions.",
        "supply_stock_tightness": "Refresh balance-sheet assumptions when stock cover weakens materially.",
    }
    directions = {row[0]: row[5] for row in RISK_DEFINITIONS}

    by_month: dict[str, list[dict]] = defaultdict(list)
    for metric in monthly_metrics:
        probability = metric["normalized_score"]
        impact = impact_score(probability, impact_baselines[metric["risk_key"]])
        composite = round(0.6 * probability + 0.4 * impact, 4)
        severity = severity_from_score(composite)
        history = {
            "risk_key": metric["risk_key"],
            "metric_month": metric["metric_month"],
            "marketing_year": metric["marketing_year"],
            "probability_score": round(probability, 4),
            "impact_score": impact,
            "composite_risk_score": composite,
            "severity": severity,
            "direction": directions[metric["risk_key"]],
            "watch_items": watch_items[metric["risk_key"]],
            "mitigation_note": mitigation_notes[metric["risk_key"]],
            "source_summary": source_summaries[metric["risk_key"]],
        }
        by_month[metric["metric_month"]].append(history)

    history_rows_out = []
    current_rows = []
    alert_rows = []
    latest_month = max(by_month)
    for month, rows in sorted(by_month.items()):
        ranked = sorted(rows, key=lambda item: item["composite_risk_score"], reverse=True)
        for rank, row in enumerate(ranked, start=1):
            history_rows_out.append(
                {
                    "id": str(uuid.uuid4()),
                    **row,
                    "rank_in_month": rank,
                    "updated_at": UPDATED_AT,
                }
            )
            if row["composite_risk_score"] >= 60:
                alert_rows.append(
                    {
                        "id": str(uuid.uuid4()),
                        "risk_key": row["risk_key"],
                        "metric_month": row["metric_month"],
                        "marketing_year": row["marketing_year"],
                        "alert_level": row["severity"],
                        "composite_risk_score": row["composite_risk_score"],
                        "message": f"{row['risk_key']} is {row['severity']} with score {row['composite_risk_score']:.2f}",
                        "trigger_rule": "composite_risk_score >= 60",
                        "updated_at": UPDATED_AT,
                    }
                )
            if month == latest_month:
                current_rows.append(
                    {
                        "risk_key": row["risk_key"],
                        "as_of_month": row["metric_month"],
                        "marketing_year": row["marketing_year"],
                        "probability_score": row["probability_score"],
                        "impact_score": row["impact_score"],
                        "composite_risk_score": row["composite_risk_score"],
                        "severity": row["severity"],
                        "rank_in_month": rank,
                        "direction": row["direction"],
                        "source_summary": row["source_summary"],
                        "watch_items": row["watch_items"],
                        "mitigation_note": row["mitigation_note"],
                        "updated_at": UPDATED_AT,
                    }
                )
    return history_rows_out, current_rows, alert_rows


def insert_many(conn: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        [tuple(row[col] for col in columns) for row in rows],
    )
    conn.commit()


def build() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()
    conn = connect(OUTPUT_DB)
    ensure_schema(conn)
    wipe_tables(conn)

    insert_many(
        conn,
        "risk_definitions",
        [
            {
                "risk_key": risk_key,
                "risk_name": risk_name,
                "risk_category": risk_category,
                "description": description,
                "why_it_matters": why_it_matters,
                "direction": direction,
                "updated_at": UPDATED_AT,
            }
            for risk_key, risk_name, risk_category, description, why_it_matters, direction in RISK_DEFINITIONS
        ],
    )
    insert_many(
        conn,
        "risk_model_reference",
        [
            {
                "risk_key": risk_key,
                "model_approach": model_approach,
                "source_data": source_data,
                "formula_logic": formula_logic,
                "confidence": confidence,
                "updated_at": UPDATED_AT,
            }
            for risk_key, model_approach, source_data, formula_logic, confidence in MODEL_REFERENCE
        ],
    )

    retail_pressure = load_factor_series(DEMAND_DB, "retail_price_cpi_wheat_pressure")
    temperature = load_factor_series(DRIVERS_DB, "north_india_winter_temperature")
    frost = load_factor_series(DRIVERS_DB, "frost_risk")
    black_sea = load_factor_series(DRIVERS_DB, "black_sea_corridor")
    russian_policy = load_factor_series(DRIVERS_DB, "russian_export_policy")
    india_policy = load_factor_series(DRIVERS_DB, "india_export_policy")
    msp = load_factor_series(DRIVERS_DB, "msp")
    opening_stock = load_factor_series(SUPPLY_DB, "opening_stock")
    total_demand = load_factor_series(SUPPLY_DB, "total_demand_monthly")
    delta = load_factor_series(SUPPLY_DB, "delta")

    monthly_metrics = []
    monthly_metrics.extend(build_price_volatility(retail_pressure))
    monthly_metrics.extend(build_weather_climate(temperature, frost))
    monthly_metrics.extend(build_geopolitical(black_sea, russian_policy))
    monthly_metrics.extend(build_policy_trade(india_policy, msp))
    monthly_metrics.extend(build_supply_tightness(opening_stock, total_demand, delta))

    insert_many(
        conn,
        "risk_monthly_metrics",
        [
            {
                "id": str(uuid.uuid4()),
                **row,
                "updated_at": UPDATED_AT,
            }
            for row in monthly_metrics
        ],
    )

    history, current, alerts = history_rows(monthly_metrics)
    insert_many(conn, "risk_register_history", history)
    insert_many(conn, "risk_register_current", current)
    insert_many(conn, "risk_alerts", alerts)

    conn.close()


if __name__ == "__main__":
    build()
