from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / "maize_supply_factors.db"
MAIZE_SUPPORT_DB = ROOT / "backend" / "data" / "maize_model_support.db"
SUPPLY_DEMAND_DB = ROOT / "backend" / "data" / "supply_demand_analytics.db"
WASDE_TEXT_PATH = ROOT / "backend" / "data" / "tmp_wasde0326.txt"
UPDATED_AT = datetime.now(UTC).isoformat().replace("+00:00", "Z")
START_MONTH = date(2016, 4, 1)
END_MONTH = date(2026, 3, 1)


SUPPLY_FACTORS = [
    (
        "acreage_sown_area",
        "Acreage (sown area)",
        "India",
        "area",
        "million_hectare",
        "Monthly maize acreage context for India.",
        "Production expands or contracts when maize acreage changes.",
        "high",
        "Loaded from official annual area rows and held monthly within each source annual period.",
    ),
    (
        "yield_per_hectare",
        "Yield per hectare",
        "India",
        "yield",
        "kg_per_hectare",
        "Monthly maize yield context for India.",
        "Yield converts area into actual production and captures crop stress.",
        "high",
        "Loaded from official annual yield rows and held monthly within each source annual period.",
    ),
    (
        "domestic_production",
        "Domestic production",
        "India",
        "production",
        "million_tonnes",
        "Monthly maize production inflow into domestic availability.",
        "Main supply block for the maize balance sheet.",
        "high",
        "Distributed from annual production into monthly maize harvest-release weights.",
    ),
    (
        "opening_stock",
        "Opening stocks",
        "India",
        "stock",
        "million_tonnes",
        "Monthly maize opening carry stock available to the domestic system.",
        "Provides the starting supply cushion before fresh crop and imports arrive.",
        "medium",
        "Uses local annual delta history and current USDA carry-over point to reconstruct a monthly stock path.",
    ),
    (
        "imports",
        "Imports",
        "India",
        "trade",
        "million_tonnes",
        "Monthly maize imports into India.",
        "Adds to domestic availability when local supply is tight.",
        "medium",
        "Uses USDA and local S&D import points with monthly allocation weights where no long native monthly trade panel exists yet.",
    ),
    (
        "buffer_stock",
        "Buffer stock",
        "India",
        "stock",
        "million_tonnes",
        "Monthly public-stock or government-cushion context for maize.",
        "Useful to monitor supply cushion and policy release capacity.",
        "medium",
        "Uses the same stock backbone as opening stock until a separate public maize stock series is available.",
    ),
    (
        "usda_global_production",
        "USDA global production by country",
        "Global",
        "global_production",
        "million_tonnes",
        "Country-wise maize production context for major global producers.",
        "Tracks external supply pressure from major exporters and benchmark producers.",
        "high",
        "Loaded from the local USDA WASDE March 2026 text snapshot and held monthly by marketing year.",
    ),
    (
        "major_producer_crop_conditions",
        "Major producer crop conditions",
        "Global",
        "crop_condition",
        "index",
        "Monthly crop-condition context for major maize producers.",
        "Early warning layer for future global maize supply risk.",
        "medium",
        "Loaded as recurring monthly crop-condition profiles for the US, Brazil, Argentina, and Ukraine.",
    ),
    (
        "brazil_safrinha_harvest_calendar",
        "Brazil safrinha harvest calendar",
        "Global",
        "calendar",
        "index",
        "Monthly seasonal harvest intensity for Brazil's safrinha maize crop.",
        "Helps explain when major global maize supply enters the market.",
        "medium",
        "Loaded as a recurring monthly seasonal calendar.",
    ),
    (
        "global_exporter_harvest_calendar",
        "Global exporter harvest calendar",
        "Global",
        "calendar",
        "index",
        "Monthly seasonal harvest timing for key maize exporters.",
        "Explains timing of fresh global maize supply and export pressure.",
        "medium",
        "Loaded as a recurring combined exporter harvest calendar.",
    ),
    (
        "total_availability",
        "Total availability",
        "India",
        "derived",
        "million_tonnes",
        "Total monthly maize available to the domestic system.",
        "Primary supply formula used in the maize S&D balance logic.",
        "high",
        "Derived monthly as opening stock + domestic production + imports.",
    ),
]


SOURCE_INVENTORY = [
    (
        "maize_support_db",
        "Local maize support store",
        str(MAIZE_SUPPORT_DB),
        "annual / daily / monthly",
        "Area, yield, production, benchmark, and market-support rows already loaded into the maize support DB.",
    ),
    (
        "economic_survey",
        "Economic Survey Statistical Appendix",
        "https://www.indiabudget.gov.in/economicsurvey/",
        "annual",
        "Official India area, yield, and production backbone for maize.",
    ),
    (
        "local_supply_demand",
        "Local supply-demand analytics store",
        str(SUPPLY_DEMAND_DB),
        "annual / snapshot",
        "Current carry-over, imports, closing stock, and annual maize delta history.",
    ),
    (
        "usda_wasde_text",
        "USDA WASDE March 2026 local text snapshot",
        str(WASDE_TEXT_PATH),
        "monthly snapshot",
        "Local WASDE text file used to seed global maize production by country.",
    ),
    (
        "crop_progress",
        "Curated global maize crop-condition profiles",
        "https://www.usda.gov/",
        "monthly",
        "Recurring monthly crop-condition profiles for major maize producers.",
    ),
    (
        "maize_harvest_calendar",
        "Curated global maize harvest calendar",
        "https://www.fao.org/",
        "seasonal",
        "Seasonal harvest timing context for major maize exporters.",
    ),
]


GLOBAL_MAIZE_PRODUCTION = {
    "2023/24": {
        "United States": 389.67,
        "Brazil": 119.00,
        "Argentina": 51.60,
        "Ukraine": 32.50,
    },
    "2024/25": {
        "United States": 378.27,
        "Brazil": 136.00,
        "Argentina": 50.00,
        "Ukraine": 26.80,
    },
    "2025/26": {
        "United States": 432.34,
        "Brazil": 131.00,
        "Argentina": 53.00,
        "Ukraine": 29.00,
    },
}

PRODUCTION_RELEASE_WEIGHTS = {
    4: 0.03,
    5: 0.05,
    6: 0.08,
    7: 0.09,
    8: 0.09,
    9: 0.14,
    10: 0.18,
    11: 0.16,
    12: 0.09,
    1: 0.05,
    2: 0.03,
    3: 0.01,
}

IMPORT_WEIGHTS = {month: 1.0 / 12.0 for month in range(1, 13)}

BRAZIL_SAFRINHA_CALENDAR = {1: 12.0, 2: 18.0, 3: 26.0, 4: 42.0, 5: 68.0, 6: 92.0, 7: 100.0, 8: 82.0, 9: 44.0, 10: 18.0, 11: 8.0, 12: 5.0}
GLOBAL_EXPORTER_HARVEST_CALENDAR = {1: 34.0, 2: 28.0, 3: 22.0, 4: 24.0, 5: 39.0, 6: 55.0, 7: 73.0, 8: 88.0, 9: 100.0, 10: 94.0, 11: 76.0, 12: 58.0}
MAJOR_PRODUCER_CONDITIONS = {
    "United States": {1: 38.0, 2: 35.0, 3: 40.0, 4: 52.0, 5: 63.0, 6: 74.0, 7: 78.0, 8: 71.0, 9: 60.0, 10: 48.0, 11: 40.0, 12: 36.0},
    "Brazil": {1: 72.0, 2: 70.0, 3: 66.0, 4: 62.0, 5: 58.0, 6: 56.0, 7: 55.0, 8: 57.0, 9: 60.0, 10: 65.0, 11: 69.0, 12: 71.0},
    "Argentina": {1: 69.0, 2: 67.0, 3: 63.0, 4: 58.0, 5: 54.0, 6: 52.0, 7: 50.0, 8: 51.0, 9: 55.0, 10: 61.0, 11: 66.0, 12: 68.0},
    "Ukraine": {1: 41.0, 2: 39.0, 3: 43.0, 4: 50.0, 5: 60.0, 6: 70.0, 7: 76.0, 8: 73.0, 9: 64.0, 10: 53.0, 11: 45.0, 12: 42.0},
}


def _connect(path: Path = OUTPUT_DB) -> sqlite3.Connection:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS maize_factor_definitions (
            factor_key TEXT PRIMARY KEY,
            factor_name TEXT NOT NULL,
            geography_scope TEXT NOT NULL,
            factor_group TEXT NOT NULL,
            default_unit TEXT NOT NULL,
            description TEXT NOT NULL,
            why_it_matters TEXT NOT NULL,
            priority TEXT NOT NULL,
            loading_note TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_source_inventory (
            source_key TEXT PRIMARY KEY,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            cadence TEXT NOT NULL,
            notes TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_factor_status (
            factor_key TEXT PRIMARY KEY,
            monthly_source_status TEXT NOT NULL,
            current_load_mode TEXT NOT NULL,
            notes TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_factor_values (
            id TEXT PRIMARY KEY,
            factor_key TEXT NOT NULL,
            metric_date TEXT NOT NULL,
            period_type TEXT NOT NULL,
            geography TEXT NOT NULL,
            value REAL,
            unit TEXT,
            source_name TEXT,
            source_url TEXT,
            method TEXT,
            confidence TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_factor_monthly_values (
            id TEXT PRIMARY KEY,
            factor_key TEXT NOT NULL,
            metric_month TEXT NOT NULL,
            marketing_year TEXT NOT NULL,
            geography TEXT NOT NULL,
            value REAL,
            unit TEXT,
            source_name TEXT,
            source_url TEXT,
            method TEXT,
            confidence TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def _drop_legacy_tables(conn: sqlite3.Connection) -> None:
    for table in ["factor_definitions", "source_inventory", "factor_status", "factor_values", "factor_monthly_values"]:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()


def _month_iter(start: date, end: date) -> list[date]:
    months = []
    current = start
    while current <= end:
        months.append(current)
        current = date(current.year + (current.month // 12), (current.month % 12) + 1, 1)
    return months


def _normalize_period(period_label: str | None) -> str:
    return (period_label or "").replace("-", "/")


def _months_for_period(period_label: str) -> list[date]:
    start_year = int(period_label[:4])
    return _month_iter(date(start_year, 4, 1), date(start_year + 1, 3, 1))


def _marketing_year_for_month(metric_month: date) -> str:
    if metric_month.month >= 10:
        return f"{metric_month.year}/{str(metric_month.year + 1)[2:]}"
    return f"{metric_month.year - 1}/{str(metric_month.year)[2:]}"


def _load_indicator_rows() -> dict[str, list[sqlite3.Row]]:
    with sqlite3.connect(MAIZE_SUPPORT_DB) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        payload = {}
        for indicator_key in [
            "maize_area",
            "maize_production",
            "maize_yield_kg_per_hectare",
            "usda_maize_beginning_stocks",
            "usda_maize_ending_stocks",
            "usda_maize_imports",
        ]:
            payload[indicator_key] = cur.execute(
                """
                SELECT *
                FROM maize_indicator_history
                WHERE indicator_key = ?
                ORDER BY indicator_date
                """,
                (indicator_key,),
            ).fetchall()
    return payload


def _load_supply_snapshot() -> dict[str, Any]:
    with sqlite3.connect(SUPPLY_DEMAND_DB) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT *
            FROM supply_demand_signals
            WHERE crop = 'Maize'
            ORDER BY signal_date DESC
            LIMIT 1
            """
        ).fetchone()
        history = conn.execute(
            """
            SELECT *
            FROM supply_demand_delta_history
            WHERE crop = 'Maize'
            ORDER BY marketing_year
            """
        ).fetchall()
    return {
        "snapshot": dict(row) if row is not None else {},
        "history": [dict(item) for item in history],
    }


def _append_current_snapshot_indicators(rows: dict[str, list[sqlite3.Row]], snapshot_payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    snapshot = snapshot_payload.get('snapshot', {})
    normalized = {key: [dict(item) for item in value] for key, value in rows.items()}
    if not snapshot:
        return normalized

    current_period = '2025/26'
    annual_date = '2026-03-31'
    source_name = 'Unified current crop balance snapshot'
    source_url = str(SUPPLY_DEMAND_DB)
    updates = [
        ('maize_area', 'Maize gross area', snapshot.get('area_million_hectare'), 'million_hectare'),
        ('maize_production', 'Maize production', snapshot.get('production_million_tonnes'), 'million_tonnes'),
        ('maize_yield_kg_per_hectare', 'Maize yield per hectare', snapshot.get('yield_kg_per_hectare'), 'kg_per_hectare'),
    ]
    for indicator_key, indicator_name, value, unit in updates:
        if value is None:
            continue
        normalized[indicator_key].append({
            'indicator_key': indicator_key,
            'indicator_name': indicator_name,
            'indicator_date': annual_date,
            'period_label': current_period,
            'value': float(value),
            'unit': unit,
            'source_name': source_name,
            'source_url': source_url,
            'notes': f'Current annual maize {indicator_name.lower()} seeded from the unified supply-demand snapshot for {current_period}.',
        })
    return normalized


def _build_stock_anchors(snapshot_payload: dict[str, Any]) -> dict[str, dict[str, float]]:
    history = snapshot_payload["history"]
    annual_closing = {item["marketing_year"]: float(item["delta_million_tonnes"]) for item in history if item["marketing_year"] != "Current Snapshot"}
    annual_imports = {item["marketing_year"]: float(item["imports_million_tonnes"] or 0.0) for item in history if item["marketing_year"] != "Current Snapshot"}
    current = snapshot_payload["snapshot"]
    annual_opening_current = float(current.get("carry_over_million_tonnes") or annual_closing.get("2024/25", 0.0)) if current else annual_closing.get("2024/25", 0.0)
    if current:
        annual_closing["2025/26"] = float(current.get("stock_million_tonnes") or current.get("closing_stock_million_tonnes") or annual_closing.get("2025/26", 0.0))
        annual_imports["2025/26"] = float(current.get("imports_million_tonnes") or 0.0)
    periods = [f"{year}/{str(year + 1)[2:]}" for year in range(2016, 2026)]
    fallback_stock = annual_closing.get("2021/22", 2.395)
    anchors = {}
    for period in periods:
        if period == "2025/26":
            opening = annual_opening_current
        else:
            previous_end_year = int(period[:4])
            prev_label = f"{previous_end_year - 1}/{str(previous_end_year)[2:]}"
            opening = annual_closing.get(prev_label, fallback_stock)
        closing = annual_closing.get(period, opening)
        imports = annual_imports.get(period, 0.0)
        anchors[period] = {"opening": opening, "closing": closing, "imports": imports}
    return anchors


def _annual_indicator_to_values(rows: list[sqlite3.Row], factor_key: str, geography: str) -> list[tuple]:
    payload = []
    for row in rows:
        payload.append((
            str(uuid.uuid4()), factor_key, row["indicator_date"], "annual", geography,
            float(row["value"]), row["unit"], row["source_name"], row["source_url"],
            "native_annual_indicator", "high", row["notes"], UPDATED_AT,
        ))
    return payload


def _build_monthly_hold_rows(rows: list[sqlite3.Row], factor_key: str, geography: str) -> list[tuple]:
    payload = []
    for row in rows:
        period = _normalize_period(row["period_label"])
        if not period:
            continue
        for metric_month in _months_for_period(period):
            if not (START_MONTH <= metric_month <= END_MONTH):
                continue
            payload.append((
                str(uuid.uuid4()), factor_key, metric_month.isoformat(), period, geography,
                float(row["value"]), row["unit"], row["source_name"], row["source_url"],
                "annual_hold_constant_monthly", "high", row["notes"], UPDATED_AT,
            ))
    return payload


def _build_monthly_production_rows(rows: list[sqlite3.Row]) -> list[tuple]:
    payload = []
    for row in rows:
        period = _normalize_period(row["period_label"])
        if not period:
            continue
        annual_value = float(row["value"])
        for metric_month in _months_for_period(period):
            if not (START_MONTH <= metric_month <= END_MONTH):
                continue
            payload.append((
                str(uuid.uuid4()), "domestic_production", metric_month.isoformat(), period, "India",
                round(annual_value * PRODUCTION_RELEASE_WEIGHTS[metric_month.month], 6), row["unit"], row["source_name"], row["source_url"],
                "annual_production_to_monthly_harvest_release_proxy", "medium_high",
                f"Annual maize production distributed into monthly harvest-release weights for {period}.", UPDATED_AT,
            ))
    return payload


def _build_monthly_stock_rows(anchors: dict[str, dict[str, float]], factor_key: str) -> list[tuple]:
    payload = []
    for period, values in anchors.items():
        months = [m for m in _months_for_period(period) if START_MONTH <= m <= END_MONTH]
        if not months:
            continue
        opening = float(values["opening"])
        closing = float(values["closing"])
        denominator = max(len(months) - 1, 1)
        for idx, metric_month in enumerate(months):
            value = opening + ((closing - opening) * (idx / denominator))
            payload.append((
                str(uuid.uuid4()), factor_key, metric_month.isoformat(), period, "India",
                round(value, 6), "million_tonnes", "Local supply-demand analytics store", str(SUPPLY_DEMAND_DB),
                "annual_opening_to_closing_stock_interpolation", "medium",
                f"Monthly maize stock path reconstructed from annual carry and delta anchors for {period}.", UPDATED_AT,
            ))
    return payload


def _build_monthly_import_rows(anchors: dict[str, dict[str, float]]) -> list[tuple]:
    payload = []
    for period, values in anchors.items():
        annual_imports = float(values["imports"])
        for metric_month in [m for m in _months_for_period(period) if START_MONTH <= m <= END_MONTH]:
            payload.append((
                str(uuid.uuid4()), "imports", metric_month.isoformat(), period, "India",
                round(annual_imports * IMPORT_WEIGHTS[metric_month.month], 6), "million_tonnes",
                "Local supply-demand analytics store", str(SUPPLY_DEMAND_DB),
                "annual_imports_to_monthly_uniform_proxy", "medium",
                f"Annual maize imports allocated across months for {period}.", UPDATED_AT,
            ))
    return payload


def _build_global_production_values() -> list[tuple]:
    payload = []
    for marketing_year, country_values in GLOBAL_MAIZE_PRODUCTION.items():
        end_year = 2000 + int(marketing_year.split("/")[1])
        metric_date = f"{end_year}-03-31"
        for country, value in country_values.items():
            payload.append((
                str(uuid.uuid4()), "usda_global_production", metric_date, "annual", country,
                float(value), "million_tonnes", "USDA WASDE March 2026 local text snapshot", str(WASDE_TEXT_PATH),
                "native_annual_snapshot", "high",
                f"Country maize production from local USDA WASDE text snapshot for {marketing_year}.", UPDATED_AT,
            ))
    return payload


def _build_global_production_monthly() -> list[tuple]:
    payload = []
    for period in [f"{year}/{str(year + 1)[2:]}" for year in range(2016, 2026)]:
        country_values = GLOBAL_MAIZE_PRODUCTION.get(period, GLOBAL_MAIZE_PRODUCTION["2023/24"])
        method = "usda_marketing_year_hold_constant_monthly" if period in GLOBAL_MAIZE_PRODUCTION else "backfilled_from_2023_24_usda_snapshot"
        confidence = "high" if period in GLOBAL_MAIZE_PRODUCTION else "low_medium"
        for metric_month in _months_for_period(period):
            if not (START_MONTH <= metric_month <= END_MONTH):
                continue
            for country, value in country_values.items():
                payload.append((
                    str(uuid.uuid4()), "usda_global_production", metric_month.isoformat(), period, country,
                    float(value), "million_tonnes", "USDA WASDE March 2026 local text snapshot", str(WASDE_TEXT_PATH),
                    method, confidence, f"Maize production by country held monthly for {period}.", UPDATED_AT,
                ))
    return payload


def _build_monthly_profile_rows(factor_key: str, profiles: dict[str, dict[int, float]], source_name: str, source_url: str, method: str) -> list[tuple]:
    payload = []
    for metric_month in _month_iter(START_MONTH, END_MONTH):
        for geography, month_map in profiles.items():
            payload.append((
                str(uuid.uuid4()), factor_key, metric_month.isoformat(), _marketing_year_for_month(metric_month), geography,
                float(month_map[metric_month.month]), "index", source_name, source_url, method, "medium",
                f"Recurring monthly profile for {geography}.", UPDATED_AT,
            ))
    return payload


def _build_single_profile_rows(factor_key: str, profile: dict[int, float], source_name: str, source_url: str, method: str) -> list[tuple]:
    payload = []
    for metric_month in _month_iter(START_MONTH, END_MONTH):
        payload.append((
            str(uuid.uuid4()), factor_key, metric_month.isoformat(), _marketing_year_for_month(metric_month), "Global",
            float(profile[metric_month.month]), "index", source_name, source_url, method, "medium",
            "Recurring monthly harvest calendar profile.", UPDATED_AT,
        ))
    return payload


def _build_total_availability_rows(conn: sqlite3.Connection) -> list[tuple]:
    rows = conn.execute(
        """
        SELECT metric_month, marketing_year,
               SUM(CASE WHEN factor_key = 'opening_stock' THEN value ELSE 0 END) AS opening_stock,
               SUM(CASE WHEN factor_key = 'domestic_production' THEN value ELSE 0 END) AS production,
               SUM(CASE WHEN factor_key = 'imports' THEN value ELSE 0 END) AS imports
        FROM maize_factor_monthly_values
        WHERE geography = 'India' AND factor_key IN ('opening_stock', 'domestic_production', 'imports')
        GROUP BY metric_month, marketing_year
        ORDER BY metric_month
        """
    ).fetchall()
    payload = []
    for row in rows:
        availability = float(row["opening_stock"] or 0.0) + float(row["production"] or 0.0) + float(row["imports"] or 0.0)
        payload.append((
            str(uuid.uuid4()), "total_availability", row["metric_month"], row["marketing_year"], "India",
            round(availability, 6), "million_tonnes", "Derived inside Maize supply store", str(OUTPUT_DB),
            "opening_stock_plus_domestic_production_plus_imports", "high",
            "Derived monthly maize availability from opening stock, production, and imports.", UPDATED_AT,
        ))
    return payload


def build_maize_supply_store() -> dict[str, Any]:
    indicator_rows = _load_indicator_rows()
    snapshot_payload = _load_supply_snapshot()
    indicator_rows = _append_current_snapshot_indicators(indicator_rows, snapshot_payload)
    stock_anchors = _build_stock_anchors(snapshot_payload)

    with _connect() as conn:
        _drop_legacy_tables(conn)
        _ensure_schema(conn)
        for table in ["maize_factor_definitions", "maize_source_inventory", "maize_factor_status", "maize_factor_values", "maize_factor_monthly_values"]:
            conn.execute(f"DELETE FROM {table}")

        conn.executemany(
            """
            INSERT INTO maize_factor_definitions (
                factor_key, factor_name, geography_scope, factor_group, default_unit,
                description, why_it_matters, priority, loading_note, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [(*row, UPDATED_AT) for row in SUPPLY_FACTORS],
        )
        conn.executemany(
            """
            INSERT INTO maize_source_inventory (source_key, source_name, source_url, cadence, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(*row, UPDATED_AT) for row in SOURCE_INVENTORY],
        )
        status_rows = [
            ("acreage_sown_area", "annual_only", "loaded_as_annual_to_monthly_hold_constant", "Official maize area is annual in the maize support store and is repeated monthly within each source annual period.", UPDATED_AT),
            ("yield_per_hectare", "annual_only", "loaded_as_annual_to_monthly_hold_constant", "Official maize yield is annual in the maize support store and is repeated monthly within each source annual period.", UPDATED_AT),
            ("domestic_production", "annual_only", "loaded_as_annual_to_monthly_harvest_release_proxy", "Official maize production is annual; monthly supply inflow is distributed using maize harvest-release weights.", UPDATED_AT),
            ("opening_stock", "mixed", "loaded_as_reconstructed_monthly_stock_path", "Monthly maize opening stock is reconstructed from local annual delta anchors and the current USDA carry-over point.", UPDATED_AT),
            ("imports", "mixed", "loaded_as_annual_to_monthly_proxy", "Current maize imports use USDA or local annual import points distributed across months because a full long monthly import panel has not been loaded yet.", UPDATED_AT),
            ("buffer_stock", "mixed", "loaded_as_same_stock_backbone_as_opening_stock", "Buffer stock currently uses the same reconstructed monthly stock backbone as opening stock.", UPDATED_AT),
            ("usda_global_production", "partial", "loaded_as_recent_usda_annual_snapshot_plus_backfill", "Global maize production by country is loaded from the local USDA WASDE March 2026 snapshot for recent years and backfilled earlier.", UPDATED_AT),
            ("major_producer_crop_conditions", "curated", "loaded_as_recurring_monthly_profiles", "Recurring monthly crop-condition profiles are used for major maize producers.", UPDATED_AT),
            ("brazil_safrinha_harvest_calendar", "curated", "loaded_as_recurring_monthly_calendar", "Recurring monthly seasonal calendar for Brazil's safrinha maize crop.", UPDATED_AT),
            ("global_exporter_harvest_calendar", "curated", "loaded_as_recurring_monthly_calendar", "Recurring monthly harvest calendar for global maize exporters.", UPDATED_AT),
            ("total_availability", "derived", "computed_from_monthly_supply_components", "Derived directly from monthly opening stock, domestic production inflow, and imports.", UPDATED_AT),
        ]
        conn.executemany(
            "INSERT INTO maize_factor_status (factor_key, monthly_source_status, current_load_mode, notes, updated_at) VALUES (?, ?, ?, ?, ?)",
            status_rows,
        )

        annual_values = []
        annual_values.extend(_annual_indicator_to_values(indicator_rows["maize_area"], "acreage_sown_area", "India"))
        annual_values.extend(_annual_indicator_to_values(indicator_rows["maize_yield_kg_per_hectare"], "yield_per_hectare", "India"))
        annual_values.extend(_annual_indicator_to_values(indicator_rows["maize_production"], "domestic_production", "India"))
        annual_values.extend(_annual_indicator_to_values(indicator_rows["usda_maize_beginning_stocks"], "opening_stock", "India"))
        annual_values.extend(_annual_indicator_to_values(indicator_rows["usda_maize_ending_stocks"], "buffer_stock", "India"))
        annual_values.extend(_annual_indicator_to_values(indicator_rows["usda_maize_imports"], "imports", "India"))
        annual_values.extend(_build_global_production_values())
        conn.executemany(
            "INSERT INTO maize_factor_values (id, factor_key, metric_date, period_type, geography, value, unit, source_name, source_url, method, confidence, notes, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            annual_values,
        )

        monthly_values = []
        monthly_values.extend(_build_monthly_hold_rows(indicator_rows["maize_area"], "acreage_sown_area", "India"))
        monthly_values.extend(_build_monthly_hold_rows(indicator_rows["maize_yield_kg_per_hectare"], "yield_per_hectare", "India"))
        monthly_values.extend(_build_monthly_production_rows(indicator_rows["maize_production"]))
        monthly_values.extend(_build_monthly_stock_rows(stock_anchors, "opening_stock"))
        monthly_values.extend(_build_monthly_import_rows(stock_anchors))
        monthly_values.extend(_build_monthly_stock_rows(stock_anchors, "buffer_stock"))
        monthly_values.extend(_build_global_production_monthly())
        monthly_values.extend(_build_monthly_profile_rows("major_producer_crop_conditions", MAJOR_PRODUCER_CONDITIONS, "Curated global maize crop-condition profile", "https://www.usda.gov/", "recurring_monthly_crop_condition_profile"))
        monthly_values.extend(_build_single_profile_rows("brazil_safrinha_harvest_calendar", BRAZIL_SAFRINHA_CALENDAR, "Curated Brazil safrinha harvest calendar", "https://www.fao.org/", "recurring_monthly_harvest_calendar"))
        monthly_values.extend(_build_single_profile_rows("global_exporter_harvest_calendar", GLOBAL_EXPORTER_HARVEST_CALENDAR, "Curated global maize exporter harvest calendar", "https://www.fao.org/", "recurring_monthly_harvest_calendar"))
        conn.executemany(
            "INSERT INTO maize_factor_monthly_values (id, factor_key, metric_month, marketing_year, geography, value, unit, source_name, source_url, method, confidence, notes, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            monthly_values,
        )
        conn.executemany(
            "INSERT INTO maize_factor_monthly_values (id, factor_key, metric_month, marketing_year, geography, value, unit, source_name, source_url, method, confidence, notes, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            _build_total_availability_rows(conn),
        )
        conn.commit()

        monthly_range = conn.execute("SELECT MIN(metric_month), MAX(metric_month) FROM maize_factor_monthly_values").fetchone()
        return {
            "db_path": str(OUTPUT_DB),
            "maize_factor_definitions": conn.execute("SELECT COUNT(*) FROM maize_factor_definitions").fetchone()[0],
            "maize_source_inventory": conn.execute("SELECT COUNT(*) FROM maize_source_inventory").fetchone()[0],
            "maize_factor_status": conn.execute("SELECT COUNT(*) FROM maize_factor_status").fetchone()[0],
            "maize_factor_values": conn.execute("SELECT COUNT(*) FROM maize_factor_values").fetchone()[0],
            "maize_factor_monthly_values": conn.execute("SELECT COUNT(*) FROM maize_factor_monthly_values").fetchone()[0],
            "monthly_range": [monthly_range[0], monthly_range[1]],
        }


if __name__ == "__main__":
    print(json.dumps(build_maize_supply_store(), indent=2))
