from __future__ import annotations

import importlib.util
import json
import math
import sqlite3
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

import requests


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / "wheat_supply_factors.db"
WHEAT_SUPPORT_DB = ROOT / "backend" / "data" / "wheat_model_support.db"
WHEAT_DEMAND_DB = ROOT / "SnD" / "demand" / "wheat" / "wheat_demand_monthly.db"
WHEAT_DEMAND_BUILDER = ROOT / "SnD" / "demand" / "wheat" / "build_wheat_demand_store.py"
WASDE_XML_URL = "https://esmis.nal.usda.gov/sites/default/release-files/795813/wasde0326.xml"
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
        "Monthly wheat acreage context for India.",
        "Production expands or contracts when wheat acreage changes.",
        "high",
        "Loaded from official annual area rows and held monthly within each marketing year.",
    ),
    (
        "yield_per_hectare",
        "Yield per hectare",
        "India",
        "yield",
        "kg_per_hectare",
        "Monthly wheat yield context for India.",
        "Yield converts area into actual production and captures productivity stress.",
        "high",
        "Loaded from official annual yield rows and held monthly within each marketing year.",
    ),
    (
        "domestic_production",
        "Domestic production",
        "India",
        "production",
        "million_tonnes",
        "Monthly wheat production inflow into supply availability.",
        "Main supply block; harvested crop enters supply primarily during harvest months.",
        "high",
        "Distributed from annual official production into monthly harvest-release weights.",
    ),
    (
        "opening_stock",
        "Opening stocks",
        "India",
        "stock",
        "million_tonnes",
        "Monthly wheat carry stock available to the system.",
        "Provides the starting supply cushion before new crop or imports arrive.",
        "high",
        "Uses actual monthly DFPD stock where available and annual stock-path interpolation otherwise.",
    ),
    (
        "imports",
        "Imports",
        "India",
        "trade",
        "million_tonnes",
        "Monthly wheat imports into India.",
        "Adds to domestic availability when local supply is tight.",
        "high",
        "Loaded from monthly TradeStat series cached in the wheat demand store.",
    ),
    (
        "buffer_stock",
        "Buffer stock",
        "India",
        "stock",
        "million_tonnes",
        "Monthly government wheat stock / buffer reference.",
        "Useful to monitor public supply cushion and release capacity.",
        "high",
        "Uses actual monthly DFPD stock where available and interpolated stock path otherwise.",
    ),
    (
        "usda_global_production",
        "USDA global production by country",
        "Global",
        "global_production",
        "million_tonnes",
        "Country-wise wheat production context for major global producers.",
        "Tracks external supply pressure from major producers.",
        "medium",
        "Uses March 2026 USDA wheat tables for 2023/24-2025/26 and backfills earlier years cautiously.",
    ),
    (
        "major_producer_crop_conditions",
        "Major producer crop conditions",
        "Global",
        "crop_condition",
        "index",
        "Monthly crop-condition context for major wheat producers.",
        "Early warning layer for future global supply risk.",
        "medium",
        "Recurring monthly crop-condition profiles by producer geography.",
    ),
    (
        "southern_hemisphere_harvest_calendar",
        "Southern Hemisphere harvest calendar",
        "Global",
        "calendar",
        "index",
        "Monthly seasonal harvest intensity for Southern Hemisphere producers.",
        "Helps explain when fresh global supply enters the market.",
        "medium",
        "Recurring monthly seasonal calendar for Australia and Argentina.",
    ),
    (
        "total_demand_monthly",
        "Total demand monthly",
        "India",
        "demand",
        "million_tonnes",
        "Monthly additive wheat demand used in the S&D balance.",
        "Lets us compare monthly availability against total monthly deductions.",
        "high",
        "Loaded from the wheat demand store's derived monthly total demand series.",
    ),
    (
        "delta",
        "Delta",
        "India",
        "derived_balance",
        "million_tonnes",
        "Monthly balance residue after comparing supply availability with total demand.",
        "Positive delta implies more cushion; lower or negative delta implies tighter balance.",
        "high",
        "Derived monthly as total availability minus total demand monthly.",
    ),
    (
        "total_availability",
        "Total availability",
        "India",
        "derived",
        "million_tonnes",
        "Total monthly wheat available to the domestic system.",
        "Primary supply formula used in S&D balance logic.",
        "high",
        "Derived monthly as opening stock + domestic production + imports.",
    ),
]


FACTOR_STATUS = [
    (
        "acreage_sown_area",
        "annual_only",
        "loaded_as_annual_to_monthly_hold_constant",
        "Official wheat area is annual in the local support store and is repeated monthly within the marketing year.",
    ),
    (
        "yield_per_hectare",
        "annual_only",
        "loaded_as_annual_to_monthly_hold_constant",
        "Official wheat yield is annual in the local support store and is repeated monthly within the marketing year.",
    ),
    (
        "domestic_production",
        "annual_only",
        "loaded_as_annual_to_monthly_harvest_release_proxy",
        "Official wheat production is annual; monthly supply inflow is distributed using wheat harvest-release weights.",
    ),
    (
        "opening_stock",
        "mixed",
        "loaded_as_native_monthly_where_available_else_interpolated",
        "Actual DFPD monthly stock is used from 2023 onward, with annual balance-sheet interpolation for older months.",
    ),
    (
        "imports",
        "available",
        "loaded_as_native_monthly_series",
        "Monthly imports are loaded from the wheat demand DB which already caches TradeStat monthly import rows and proxy fallback for older uncovered months.",
    ),
    (
        "buffer_stock",
        "mixed",
        "loaded_as_native_monthly_where_available_else_interpolated",
        "Uses the same monthly stock backbone as opening stock for a public-stock cushion view.",
    ),
    (
        "usda_global_production",
        "partial",
        "loaded_as_usda_recent_years_plus_backfill",
        "2023/24-2025/26 come from USDA March 2026 wheat tables; earlier years are backfilled from 2023/24 levels to preserve a full 10-year monthly panel.",
    ),
    (
        "major_producer_crop_conditions",
        "curated",
        "loaded_as_recurring_monthly_profiles",
        "No single clean public 10-year monthly country-condition archive was loaded, so recurring monthly crop-condition profiles are used.",
    ),
    (
        "southern_hemisphere_harvest_calendar",
        "curated",
        "loaded_as_recurring_monthly_calendar",
        "Seasonal harvest-intensity calendar repeated across years.",
    ),
    (
        "total_demand_monthly",
        "derived",
        "loaded_from_wheat_demand_store",
        "Loaded from the wheat demand DB where total monthly demand is computed from additive demand components.",
    ),
    (
        "delta",
        "derived",
        "computed_from_total_availability_minus_total_demand",
        "Derived directly as total availability minus total demand monthly.",
    ),
    (
        "total_availability",
        "derived",
        "computed_from_monthly_supply_components",
        "Derived directly from monthly opening stock, domestic production inflow, and imports.",
    ),
]


SOURCE_INVENTORY = [
    (
        "wheat_support_db",
        "Local wheat support store",
        str(WHEAT_SUPPORT_DB),
        "annual / monthly",
        "Area, yield, production, and monthly DFPD stock rows already loaded into the wheat support DB.",
    ),
    (
        "dfpd",
        "Department of Food and Public Distribution",
        "https://dfpd.gov.in/",
        "monthly",
        "Public stock context source family.",
    ),
    (
        "tradestat",
        "DGCI&S TradeStat",
        "https://tradestat.commerce.gov.in/",
        "monthly",
        "Monthly trade source for wheat imports.",
    ),
    (
        "wheat_demand_db",
        "Local wheat demand store",
        str(WHEAT_DEMAND_DB),
        "monthly",
        "Used here as a local cache for monthly wheat imports sourced from TradeStat.",
    ),
    (
        "usda_wasde_psd",
        "USDA WASDE / PSD",
        "https://apps.fas.usda.gov/psdonline/circulars/grain.pdf",
        "monthly / annual",
        "Global wheat production and current India balance context.",
    ),
    (
        "curated_global_profiles",
        "Curated global crop-condition / harvest profiles",
        None,
        "monthly",
        "Used where no clean 10-year public monthly series was loaded.",
    ),
]


PRODUCTION_RELEASE_WEIGHTS = {
    4: 0.46,
    5: 0.31,
    6: 0.13,
    7: 0.06,
    8: 0.03,
    9: 0.01,
    10: 0.0,
    11: 0.0,
    12: 0.0,
    1: 0.0,
    2: 0.0,
    3: 0.0,
}


HARVEST_CALENDAR = {
    "Australia": {1: 95, 2: 75, 3: 30, 4: 10, 5: 5, 6: 5, 7: 5, 8: 10, 9: 20, 10: 40, 11: 80, 12: 100},
    "Argentina": {1: 85, 2: 65, 3: 25, 4: 10, 5: 5, 6: 5, 7: 5, 8: 10, 9: 20, 10: 45, 11: 85, 12: 100},
}


CROP_CONDITION_PROFILES = {
    "United States": {1: 46, 2: 47, 3: 48, 4: 52, 5: 58, 6: 61, 7: 57, 8: 54, 9: 52, 10: 50, 11: 48, 12: 47},
    "Australia": {1: 62, 2: 58, 3: 50, 4: 42, 5: 48, 6: 55, 7: 60, 8: 63, 9: 67, 10: 70, 11: 68, 12: 65},
    "Argentina": {1: 58, 2: 54, 3: 48, 4: 40, 5: 44, 6: 50, 7: 56, 8: 60, 9: 64, 10: 66, 11: 64, 12: 61},
    "European Union": {1: 52, 2: 53, 3: 55, 4: 58, 5: 62, 6: 64, 7: 60, 8: 57, 9: 55, 10: 54, 11: 53, 12: 52},
    "Russia": {1: 49, 2: 50, 3: 53, 4: 57, 5: 61, 6: 63, 7: 58, 8: 54, 9: 52, 10: 51, 11: 50, 12: 49},
    "Ukraine": {1: 47, 2: 48, 3: 50, 4: 54, 5: 59, 6: 61, 7: 56, 8: 52, 9: 50, 10: 49, 11: 48, 12: 47},
    "Canada": {1: 44, 2: 44, 3: 46, 4: 50, 5: 56, 6: 60, 7: 62, 8: 59, 9: 54, 10: 49, 11: 46, 12: 45},
}


INDIA_WHEAT_BALANCE_OVERRIDES = {
    "2025/26": {
        "Imports": 0.20,
        "Exports": 0.25,
        "Ending Stocks": 17.19,
    }
}


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").replace("\r", " ").replace("\n", " ").split())


def month_range(start: date, end: date) -> list[date]:
    current = date(start.year, start.month, 1)
    dates: list[date] = []
    while current <= end:
        dates.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return dates


def marketing_year_for_month(d: date) -> str:
    start_year = d.year if d.month >= 4 else d.year - 1
    return f"{start_year}/{str(start_year + 1)[-2:]}"


def indicator_marketing_year(indicator_date: str) -> str:
    parsed = datetime.fromisoformat(indicator_date).date()
    start_year = parsed.year - 1
    return f"{start_year}/{str(start_year + 1)[-2:]}"


def convert_to_million_tonnes(value: float, unit: str) -> float:
    normalized = normalize_text(unit).lower()
    if normalized in {"million_tonnes", "million tonnes", "mmt"}:
        return float(value)
    if normalized in {"lakh_tonnes", "lakh tonnes", "lmt"}:
        return float(value) * 0.1
    return float(value)


def load_demand_module() -> Any:
    spec = importlib.util.spec_from_file_location("wheat_demand_builder", WHEAT_DEMAND_BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load wheat demand builder module.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_annual_indicator_series(indicator_key: str) -> dict[str, tuple[float, str, str, str | None, str | None]]:
    result: dict[str, tuple[float, str, str, str | None, str | None]] = {}
    with sqlite3.connect(str(WHEAT_SUPPORT_DB)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT indicator_date, value, unit, source_name, source_url, notes
            FROM wheat_indicator_history
            WHERE indicator_key = ?
            ORDER BY indicator_date
            """,
            (indicator_key,),
        ).fetchall()
    for row in rows:
        my = indicator_marketing_year(str(row["indicator_date"]))
        if my < "2016/17":
            continue
        result[my] = (
            float(row["value"]),
            str(row["unit"]),
            str(row["source_name"]),
            row["source_url"],
            row["notes"],
        )
    return result


def load_monthly_stock_series() -> dict[str, tuple[float, str, str | None, str]]:
    result: dict[str, tuple[float, str, str | None, str]] = {}
    with sqlite3.connect(str(WHEAT_SUPPORT_DB)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT indicator_date, value, unit, source_name, source_url, notes
            FROM wheat_indicator_history
            WHERE indicator_key = 'government_buffer_wheat_stock'
            ORDER BY indicator_date
            """
        ).fetchall()
    for row in rows:
        metric_month = str(row["indicator_date"])
        value_mmt = round(convert_to_million_tonnes(float(row["value"]), str(row["unit"])), 6)
        result[metric_month] = (
            value_mmt,
            str(row["source_name"]),
            row["source_url"],
            row["notes"] or "Loaded from government monthly wheat stock bulletin.",
        )
    return result


def load_monthly_import_series() -> dict[str, tuple[float, str, str | None, str, str, str | None]]:
    result: dict[str, tuple[float, str, str | None, str, str, str | None]] = {}
    with sqlite3.connect(str(WHEAT_DEMAND_DB)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT metric_month, value, source_name, source_url, method, confidence, notes
            FROM factor_monthly_values
            WHERE factor_key = 'imports'
            ORDER BY metric_month
            """
        ).fetchall()
    for row in rows:
        result[str(row["metric_month"])] = (
            float(row["value"]),
            str(row["source_name"]),
            row["source_url"],
            str(row["method"]),
            str(row["confidence"]),
            row["notes"],
        )
    return result


def load_monthly_total_demand_series() -> dict[str, tuple[float, str, str | None, str, str, str | None]]:
    result: dict[str, tuple[float, str, str | None, str, str, str | None]] = {}
    with sqlite3.connect(str(WHEAT_DEMAND_DB)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT metric_month, value, source_name, source_url, method, confidence, notes
            FROM factor_monthly_values
            WHERE factor_key = 'total_demand_monthly'
            ORDER BY metric_month
            """
        ).fetchall()
    for row in rows:
        result[str(row["metric_month"])] = (
            float(row["value"]),
            str(row["source_name"]),
            row["source_url"],
            str(row["method"]),
            str(row["confidence"]),
            row["notes"],
        )
    return result


def load_cached_wasde_context() -> dict[str, dict[str, dict[str, float]]]:
    if not OUTPUT_DB.exists():
        return {}
    result: dict[str, dict[str, dict[str, float]]] = {}
    with sqlite3.connect(str(OUTPUT_DB)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT marketing_year, geography, value
            FROM factor_monthly_values
            WHERE factor_key = 'usda_global_production'
              AND marketing_year IN ('2023/24', '2024/25', '2025/26')
              AND metric_month LIKE '%-04-01'
            ORDER BY marketing_year, geography
            """
        ).fetchall()
    for row in rows:
        result.setdefault(str(row["marketing_year"]), {})[str(row["geography"])] = {"Production": float(row["value"])}
    return result
def fetch_wasde_wheat_context() -> dict[str, dict[str, dict[str, float]]]:
    try:
        xml_text = requests.get(WASDE_XML_URL, timeout=60).text
        root = ET.fromstring(xml_text)
    except Exception:
        cached = load_cached_wasde_context()
        if cached:
            return cached
        raise
    country_map = {
        "World 3/": "World",
        "Argentina": "Argentina",
        "Australia": "Australia",
        "Canada": "Canada",
        "European Union 5/": "European Union",
        "Russia": "Russia",
        "Ukraine": "Ukraine",
        "India": "India",
        "China": "China",
        "United States": "United States",
    }

    def parse_direct_matrix(
        matrix: ET.Element,
        region_attr: str,
        attr_group_collection_tag: str,
        attr_group_tag: str,
        attr_name_key: str,
        cell_value_key: str,
    ) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for region_group in matrix:
            region = normalize_text(region_group.attrib.get(region_attr))
            if region not in country_map:
                continue
            attrs: dict[str, float] = {}
            for attr in region_group.findall(f"./{attr_group_collection_tag}/{attr_group_tag}"):
                name = normalize_text(attr.attrib.get(attr_name_key))
                cell = attr.find(".//Cell")
                if cell is not None and cell.attrib.get(cell_value_key):
                    attrs[name] = float(cell.attrib[cell_value_key])
            out[country_map[region]] = attrs
        return out

    parsed: dict[str, dict[str, dict[str, float]]] = {}
    sr18 = root.find("./sr18/Report")
    sr19 = root.find("./sr19/Report")
    if sr18 is not None:
        matrix1 = sr18.find("./matrix1/m1_region_group_Collection")
        matrix2 = sr18.find("./matrix2/m2_region_group_Collection")
        if matrix1 is not None:
            parsed["2023/24"] = parse_direct_matrix(
                matrix1,
                "region1",
                "m1_attribute_group_Collection",
                "m1_attribute_group",
                "attribute1",
                "cell_value1",
            )
        if matrix2 is not None:
            parsed["2024/25"] = parse_direct_matrix(
                matrix2,
                "region2",
                "m2_attribute_group_Collection",
                "m2_attribute_group",
                "attribute2",
                "cell_value2",
            )
    if sr19 is not None:
        matrix1 = sr19.find("./matrix1/m1_region_group_Collection")
        if matrix1 is not None:
            projection: dict[str, dict[str, float]] = {}
            for region_group in matrix1.findall("./m1_region_group"):
                region = normalize_text(region_group.attrib.get("region1"))
                if region not in country_map:
                    continue
                march_group = None
                for month_group in region_group.findall("./m1_month_group_Collection/m1_month_group"):
                    if (month_group.attrib.get("forecast_month1") or "").strip() == "Mar":
                        march_group = month_group
                        break
                if march_group is None:
                    continue
                attrs: dict[str, float] = {}
                for attr in march_group.findall("./m1_attribute_group_Collection/m1_attribute_group"):
                    name = normalize_text(attr.attrib.get("attribute1"))
                    cell = attr.find(".//Cell")
                    if cell is not None and cell.attrib.get("cell_value1"):
                        attrs[name] = float(cell.attrib["cell_value1"])
                projection[country_map[region]] = attrs
            parsed["2025/26"] = projection
    return parsed


def build_annual_context() -> dict[str, Any]:
    demand_module = load_demand_module()
    annual_balance = dict(demand_module.ANNUAL_WHEAT)
    area_raw = load_annual_indicator_series("wheat_area")
    yield_raw = load_annual_indicator_series("wheat_yield_kg_per_hectare")
    production_raw = load_annual_indicator_series("wheat_production")
    wasde = fetch_wasde_wheat_context()

    area_by_my = {my: value for my, (value, *_rest) in area_raw.items() if my >= "2016/17"}
    yield_by_my = {my: value for my, (value, *_rest) in yield_raw.items() if my >= "2016/17"}
    production_by_my = {my: value for my, (value, *_rest) in production_raw.items() if my >= "2016/17"}

    current_my = "2025/26"
    if current_my in wasde and "India" in wasde[current_my]:
        india_attrs = wasde[current_my]["India"]
        production_by_my[current_my] = india_attrs.get("Production", production_by_my.get("2024/25", 117.9))
    latest_area = area_by_my.get("2024/25", max(area_by_my.values()))
    area_by_my[current_my] = latest_area
    yield_by_my[current_my] = round((production_by_my[current_my] / latest_area) * 1000.0, 3)

    imports_annual: dict[str, float] = {}
    ending_stock_annual: dict[str, float] = {}
    total_consumption_annual: dict[str, float] = {}
    exports_annual: dict[str, float] = {}
    for my, balance in annual_balance.items():
        if my < "2016/17":
            continue
        imports_annual[my] = float(balance.imports_mmt)
        ending_stock_annual[my] = float(balance.ending_stock_mmt)
        total_consumption_annual[my] = float(balance.total_consumption_mmt)
        exports_annual[my] = float(balance.exports_mmt)
    if current_my in wasde and "India" in wasde[current_my]:
        india_attrs = wasde[current_my]["India"]
        imports_annual[current_my] = india_attrs.get("Imports", imports_annual.get(current_my, 0.0))
        ending_stock_annual[current_my] = india_attrs.get("Ending Stocks", ending_stock_annual.get(current_my, 17.185))
        total_consumption_annual[current_my] = india_attrs.get("Domestic Total 2/", total_consumption_annual.get(current_my, 112.51))
        exports_annual[current_my] = india_attrs.get("Exports", exports_annual.get(current_my, 0.0))

    opening_stock_annual: dict[str, float] = {}
    for my, production in production_by_my.items():
        if my not in ending_stock_annual or my not in imports_annual or my not in total_consumption_annual or my not in exports_annual:
            continue
        opening_stock_annual[my] = round(
            ending_stock_annual[my] + total_consumption_annual[my] + exports_annual[my] - production - imports_annual[my],
            6,
        )

    return {
        "area": area_by_my,
        "yield": yield_by_my,
        "production": production_by_my,
        "imports_annual": imports_annual,
        "opening_stock_annual": opening_stock_annual,
        "ending_stock_annual": ending_stock_annual,
        "wasde": wasde,
        "area_meta": area_raw,
        "yield_meta": yield_raw,
        "production_meta": production_raw,
    }


def interpolate_stock_for_month(metric_month: date, opening_stock_annual: dict[str, float], ending_stock_annual: dict[str, float]) -> float:
    my = marketing_year_for_month(metric_month)
    opening = opening_stock_annual[my]
    ending = ending_stock_annual[my]
    month_order = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
    month_idx = month_order.index(metric_month.month)
    fraction = month_idx / 11.0
    return round(opening + ((ending - opening) * fraction), 6)


def build_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS factor_definitions (
            factor_key TEXT PRIMARY KEY,
            factor_name TEXT NOT NULL,
            geography_scope TEXT NOT NULL,
            factor_group TEXT NOT NULL,
            default_unit TEXT NOT NULL,
            description TEXT NOT NULL,
            why_it_matters TEXT NOT NULL,
            priority TEXT NOT NULL,
            loading_note TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS source_inventory (
            source_key TEXT PRIMARY KEY,
            source_name TEXT NOT NULL,
            source_url TEXT,
            cadence TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS factor_status (
            factor_key TEXT PRIMARY KEY,
            monthly_source_status TEXT NOT NULL,
            current_load_mode TEXT NOT NULL,
            notes TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS factor_monthly_values (
            id TEXT PRIMARY KEY,
            factor_key TEXT NOT NULL,
            metric_month TEXT NOT NULL,
            marketing_year TEXT NOT NULL,
            geography TEXT NOT NULL DEFAULT 'India',
            value REAL,
            unit TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            method TEXT NOT NULL,
            confidence TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(factor_key, metric_month, geography)
        );

        CREATE TABLE IF NOT EXISTS factor_values (
            id TEXT PRIMARY KEY,
            factor_key TEXT NOT NULL,
            metric_date TEXT NOT NULL,
            period_type TEXT NOT NULL,
            geography TEXT NOT NULL DEFAULT 'India',
            value REAL,
            unit TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            method TEXT NOT NULL,
            confidence TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(factor_key, metric_date, geography, period_type)
        );

        CREATE TABLE IF NOT EXISTS wheat_balance_sheet_annual (
            marketing_year TEXT PRIMARY KEY,
            opening_stock_mmt REAL NOT NULL,
            acreage_million_hectare REAL,
            yield_kg_per_hectare REAL,
            production_mmt REAL NOT NULL,
            imports_mmt REAL NOT NULL,
            food_use_mmt REAL NOT NULL,
            feed_use_mmt REAL NOT NULL,
            industrial_use_mmt REAL NOT NULL,
            exports_mmt REAL NOT NULL,
            total_use_mmt REAL NOT NULL,
            ending_stock_mmt REAL NOT NULL,
            reported_ending_stock_mmt REAL,
            stocks_to_use_ratio_pct REAL NOT NULL,
            row_type TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            method TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS wheat_balance_sheet_projection (
            marketing_year TEXT PRIMARY KEY,
            opening_stock_mmt REAL NOT NULL,
            acreage_million_hectare REAL,
            yield_kg_per_hectare REAL,
            production_mmt REAL NOT NULL,
            imports_mmt REAL NOT NULL,
            food_use_mmt REAL NOT NULL,
            feed_use_mmt REAL NOT NULL,
            industrial_use_mmt REAL NOT NULL,
            exports_mmt REAL NOT NULL,
            total_use_mmt REAL NOT NULL,
            ending_stock_mmt REAL NOT NULL,
            stocks_to_use_ratio_pct REAL NOT NULL,
            projection_method TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )


def upsert_reference_tables(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """
        INSERT INTO factor_definitions (
            factor_key, factor_name, geography_scope, factor_group,
            default_unit, description, why_it_matters, priority, loading_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(factor_key) DO UPDATE SET
            factor_name=excluded.factor_name,
            geography_scope=excluded.geography_scope,
            factor_group=excluded.factor_group,
            default_unit=excluded.default_unit,
            description=excluded.description,
            why_it_matters=excluded.why_it_matters,
            priority=excluded.priority,
            loading_note=excluded.loading_note
        """,
        SUPPLY_FACTORS,
    )
    conn.executemany(
        """
        INSERT INTO source_inventory (source_key, source_name, source_url, cadence, notes)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(source_key) DO UPDATE SET
            source_name=excluded.source_name,
            source_url=excluded.source_url,
            cadence=excluded.cadence,
            notes=excluded.notes
        """,
        SOURCE_INVENTORY,
    )
    conn.executemany(
        """
        INSERT INTO factor_status (factor_key, monthly_source_status, current_load_mode, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(factor_key) DO UPDATE SET
            monthly_source_status=excluded.monthly_source_status,
            current_load_mode=excluded.current_load_mode,
            notes=excluded.notes
        """,
        FACTOR_STATUS,
    )
def build_monthly_rows() -> list[tuple[Any, ...]]:
    months = month_range(START_MONTH, END_MONTH)
    annual_context = build_annual_context()
    stock_actual = load_monthly_stock_series()
    imports_monthly = load_monthly_import_series()
    total_demand_monthly = load_monthly_total_demand_series()
    wasde = annual_context["wasde"]
    area_meta = annual_context["area_meta"]
    yield_meta = annual_context["yield_meta"]
    production_meta = annual_context["production_meta"]

    rows: list[tuple[Any, ...]] = []
    production_monthly_cache: dict[str, float] = {}
    stock_monthly_cache: dict[str, float] = {}
    import_monthly_cache: dict[str, float] = {}
    total_demand_cache: dict[str, float] = {}

    for d in months:
        my = marketing_year_for_month(d)
        metric_month = d.isoformat()

        area_value = annual_context["area"][my]
        area_meta_row = area_meta.get(my, area_meta.get("2024/25"))
        area_source_name = area_meta_row[2] if area_meta_row else "Economic Survey Statistical Appendix"
        area_source_url = area_meta_row[3] if area_meta_row else None
        rows.append((f"area:{metric_month}:India", "acreage_sown_area", metric_month, my, "India", round(area_value, 6), "million_hectare", area_source_name, area_source_url, "annual_area_hold_constant_monthly", "high" if my != "2025/26" else "medium", f"Official annual wheat area held constant across the {my} marketing year for monthly supply context.", UPDATED_AT))

        yield_value = annual_context["yield"][my]
        yield_meta_row = yield_meta.get(my, yield_meta.get("2024/25"))
        yield_source_name = yield_meta_row[2] if yield_meta_row else "Economic Survey Statistical Appendix"
        yield_source_url = yield_meta_row[3] if yield_meta_row else None
        rows.append((f"yield:{metric_month}:India", "yield_per_hectare", metric_month, my, "India", round(yield_value, 6), "kg_per_hectare", yield_source_name, yield_source_url, "annual_yield_hold_constant_monthly", "high" if my != "2025/26" else "medium", f"Official annual wheat yield held constant across the {my} marketing year for monthly supply context.", UPDATED_AT))

        annual_production = annual_context["production"][my]
        production_value = round(annual_production * PRODUCTION_RELEASE_WEIGHTS[d.month], 6)
        production_meta_row = production_meta.get(my, production_meta.get("2024/25"))
        production_source_name = production_meta_row[2] if production_meta_row else "Economic Survey Statistical Appendix / USDA WASDE"
        production_source_url = production_meta_row[3] if production_meta_row else WASDE_XML_URL
        rows.append((f"production:{metric_month}:India", "domestic_production", metric_month, my, "India", production_value, "million_tonnes", production_source_name, production_source_url, "annual_production_to_monthly_harvest_release_proxy", "high" if my != "2025/26" else "medium", f"Monthly wheat supply inflow distributed from annual production for {my} using harvest-release weights.", UPDATED_AT))
        production_monthly_cache[metric_month] = production_value

        if metric_month in stock_actual:
            stock_value, stock_source_name, stock_source_url, stock_note = stock_actual[metric_month]
            stock_method = "dfpd_monthly_central_pool_stock"
            stock_confidence = "high"
        else:
            stock_value = interpolate_stock_for_month(d, annual_context["opening_stock_annual"], annual_context["ending_stock_annual"])
            stock_source_name = "USDA annual wheat balance + interpolation"
            stock_source_url = "https://apps.fas.usda.gov/psdonline/circulars/grain.pdf"
            stock_method = "annual_opening_to_ending_stock_interpolation"
            stock_confidence = "medium"
            stock_note = f"Interpolated monthly stock path for {my} from annual opening stock {annual_context['opening_stock_annual'][my]:.3f} MnT to ending stock {annual_context['ending_stock_annual'][my]:.3f} MnT."
        rows.append((f"opening_stock:{metric_month}:India", "opening_stock", metric_month, my, "India", stock_value, "million_tonnes", stock_source_name, stock_source_url, stock_method, stock_confidence, stock_note, UPDATED_AT))
        rows.append((f"buffer_stock:{metric_month}:India", "buffer_stock", metric_month, my, "India", stock_value, "million_tonnes", stock_source_name, stock_source_url, stock_method, stock_confidence, stock_note, UPDATED_AT))
        stock_monthly_cache[metric_month] = stock_value

        import_value, import_source_name, import_source_url, import_method, import_confidence, import_notes = imports_monthly[metric_month]
        rows.append((f"imports:{metric_month}:India", "imports", metric_month, my, "India", round(import_value, 6), "million_tonnes", import_source_name, import_source_url, f"supply_store_from_{import_method}", import_confidence, import_notes, UPDATED_AT))
        import_monthly_cache[metric_month] = round(import_value, 6)

        demand_value, demand_source_name, demand_source_url, demand_method, demand_confidence, demand_notes = total_demand_monthly[metric_month]
        rows.append((f"total_demand:{metric_month}:India", "total_demand_monthly", metric_month, my, "India", round(demand_value, 6), "million_tonnes", demand_source_name, demand_source_url, f"supply_store_from_{demand_method}", demand_confidence, demand_notes, UPDATED_AT))
        total_demand_cache[metric_month] = round(demand_value, 6)

    target_countries = ["World", "Argentina", "Australia", "Canada", "European Union", "Russia", "Ukraine", "India", "China", "United States"]
    for d in months:
        my = marketing_year_for_month(d)
        metric_month = d.isoformat()
        for geography in target_countries:
            if my in wasde and geography in wasde[my]:
                attrs = wasde[my][geography]
                production_value = attrs.get("Production")
                method = "usda_wasde_marketing_year_hold_constant_monthly"
                confidence = "high"
                note = f"USDA wheat production for {geography} in {my}, held constant across months of that marketing year."
            else:
                attrs = wasde.get("2023/24", {}).get(geography, {})
                production_value = attrs.get("Production")
                method = "backfilled_from_2023_24_usda_snapshot"
                confidence = "low"
                note = f"Historical monthly backfill for {geography} before USDA-loaded years, anchored to 2023/24 wheat production."
            if production_value is None:
                continue
            rows.append((f"global_production:{metric_month}:{geography}", "usda_global_production", metric_month, my, geography, round(float(production_value), 6), "million_tonnes", "USDA WASDE March 2026", WASDE_XML_URL, method, confidence, note, UPDATED_AT))

    for geography, profile in CROP_CONDITION_PROFILES.items():
        for d in months:
            metric_month = d.isoformat()
            my = marketing_year_for_month(d)
            rows.append((f"crop_condition:{metric_month}:{geography}", "major_producer_crop_conditions", metric_month, my, geography, float(profile[d.month]), "index", "Curated global crop-condition profile", None, "recurring_monthly_crop_condition_profile", "medium", f"Recurring monthly crop-condition profile for {geography}.", UPDATED_AT))

    for geography, profile in HARVEST_CALENDAR.items():
        for d in months:
            metric_month = d.isoformat()
            my = marketing_year_for_month(d)
            rows.append((f"harvest_calendar:{metric_month}:{geography}", "southern_hemisphere_harvest_calendar", metric_month, my, geography, float(profile[d.month]), "index", "Curated Southern Hemisphere wheat harvest calendar", None, "recurring_monthly_harvest_calendar", "medium", f"Seasonal harvest-intensity index for {geography}; higher values mean fresher exportable wheat supply is entering the market.", UPDATED_AT))

    for d in months:
        metric_month = d.isoformat()
        my = marketing_year_for_month(d)
        total_availability = round(stock_monthly_cache[metric_month] + production_monthly_cache[metric_month] + import_monthly_cache[metric_month], 6)
        rows.append((f"total_availability:{metric_month}:India", "total_availability", metric_month, my, "India", total_availability, "million_tonnes", "Derived inside wheat supply store", None, "opening_stock_plus_domestic_production_plus_imports", "high", f"Computed as {stock_monthly_cache[metric_month]:.3f} opening stock + {production_monthly_cache[metric_month]:.3f} domestic production inflow + {import_monthly_cache[metric_month]:.3f} imports.", UPDATED_AT))
        delta_value = round(total_availability - total_demand_cache[metric_month], 6)
        rows.append((f"delta:{metric_month}:India", "delta", metric_month, my, "India", delta_value, "million_tonnes", "Derived inside wheat supply store", None, "total_availability_minus_total_demand_monthly", "high", f"Computed as {total_availability:.3f} total availability - {total_demand_cache[metric_month]:.3f} total demand monthly.", UPDATED_AT))

    return rows


def build_snapshot_rows(monthly_rows: list[tuple[Any, ...]]) -> list[tuple[Any, ...]]:
    latest: dict[tuple[str, str], tuple[Any, ...]] = {}
    for row in monthly_rows:
        factor_key = row[1]
        metric_month = row[2]
        geography = row[4]
        current = latest.get((factor_key, geography))
        if current is None or metric_month > current[2]:
            latest[(factor_key, geography)] = row
    snapshot_rows: list[tuple[Any, ...]] = []
    for row in latest.values():
        snapshot_rows.append((f"{row[1]}:{row[2]}:{row[4]}:snapshot", row[1], row[2], "monthly_snapshot", row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12]))
    return snapshot_rows


def compute_growth(values: list[float], default: float = 0.0, minimum: float = -0.05, maximum: float = 0.05) -> float:
    growths: list[float] = []
    for previous, current in zip(values, values[1:]):
        if previous and previous > 0:
            growths.append((current / previous) - 1.0)
    if not growths:
        return default
    return max(min(sum(growths) / len(growths), maximum), minimum)


def build_annual_balance_tables() -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    annual_context = build_annual_context()
    demand_module = load_demand_module()
    annual_balance = dict(demand_module.ANNUAL_WHEAT)

    actual_rows: list[tuple[Any, ...]] = []
    annual_state: dict[str, dict[str, float]] = {}
    marketing_years = sorted(annual_balance.keys())

    for marketing_year in marketing_years:
        balance = annual_balance[marketing_year]
        india_wasde_attrs = annual_context["wasde"].get(marketing_year, {}).get("India", {})
        india_override = INDIA_WHEAT_BALANCE_OVERRIDES.get(marketing_year, {})
        opening_stock = round(annual_context["opening_stock_annual"][marketing_year], 6)
        acreage = round(annual_context["area"][marketing_year], 6)
        yield_value = round(annual_context["yield"][marketing_year], 6)
        production = round(annual_context["production"][marketing_year], 6)
        imports = round(india_wasde_attrs.get("Imports", india_override.get("Imports", balance.imports_mmt)), 6)
        feed_use = round(balance.feed_residual_mmt, 6)
        industrial_use = round(balance.fsi_consumption_mmt * 0.062, 6)
        food_use = round(balance.total_consumption_mmt - balance.feed_residual_mmt - industrial_use, 6)
        exports = round(india_wasde_attrs.get("Exports", india_override.get("Exports", balance.exports_mmt)), 6)
        total_use = round(food_use + feed_use + industrial_use + exports, 6)
        ending_stock = round(opening_stock + production + imports - total_use, 6)
        reported_ending = round(india_wasde_attrs.get("Ending Stocks", india_override.get("Ending Stocks", balance.ending_stock_mmt)), 6)
        stocks_to_use_ratio = round((ending_stock / total_use) * 100.0, 6) if total_use else 0.0
        note = (
            "Food use is derived as total consumption minus feed and industrial use, so it absorbs the seed component "
            "needed to keep the annual balance sheet closed against official ending stock."
        )

        actual_rows.append(
            (
                marketing_year,
                opening_stock,
                acreage,
                yield_value,
                production,
                imports,
                food_use,
                feed_use,
                industrial_use,
                exports,
                total_use,
                ending_stock,
                reported_ending,
                stocks_to_use_ratio,
                "actual",
                balance.source_name,
                balance.source_url,
                "opening_plus_production_plus_imports_minus_food_feed_industrial_exports",
                note,
                UPDATED_AT,
            )
        )
        annual_state[marketing_year] = {
            "opening_stock": opening_stock,
            "acreage": acreage,
            "yield": yield_value,
            "production": production,
            "imports": imports,
            "food_use": food_use,
            "feed_use": feed_use,
            "industrial_use": industrial_use,
            "exports": exports,
            "total_use": total_use,
            "ending_stock": ending_stock,
            "stocks_to_use_ratio": stocks_to_use_ratio,
        }

    recent_years = marketing_years[-5:]
    area_growth = compute_growth([annual_state[year]["acreage"] for year in recent_years], default=0.002, minimum=-0.01, maximum=0.02)
    yield_growth = compute_growth([annual_state[year]["yield"] for year in recent_years], default=0.005, minimum=-0.01, maximum=0.025)
    food_growth = compute_growth([annual_state[year]["food_use"] for year in recent_years], default=0.01, minimum=0.0, maximum=0.03)
    feed_growth = compute_growth([annual_state[year]["feed_use"] for year in recent_years], default=0.005, minimum=-0.02, maximum=0.03)
    industrial_growth = compute_growth([annual_state[year]["industrial_use"] for year in recent_years], default=0.008, minimum=0.0, maximum=0.02)
    exports_growth = compute_growth([annual_state[year]["exports"] for year in recent_years], default=0.0, minimum=-0.5, maximum=0.5)
    target_ratio = sum(annual_state[year]["stocks_to_use_ratio"] for year in marketing_years[-3:]) / 3.0

    projection_rows: list[tuple[Any, ...]] = []
    previous_key = marketing_years[-1]
    previous_state = annual_state[previous_key].copy()
    start_year = int(previous_key.split("/")[0]) + 1

    for offset in range(3):
        start = start_year + offset
        end = str(start + 1)[-2:]
        marketing_year = f"{start}/{end}"
        opening_stock = round(previous_state["ending_stock"], 6)
        acreage = round(previous_state["acreage"] * (1.0 + area_growth), 6)
        yield_value = round(previous_state["yield"] * (1.0 + yield_growth), 6)
        production = round((acreage * yield_value) / 1000.0, 6)
        food_use = round(previous_state["food_use"] * (1.0 + food_growth), 6)
        feed_use = round(previous_state["feed_use"] * (1.0 + feed_growth), 6)
        industrial_use = round(previous_state["industrial_use"] * (1.0 + industrial_growth), 6)
        exports = round(max(0.0, previous_state["exports"] * (1.0 + exports_growth)), 6)
        total_use = round(food_use + feed_use + industrial_use + exports, 6)
        target_ending_stock = round((target_ratio / 100.0) * total_use, 6)
        imports = round(max(0.0, target_ending_stock + total_use - opening_stock - production), 6)
        ending_stock = round(opening_stock + production + imports - total_use, 6)
        stocks_to_use_ratio = round((ending_stock / total_use) * 100.0, 6) if total_use else 0.0

        projection_rows.append(
            (
                marketing_year,
                opening_stock,
                acreage,
                yield_value,
                production,
                imports,
                food_use,
                feed_use,
                industrial_use,
                exports,
                total_use,
                ending_stock,
                stocks_to_use_ratio,
                "recent_5y_growth_with_target_stock_to_use",
                (
                    f"Projected from recent 5-year average growth in area/yield/use. Imports are solved endogenously to "
                    f"target an average stocks-to-use ratio of {target_ratio:.2f}% where needed."
                ),
                UPDATED_AT,
            )
        )
        previous_state = {
            "ending_stock": ending_stock,
            "acreage": acreage,
            "yield": yield_value,
            "food_use": food_use,
            "feed_use": feed_use,
            "industrial_use": industrial_use,
            "exports": exports,
        }

    return actual_rows, projection_rows


def build_db() -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    monthly_rows = build_monthly_rows()
    snapshot_rows = build_snapshot_rows(monthly_rows)
    actual_balance_rows, projection_balance_rows = build_annual_balance_tables()
    with sqlite3.connect(str(OUTPUT_DB)) as conn:
        build_schema(conn)
        upsert_reference_tables(conn)
        conn.execute("DELETE FROM factor_monthly_values")
        conn.execute("DELETE FROM factor_values")
        conn.execute("DELETE FROM wheat_balance_sheet_annual")
        conn.execute("DELETE FROM wheat_balance_sheet_projection")
        conn.executemany("""
            INSERT INTO factor_monthly_values (
                id, factor_key, metric_month, marketing_year, geography, value, unit,
                source_name, source_url, method, confidence, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, monthly_rows)
        conn.executemany("""
            INSERT INTO factor_values (
                id, factor_key, metric_date, period_type, geography, value, unit,
                source_name, source_url, method, confidence, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, snapshot_rows)
        conn.executemany(
            """
            INSERT INTO wheat_balance_sheet_annual (
                marketing_year, opening_stock_mmt, acreage_million_hectare, yield_kg_per_hectare,
                production_mmt, imports_mmt, food_use_mmt, feed_use_mmt, industrial_use_mmt,
                exports_mmt, total_use_mmt, ending_stock_mmt, reported_ending_stock_mmt,
                stocks_to_use_ratio_pct, row_type, source_name, source_url, method, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            actual_balance_rows,
        )
        conn.executemany(
            """
            INSERT INTO wheat_balance_sheet_projection (
                marketing_year, opening_stock_mmt, acreage_million_hectare, yield_kg_per_hectare,
                production_mmt, imports_mmt, food_use_mmt, feed_use_mmt, industrial_use_mmt,
                exports_mmt, total_use_mmt, ending_stock_mmt, stocks_to_use_ratio_pct,
                projection_method, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            projection_balance_rows,
        )
        summary = conn.execute("SELECT COUNT(*), MIN(metric_month), MAX(metric_month) FROM factor_monthly_values").fetchone()
        factor_counts = conn.execute("SELECT factor_key, COUNT(*) FROM factor_monthly_values GROUP BY factor_key ORDER BY factor_key").fetchall()
        annual_balance_count = conn.execute("SELECT COUNT(*) FROM wheat_balance_sheet_annual").fetchone()[0]
        projection_balance_count = conn.execute("SELECT COUNT(*) FROM wheat_balance_sheet_projection").fetchone()[0]
        conn.commit()

    return {
        "status": "success",
        "db_path": str(OUTPUT_DB),
        "rows_written": int(summary[0]),
        "from": summary[1],
        "to": summary[2],
        "factor_counts": {row[0]: row[1] for row in factor_counts},
        "annual_balance_rows": annual_balance_count,
        "projection_rows": projection_balance_count,
        "formula": "Total Availability = Opening Stock + Domestic Production + Imports",
        "updated_at": UPDATED_AT,
    }


if __name__ == "__main__":
    print(json.dumps(build_db(), indent=2))
