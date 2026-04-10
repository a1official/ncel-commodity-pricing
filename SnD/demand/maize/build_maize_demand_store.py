from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / "maize_demand_monthly.db"
MAIZE_SUPPORT_DB = ROOT / "backend" / "data" / "maize_model_support.db"
WHEAT_SUPPORT_DB = ROOT / "backend" / "data" / "wheat_model_support.db"
MAIZE_SUPPLY_DB = ROOT / "SnD" / "supply" / "maize" / "maize_supply_factors.db"
UPDATED_AT = datetime.now(UTC).isoformat().replace("+00:00", "Z")

POPULATION_MILLIONS = {
    2015: 1311.05,
    2016: 1324.52,
    2017: 1338.68,
    2018: 1352.64,
    2019: 1366.42,
    2020: 1380.00,
    2021: 1393.41,
    2022: 1406.63,
    2023: 1428.63,
    2024: 1440.17,
    2025: 1451.67,
    2026: 1463.00,
}

FEED_WEIGHTS = {1: 0.086, 2: 0.084, 3: 0.082, 4: 0.079, 5: 0.079, 6: 0.079, 7: 0.082, 8: 0.084, 9: 0.084, 10: 0.086, 11: 0.087, 12: 0.088}
OTHER_WEIGHTS = {1: 0.082, 2: 0.081, 3: 0.081, 4: 0.081, 5: 0.081, 6: 0.081, 7: 0.083, 8: 0.084, 9: 0.084, 10: 0.086, 11: 0.088, 12: 0.088}
EXPORT_WEIGHTS = {1: 0.09, 2: 0.09, 3: 0.08, 4: 0.07, 5: 0.07, 6: 0.07, 7: 0.07, 8: 0.07, 9: 0.08, 10: 0.10, 11: 0.11, 12: 0.10}
SEED_WEIGHTS = {1: 0.01, 2: 0.01, 3: 0.01, 4: 0.02, 5: 0.04, 6: 0.19, 7: 0.22, 8: 0.08, 9: 0.03, 10: 0.16, 11: 0.16, 12: 0.07}
INDUSTRIAL_WEIGHTS = {month: 1 / 12 for month in range(1, 13)}

FACTOR_DEFINITIONS = [
    ("feed_use", "Feed use", "Maize used directly in poultry and livestock feed channels.", "main Maize demand driver", "million_tonnes"),
    ("poultry_demand_cycle", "Poultry demand cycle", "Monthly poultry-feed demand intensity index.", "important demand seasonality signal", "index_100"),
    ("industrial_use", "Industrial use", "Maize used in starch, processing, and industrial channels.", "important non-feed demand layer", "million_tonnes"),
    ("exports", "Exports", "Maize shipped out of India.", "adds external demand pull", "million_tonnes"),
    ("seed_use", "Seed use", "Maize reserved for sowing activity.", "seasonal planting demand", "million_tonnes"),
    ("domestic_other_use", "Domestic other use", "Residual food and other domestic Maize use after feed, industrial, seed, and exports.", "completes the demand balance", "million_tonnes"),
    ("ethanol_demand_signal", "Ethanol demand signal", "Policy-linked ethanol and industrial demand pressure indicator.", "policy-linked demand context", "index_100"),
    ("substitution_effect", "Substitution effect", "Relative price relationship between maize and wheat.", "captures substitution pressure", "index_100"),
    ("retail_price_pressure", "Retail / mandi price pressure", "Monthly Maize price-pressure index built from national daily mandi prices.", "explains demand response and tightness", "index_100"),
    ("policy_changes", "Policy changes", "Monthly policy-event intensity affecting Maize trade or demand.", "captures sudden demand regime shifts", "policy_index"),
    ("population_trend", "Population / consumption trend", "Interpolated population trend as slow structural demand context.", "supports baseline trend", "million_people"),
    ("total_demand_monthly", "Total demand monthly", "Total additive monthly Maize demand used for S&D balance.", "core balance-sheet demand total", "million_tonnes"),
]

FACTOR_STATUS = [
    ("feed_use", "mixed", "loaded_as_annual_to_monthly_proxy", "Built from annual Maize demand balance with poultry/feed-heavy monthly seasonality."),
    ("poultry_demand_cycle", "curated", "loaded_as_curated_monthly_series", "Curated monthly feed-demand cycle used as a demand signal."),
    ("industrial_use", "not_found_cleanly", "loaded_as_annual_to_monthly_proxy", "No long clean monthly industrial-use history was available, so industrial demand is modeled from annual demand shares."),
    ("exports", "partially_available", "loaded_as_annual_to_monthly_proxy", "Recent APEDA annual export points exist, but a full clean 10-year monthly Maize export series is not yet loaded in this pass."),
    ("seed_use", "not_found_cleanly", "loaded_as_annual_to_monthly_proxy", "Seed use is modeled seasonally around sowing windows."),
    ("domestic_other_use", "not_found_cleanly", "loaded_as_annual_to_monthly_proxy", "Residual domestic use after feed, industrial, seed, and exports."),
    ("ethanol_demand_signal", "curated", "loaded_as_policy_signal_series", "Curated step signal reflecting ethanol-linked demand attention in recent years."),
    ("substitution_effect", "available", "loaded_as_native_monthly_series", "Built from monthly maize versus wheat national mandi price relationships."),
    ("retail_price_pressure", "available", "loaded_as_native_monthly_series", "Built directly from monthly national Maize mandi prices."),
    ("policy_changes", "curated", "loaded_as_event_monthly_series", "Curated monthly policy-event score for export/trade and industrial-demand relevance."),
    ("population_trend", "annual_only", "loaded_as_annual_to_monthly_interpolation", "Interpolated monthly from annual population path."),
    ("total_demand_monthly", "derived", "computed_from_monthly_demand_components", "Computed as feed + industrial + exports + seed + domestic other use."),
]

SOURCES = [
    ("economic_survey", "Economic Survey Statistical Appendix", "https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf", "annual pdf", "Official production, area, and yield backbone used in the Maize support layer."),
    ("maize_support", "Local maize support store", str(MAIZE_SUPPORT_DB), "db", "Local support DB used for Maize indicators and national daily price context."),
    ("wheat_support", "Local wheat support store", str(WHEAT_SUPPORT_DB), "db", "Used for Maize-vs-Wheat substitution index."),
    ("apeda", "APEDA product and annual report references", "https://apeda.gov.in/", "web/pdf", "Recent Maize export points and trade context."),
    ("curated", "Curated Maize demand profile", str(Path(__file__).resolve()), "curated/local", "Curated poultry, ethanol, and policy-demand monthly signal layer."),
]


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def month_range(start: date, end: date) -> list[date]:
    current = date(start.year, start.month, 1)
    months: list[date] = []
    while current <= end:
        months.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months


def marketing_year_for_month(d: date) -> str:
    start_year = d.year if d.month >= 4 else d.year - 1
    return f"{start_year}/{str(start_year + 1)[-2:]}"


def normalized(weights: dict[int, float]) -> dict[int, float]:
    total = sum(weights.values()) or 1.0
    return {key: value / total for key, value in weights.items()}


FEED_WEIGHTS = normalized(FEED_WEIGHTS)
OTHER_WEIGHTS = normalized(OTHER_WEIGHTS)
EXPORT_WEIGHTS = normalized(EXPORT_WEIGHTS)
SEED_WEIGHTS = normalized(SEED_WEIGHTS)
INDUSTRIAL_WEIGHTS = normalized(INDUSTRIAL_WEIGHTS)


def build_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS maize_factor_definitions (
            factor_key TEXT PRIMARY KEY,
            factor_name TEXT NOT NULL,
            description TEXT NOT NULL,
            why_it_matters TEXT NOT NULL,
            default_unit TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_source_inventory (
            source_key TEXT PRIMARY KEY,
            source_name TEXT NOT NULL,
            source_url TEXT,
            cadence TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS maize_factor_status (
            factor_key TEXT PRIMARY KEY,
            monthly_source_status TEXT NOT NULL,
            current_load_mode TEXT NOT NULL,
            notes TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_factor_monthly_values (
            id TEXT PRIMARY KEY,
            factor_key TEXT NOT NULL,
            metric_month TEXT NOT NULL,
            marketing_year TEXT NOT NULL,
            value REAL,
            unit TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            method TEXT NOT NULL,
            confidence TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(factor_key, metric_month)
        );
        """
    )
    conn.commit()


def drop_legacy_tables(conn: sqlite3.Connection) -> None:
    for table in ("factor_definitions", "source_inventory", "factor_status", "factor_monthly_values"):
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()


def reset(conn: sqlite3.Connection) -> None:
    for table in ("maize_factor_definitions", "maize_source_inventory", "maize_factor_status", "maize_factor_monthly_values"):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()


def load_supply_annual_balance() -> dict[str, dict[str, float]]:
    conn = connect(MAIZE_SUPPLY_DB)
    rows = conn.execute(
        """
        SELECT factor_key, metric_month, marketing_year, value
        FROM maize_factor_monthly_values
        WHERE factor_key IN ('domestic_production', 'imports', 'opening_stock')
        ORDER BY metric_month
        """
    ).fetchall()
    conn.close()

    by_year: dict[str, dict[str, list[tuple[str, float]]]] = {}
    for row in rows:
        marketing_year = row["marketing_year"]
        factor_key = row["factor_key"]
        by_year.setdefault(marketing_year, {}).setdefault(factor_key, []).append((row["metric_month"], float(row["value"] or 0.0)))

    annual: dict[str, dict[str, float]] = {}
    for marketing_year, factor_map in by_year.items():
        opening_series = factor_map.get("opening_stock", [])
        opening_stock = opening_series[0][1] if opening_series else 0.0
        ending_stock = opening_series[-1][1] if opening_series else 0.0
        production = sum(value for _, value in factor_map.get("domestic_production", []))
        imports = sum(value for _, value in factor_map.get("imports", []))
        total_demand = max(0.0, opening_stock + production + imports - ending_stock)
        annual[marketing_year] = {
            "opening_stock": opening_stock,
            "ending_stock": ending_stock,
            "production": production,
            "imports": imports,
            "total_demand": total_demand,
        }
    return annual


def load_export_overrides() -> dict[str, float]:
    conn = connect(MAIZE_SUPPORT_DB)
    rows = conn.execute(
        """
        SELECT period_label, value, unit
        FROM maize_indicator_history
        WHERE indicator_key = 'maize_exports_mt'
        ORDER BY indicator_date
        """
    ).fetchall()
    conn.close()

    overrides: dict[str, float] = {}
    for row in rows:
        value = float(row["value"])
        unit = (row["unit"] or "").lower()
        if "mt" in unit and "million" not in unit:
            value = value / 1_000_000.0
        marketing_year = row["period_label"].replace("-", "/") if row["period_label"] else "2024/25"
        if marketing_year.count("/") == 0 and "-" in marketing_year:
            left, right = marketing_year.split("-", 1)
            marketing_year = f"{left}/{right[-2:]}"
        overrides[marketing_year] = value
    return overrides


def load_monthly_price_indices() -> tuple[dict[str, float], dict[str, float]]:
    maize_conn = connect(MAIZE_SUPPORT_DB)
    wheat_conn = connect(WHEAT_SUPPORT_DB)
    maize = maize_conn.execute(
        "SELECT substr(date, 1, 7) AS ym, AVG(modal_price) FROM maize_national_daily GROUP BY substr(date, 1, 7) ORDER BY ym"
    ).fetchall()
    wheat = wheat_conn.execute(
        "SELECT substr(date, 1, 7) AS ym, AVG(modal_price) FROM wheat_national_daily GROUP BY substr(date, 1, 7) ORDER BY ym"
    ).fetchall()
    maize_conn.close()
    wheat_conn.close()

    maize_map = {row[0]: float(row[1]) for row in maize}
    wheat_map = {row[0]: float(row[1]) for row in wheat}
    retail_pressure: dict[str, float] = {}
    substitution: dict[str, float] = {}

    if maize_map:
        maize_baseline = sum(maize_map.values()) / len(maize_map)
        retail_pressure = {f"{ym}-01": (value / maize_baseline) * 100.0 for ym, value in maize_map.items()}

    common = {ym for ym in maize_map if ym in wheat_map and maize_map[ym] > 0}
    if common:
        raw_ratios = {ym: wheat_map[ym] / maize_map[ym] for ym in common}
        ratio_baseline = sum(raw_ratios.values()) / len(raw_ratios)
        substitution = {f"{ym}-01": (value / ratio_baseline) * 100.0 for ym, value in raw_ratios.items()}

    return retail_pressure, substitution


def interpolate_population(months: list[date]) -> dict[str, float]:
    result: dict[str, float] = {}
    for d in months:
        year_start = POPULATION_MILLIONS.get(d.year)
        next_year = POPULATION_MILLIONS.get(d.year + 1, year_start)
        if year_start is None:
            fallback = max(year for year in POPULATION_MILLIONS if year <= d.year)
            year_start = POPULATION_MILLIONS[fallback]
            next_year = POPULATION_MILLIONS.get(fallback + 1, year_start)
        fraction = (d.month - 1) / 12.0
        result[d.isoformat()] = year_start + ((next_year - year_start) * fraction)
    return result


def poultry_cycle(month: int) -> float:
    return {1: 102.0, 2: 101.0, 3: 99.0, 4: 97.0, 5: 96.0, 6: 98.0, 7: 101.0, 8: 103.0, 9: 104.0, 10: 105.0, 11: 107.0, 12: 107.0}[month]


def ethanol_signal(d: date) -> float:
    if d.year <= 2020:
        return 35.0
    if d.year == 2021:
        return 45.0
    if d.year == 2022:
        return 52.0
    if d.year == 2023:
        return 60.0
    if d.year == 2024:
        return 66.0
    return 70.0


def policy_signal(d: date) -> float:
    events = {
        "2022-08": 55.0,
        "2023-07": 62.0,
        "2024-03": 58.0,
        "2025-01": 64.0,
    }
    return events.get(d.strftime("%Y-%m"), 0.0)


def build_rows() -> list[dict]:
    months = month_range(date(2016, 4, 1), date(2026, 3, 1))
    annual_balance = load_supply_annual_balance()
    export_overrides = load_export_overrides()
    retail_pressure, substitution = load_monthly_price_indices()
    population = interpolate_population(months)

    rows: list[dict] = []
    counter = 1
    for marketing_year, annual in annual_balance.items():
        total = annual["total_demand"]
        exports_annual = export_overrides.get(marketing_year, max(0.20, annual["production"] * 0.015))
        seed_annual = annual["production"] * 0.04
        industrial_annual = total * 0.12
        feed_annual = total * 0.58
        other_annual = max(0.0, total - exports_annual - seed_annual - industrial_annual - feed_annual)

        months_in_year = [m for m in months if marketing_year_for_month(m) == marketing_year]
        for d in months_in_year:
            month = d.month
            metric_month = d.isoformat()
            metric_month_key = d.strftime("%Y-%m-01")
            components = [
                ("feed_use", feed_annual * FEED_WEIGHTS[month], "million_tonnes", "Local maize supply-demand balance", str(MAIZE_SUPPLY_DB), "annual_total_demand_to_monthly_feed_proxy", "medium", "Feed-heavy Maize demand proxy."),
                ("industrial_use", industrial_annual * INDUSTRIAL_WEIGHTS[month], "million_tonnes", "Local maize supply-demand balance", str(MAIZE_SUPPLY_DB), "annual_total_demand_to_monthly_industrial_proxy", "medium", "Industrial demand proxy from annual total demand share."),
                ("exports", exports_annual * EXPORT_WEIGHTS[month], "million_tonnes", "APEDA Product Page + proxy", "https://apeda.gov.in/", "annual_exports_to_monthly_proxy", "medium", "Recent APEDA export point with proxy monthly profile."),
                ("seed_use", seed_annual * SEED_WEIGHTS[month], "million_tonnes", "Derived sowing proxy", str(Path(__file__).resolve()), "annual_seed_to_monthly_sowing_proxy", "medium", "Seed use concentrated around sowing windows."),
                ("domestic_other_use", other_annual * OTHER_WEIGHTS[month], "million_tonnes", "Local maize supply-demand balance", str(MAIZE_SUPPLY_DB), "annual_total_demand_to_monthly_other_proxy", "medium", "Residual domestic Maize use proxy."),
                ("poultry_demand_cycle", poultry_cycle(month), "index_100", "Curated Maize demand profile", str(Path(__file__).resolve()), "curated_monthly_poultry_cycle", "medium", "Poultry-feed demand intensity index."),
                ("ethanol_demand_signal", ethanol_signal(d), "index_100", "Curated Maize demand profile", str(Path(__file__).resolve()), "curated_step_signal", "medium", "Policy-linked ethanol demand signal."),
                ("policy_changes", policy_signal(d), "policy_index", "Curated Maize demand profile", str(Path(__file__).resolve()), "curated_event_series", "medium", "Monthly policy demand signal."),
                ("population_trend", population[metric_month], "million_people", "Interpolated population trend", str(Path(__file__).resolve()), "annual_population_to_monthly_interpolation", "medium", "Structural population demand context."),
                ("retail_price_pressure", retail_pressure.get(metric_month_key, 100.0), "index_100", "Local maize support store", str(MAIZE_SUPPORT_DB), "monthly_national_maize_price_index", "high", "Monthly Maize national price-pressure index."),
                ("substitution_effect", substitution.get(metric_month_key, 100.0), "index_100", "Local maize vs wheat support stores", f"{MAIZE_SUPPORT_DB} | {WHEAT_SUPPORT_DB}", "monthly_maize_vs_wheat_ratio_index", "medium", "Relative price substitution index versus wheat."),
            ]

            total_month = 0.0
            for factor_key, value, unit, source_name, source_url, method, confidence, notes in components:
                numeric_value = round(float(value), 6)
                if factor_key in {"feed_use", "industrial_use", "exports", "seed_use", "domestic_other_use"}:
                    total_month += numeric_value
                rows.append(
                    {
                        "id": f"maize-demand-{counter:05d}",
                        "factor_key": factor_key,
                        "metric_month": metric_month,
                        "marketing_year": marketing_year,
                        "value": numeric_value,
                        "unit": unit,
                        "source_name": source_name,
                        "source_url": source_url,
                        "method": method,
                        "confidence": confidence,
                        "notes": notes,
                        "updated_at": UPDATED_AT,
                    }
                )
                counter += 1

            rows.append(
                {
                    "id": f"maize-demand-{counter:05d}",
                    "factor_key": "total_demand_monthly",
                    "metric_month": metric_month,
                    "marketing_year": marketing_year,
                    "value": round(total_month, 6),
                    "unit": "million_tonnes",
                    "source_name": "Derived inside Maize demand store",
                    "source_url": str(Path(__file__).resolve()),
                    "method": "feed_plus_industrial_plus_exports_plus_seed_plus_domestic_other_use",
                    "confidence": "medium",
                    "notes": "Derived monthly total demand for Maize.",
                    "updated_at": UPDATED_AT,
                }
            )
            counter += 1

    return rows


def build() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect(OUTPUT_DB)
    drop_legacy_tables(conn)
    build_schema(conn)
    reset(conn)

    conn.executemany(
        "INSERT INTO maize_factor_definitions (factor_key, factor_name, description, why_it_matters, default_unit) VALUES (?, ?, ?, ?, ?)",
        FACTOR_DEFINITIONS,
    )
    conn.executemany(
        "INSERT INTO maize_source_inventory (source_key, source_name, source_url, cadence, notes) VALUES (?, ?, ?, ?, ?)",
        SOURCES,
    )
    conn.executemany(
        "INSERT INTO maize_factor_status (factor_key, monthly_source_status, current_load_mode, notes) VALUES (?, ?, ?, ?)",
        FACTOR_STATUS,
    )

    rows = build_rows()
    conn.executemany(
        """
        INSERT INTO maize_factor_monthly_values (
            id, factor_key, metric_month, marketing_year, value, unit,
            source_name, source_url, method, confidence, notes, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row["factor_key"],
                row["metric_month"],
                row["marketing_year"],
                row["value"],
                row["unit"],
                row["source_name"],
                row["source_url"],
                row["method"],
                row["confidence"],
                row["notes"],
                row["updated_at"],
            )
            for row in rows
        ],
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    build()
    print(f"Built {OUTPUT_DB}")
