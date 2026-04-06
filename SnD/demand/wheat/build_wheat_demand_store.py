from __future__ import annotations

import json
import math
import sqlite3
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / "wheat_demand_monthly.db"
AGMARKNET_DB = ROOT / "agmarknet_history_local.db"
WORLD_BANK_POP_URL = "https://api.worldbank.org/v2/country/IND/indicator/SP.POP.TOTL?format=json&per_page=100"
TRADESTAT_EXPORT_URL = "https://tradestat.commerce.gov.in/meidb/commodity_wise_all_countries_export"
TRADESTAT_IMPORT_URL = "https://tradestat.commerce.gov.in/meidb/commodity_wise_all_countries_import"
UPDATED_AT = datetime.utcnow().isoformat() + "Z"
FALLBACK_POPULATION_MILLIONS = {
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
}


@dataclass(frozen=True)
class AnnualWheatBalance:
    marketing_year: str
    total_consumption_mmt: float
    fsi_consumption_mmt: float
    feed_residual_mmt: float
    imports_mmt: float
    exports_mmt: float
    ending_stock_mmt: float
    source_name: str
    source_url: str


ANNUAL_WHEAT = {
    "2016/17": AnnualWheatBalance(
        "2016/17", 97.120, 92.420, 4.700, 5.896, 0.516, 9.800,
        "USDA GAIN India Grain Voluntary Update (October 2017)",
        "https://gain.fas.usda.gov/Recent%20GAIN%20Publications/India%20Grain%20Voluntary%20Update%20-%20October%202017_New%20Delhi_India_10-3-2017.pdf",
    ),
    "2017/18": AnnualWheatBalance(
        "2017/18", 95.677, 90.677, 5.000, 3.000, 0.500, 13.344,
        "USDA GAIN India Grain Quarterly Update (November 2019)",
        "https://apps.fas.usda.gov/newgainapi/api/Report/DownloadReportByFileName?fileName=Grain+and+Feed+Quarterly+Update-November+2019_New+Delhi_India_10-30-2019.pdf",
    ),
    "2018/19": AnnualWheatBalance(
        "2018/19", 95.629, 90.629, 5.000, 0.017, 0.496, 17.106,
        "USDA GAIN India Grain Quarterly Update (November 2019)",
        "https://apps.fas.usda.gov/newgainapi/api/Report/DownloadReportByFileName?fileName=Grain+and+Feed+Quarterly+Update-November+2019_New+Delhi_India_10-30-2019.pdf",
    ),
    "2019/20": AnnualWheatBalance(
        "2019/20", 95.409, 89.409, 6.000, 0.020, 0.509, 24.700,
        "USDA GAIN India Grain and Feed Update (July 2021)",
        "https://apps.fas.usda.gov/newgainapi/api/Report/DownloadReportByFileName?fileName=Grain+and+Feed+Update_New+Delhi_India_07-15-2021.pdf",
    ),
    "2020/21": AnnualWheatBalance(
        "2020/21", 102.885, 96.385, 6.500, 0.025, 2.400, 27.300,
        "USDA GAIN India Grain and Feed Update (July 2021)",
        "https://apps.fas.usda.gov/newgainapi/api/Report/DownloadReportByFileName?fileName=Grain+and+Feed+Update_New+Delhi_India_07-15-2021.pdf",
    ),
    "2021/22": AnnualWheatBalance(
        "2021/22", 105.000, 98.000, 7.000, 0.025, 2.500, 27.825,
        "USDA GAIN India Grain and Feed Update (July 2021)",
        "https://apps.fas.usda.gov/newgainapi/api/Report/DownloadReportByFileName?fileName=Grain+and+Feed+Update_New+Delhi_India_07-15-2021.pdf",
    ),
    "2022/23": AnnualWheatBalance(
        "2022/23", 108.665, 102.365, 6.300, 0.000, 0.000, 9.500,
        "USDA FAS Grain Circular (March 2026) + derived feed/FSI split",
        "https://apps.fas.usda.gov/psdonline/circulars/grain.pdf",
    ),
    "2023/24": AnnualWheatBalance(
        "2023/24", 112.342, 105.792, 6.550, 0.000, 0.000, 7.500,
        "USDA FAS Grain Circular (March 2026) + derived feed/FSI split",
        "https://apps.fas.usda.gov/psdonline/circulars/grain.pdf",
    ),
    "2024/25": AnnualWheatBalance(
        "2024/25", 108.961, 102.611, 6.350, 0.000, 0.000, 11.800,
        "USDA FAS Grain Circular (March 2026) + derived feed/FSI split",
        "https://apps.fas.usda.gov/psdonline/circulars/grain.pdf",
    ),
    "2025/26": AnnualWheatBalance(
        "2025/26", 112.510, 105.950, 6.560, 0.000, 0.000, 17.185,
        "USDA FAS Grain Circular (March 2026) + derived feed/FSI split",
        "https://apps.fas.usda.gov/psdonline/circulars/grain.pdf",
    ),
}


FACTOR_DEFINITIONS = [
    ("domestic_consumption", "Domestic consumption", "Total wheat used for food consumption.", "main demand driver", "million_tonnes"),
    ("pds_government_offtake", "PDS / government offtake", "Wheat lifted through public distribution and welfare schemes.", "strong institutional demand", "million_tonnes"),
    ("open_market_sales_release", "Open market sales / government release", "Government wheat sold into the market.", "reduces net demand pressure on private markets", "policy_index"),
    ("private_trade_demand", "Private trade demand", "Flour mills, atta makers, processors, wholesalers.", "core commercial demand", "million_tonnes"),
    ("exports", "Exports", "Wheat sent outside India.", "adds external demand", "million_tonnes"),
    ("feed_use", "Feed use", "Wheat used for animal feed when substitutes are expensive.", "can raise demand unexpectedly", "million_tonnes"),
    ("seed_use", "Seed use", "Wheat kept aside for sowing.", "seasonal but important", "million_tonnes"),
    ("industrial_use", "Industrial use", "Starch, processed foods, other industrial consumption.", "non-food demand layer", "million_tonnes"),
    ("private_stock_build", "Stock build by private players", "Traders and millers holding inventory.", "increases short-term demand pull", "million_tonnes"),
    ("substitution_effect", "Substitution effect", "Switching between wheat, rice, maize, etc.", "changes demand depending on relative prices", "index_100"),
    ("population_trend", "Population / consumption trend", "Structural growth in demand.", "useful for baseline demand trend", "million_people"),
    ("festival_seasonal_demand", "Festival / seasonal demand", "Higher consumption in certain months.", "monthly demand variation", "index_100"),
    ("retail_price_cpi_wheat_pressure", "Retail price / CPI wheat pressure", "Consumer price changes affecting demand behavior.", "helps explain softening or tightening", "index_100"),
    ("imports", "Imports", "Imported wheat entering domestic system.", "changes availability and suppresses demand pressure", "million_tonnes"),
    ("policy_changes", "Policy changes", "Export bans, stock limits, OMSS, procurement policy.", "can sharply change effective demand", "policy_index"),
    ("total_demand_monthly", "Total demand monthly", "Total additive monthly wheat demand used for S&D balance.", "core balance-sheet demand total", "million_tonnes"),
]

FACTOR_STATUS = [
    ("domestic_consumption", "not_found_cleanly", "loaded_as_annual_to_monthly_proxy", "USDA annual FSI/total consumption exists, but no clean public monthly India wheat food-consumption series was found."),
    ("pds_government_offtake", "partially_available", "loaded_as_annual_to_monthly_proxy", "Monthly offtake exists in DFPD bulletins, but a clean normalized 10-year machine-readable series was not assembled in this pass."),
    ("open_market_sales_release", "partially_available", "loaded_as_event_monthly_series", "Policy / OMSS releases exist as circulars and notices, so this factor is currently loaded as a monthly policy-event score."),
    ("private_trade_demand", "not_found_cleanly", "loaded_as_annual_to_monthly_proxy", "No direct monthly official private-trade demand series was found; this factor is modeled as residual demand."),
    ("exports", "available", "loaded_as_native_monthly_series_where_available_else_proxy", "TradeStat monthly export data is loaded where the portal returns a month-level total; older uncovered months retain the annual proxy."),
    ("feed_use", "not_found_cleanly", "loaded_as_annual_to_monthly_proxy", "Only annual feed/residual values were available from USDA PSD-style tables."),
    ("seed_use", "not_found_cleanly", "loaded_as_annual_to_monthly_proxy", "No official 10-year monthly public seed-use series was found."),
    ("industrial_use", "not_found_cleanly", "loaded_as_annual_to_monthly_proxy", "No clean monthly public industrial-use series was found."),
    ("private_stock_build", "not_found_cleanly", "loaded_as_annual_to_monthly_proxy", "Private inventory build is not published as a clean monthly official series."),
    ("substitution_effect", "available", "loaded_as_native_monthly_series", "Built directly from monthly AGMARKNET wheat/rice/maize price relationships."),
    ("population_trend", "annual_only", "loaded_as_annual_to_monthly_interpolation", "Population is annual in source and is interpolated smoothly into monthly values."),
    ("festival_seasonal_demand", "available", "loaded_as_curated_monthly_series", "Loaded as a fixed monthly seasonal calendar index."),
    ("retail_price_cpi_wheat_pressure", "available", "loaded_as_native_monthly_series", "Built directly from monthly wheat mandi price movements as a pressure index until a longer clean wheat CPI component series is loaded."),
    ("imports", "available", "loaded_as_native_monthly_series_where_available_else_proxy", "TradeStat monthly import data is loaded where the portal returns a month-level total; older uncovered months retain the annual proxy."),
    ("policy_changes", "available", "loaded_as_event_monthly_series", "Loaded from tracked monthly wheat-policy shock dates."),
    ("total_demand_monthly", "derived", "computed_from_monthly_demand_components", "Derived as domestic consumption + exports + feed use + seed use + industrial use + private stock build. PDS and private-trade rows are explanatory splits of domestic consumption and are not added again."),
]


CONSUMPTION_WEIGHTS = {
    1: 0.090, 2: 0.088, 3: 0.088, 4: 0.078, 5: 0.077, 6: 0.077,
    7: 0.079, 8: 0.081, 9: 0.082, 10: 0.084, 11: 0.086, 12: 0.090,
}
SEED_WEIGHTS = {
    1: 0.01, 2: 0.01, 3: 0.00, 4: 0.02, 5: 0.02, 6: 0.02,
    7: 0.03, 8: 0.03, 9: 0.03, 10: 0.28, 11: 0.32, 12: 0.23,
}
TRADE_WEIGHTS = {
    1: 0.070, 2: 0.075, 3: 0.080, 4: 0.085, 5: 0.085, 6: 0.085,
    7: 0.090, 8: 0.090, 9: 0.085, 10: 0.085, 11: 0.085, 12: 0.085,
}
IMPORT_WEIGHTS = {
    1: 0.06, 2: 0.06, 3: 0.07, 4: 0.08, 5: 0.08, 6: 0.08,
    7: 0.10, 8: 0.11, 9: 0.11, 10: 0.09, 11: 0.08, 12: 0.08,
}


POLICY_EVENTS = {
    "2021-04": {"policy_changes": 60.0, "open_market_sales_release": 75.0, "notes": "OMSS reserve price policy announced for 2021/22."},
    "2022-05": {"policy_changes": 95.0, "open_market_sales_release": 20.0, "notes": "Wheat export ban period begins; market regime shifts sharply."},
    "2023-06": {"policy_changes": 82.0, "open_market_sales_release": 15.0, "notes": "Wheat stock limits tightened on traders and processors."},
    "2024-06": {"policy_changes": 76.0, "open_market_sales_release": 18.0, "notes": "Wheat stock limits extended / reimposed to manage prices."},
}


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


def fetch_population_series() -> dict[int, float]:
    try:
        with urllib.request.urlopen(WORLD_BANK_POP_URL, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rows = payload[1]
        result: dict[int, float] = {}
        for row in rows:
            year = int(row["date"])
            value = row["value"]
            if 2015 <= year <= 2025 and value is not None:
                result[year] = float(value) / 1_000_000.0
        if len(result) >= 2:
            return result
    except Exception:
        pass
    return FALLBACK_POPULATION_MILLIONS.copy()


def interpolate_population_monthly(months: list[date], annual_population: dict[int, float]) -> dict[str, float]:
    values: dict[str, float] = {}
    for d in months:
        year_start = annual_population.get(d.year)
        next_year = annual_population.get(d.year + 1, year_start)
        if year_start is None:
            fallback_year = max(y for y in annual_population if y <= d.year)
            year_start = annual_population[fallback_year]
            next_year = annual_population.get(fallback_year + 1, year_start)
        fraction = (d.month - 1) / 12.0
        values[d.isoformat()] = year_start + ((next_year - year_start) * fraction)
    return values


def load_monthly_price_ratios() -> tuple[dict[str, float], dict[str, float]]:
    if not AGMARKNET_DB.exists():
        return {}, {}
    query = """
        WITH monthly AS (
            SELECT
                substr(date, 1, 7) AS ym,
                commodity,
                SUM(modal_price * CASE WHEN arrival_quantity > 0 THEN arrival_quantity ELSE 1 END) /
                SUM(CASE WHEN arrival_quantity > 0 THEN arrival_quantity ELSE 1 END) AS weighted_price
            FROM market_price_data
            WHERE commodity IN ('Wheat', 'Rice', 'Maize')
            GROUP BY substr(date, 1, 7), commodity
        )
        SELECT ym, commodity, weighted_price
        FROM monthly
    """
    with sqlite3.connect(str(AGMARKNET_DB)) as conn:
        rows = conn.execute(query).fetchall()
    by_month: dict[str, dict[str, float]] = {}
    for ym, commodity, price in rows:
        by_month.setdefault(str(ym), {})[str(commodity)] = float(price)

    raw_ratios: dict[str, float] = {}
    wheat_index_raw: dict[str, float] = {}
    for ym, values in by_month.items():
        if all(k in values for k in ("Wheat", "Rice", "Maize")):
            peer = (values["Rice"] + values["Maize"]) / 2.0
            if peer:
                raw_ratios[ym] = values["Wheat"] / peer
        if "Wheat" in values:
            wheat_index_raw[ym] = values["Wheat"]

    if raw_ratios:
        ratio_baseline = sum(raw_ratios.values()) / len(raw_ratios)
        substitution_index = {ym: (value / ratio_baseline) * 100.0 for ym, value in raw_ratios.items()}
    else:
        substitution_index = {}

    if wheat_index_raw:
        wheat_baseline = sum(wheat_index_raw.values()) / len(wheat_index_raw)
        price_pressure_index = {ym: (value / wheat_baseline) * 100.0 for ym, value in wheat_index_raw.items()}
    else:
        price_pressure_index = {}

    return substitution_index, price_pressure_index


def fetch_tradestat_monthly(kind: str) -> dict[str, float]:
    if kind not in {"export", "import"}:
        raise ValueError(f"Unsupported TradeStat kind: {kind}")

    url = TRADESTAT_EXPORT_URL if kind == "export" else TRADESTAT_IMPORT_URL
    field_prefix = "cwacex" if kind == "export" else "cwacim"
    session = requests.Session()

    data: dict[str, float] = {}
    current_year = datetime.now().year
    for year in range(2018, current_year + 1):
        max_month = 12 if year < current_year else min(datetime.now().month, 12)
        for month in range(1, max_month + 1):
            html = session.get(url, timeout=30).text
            soup = BeautifulSoup(html, "html.parser")
            csrf = soup.find("input", {"name": "_token"})
            if not csrf:
                continue
            payload = {
                "_token": csrf.get("value"),
                f"{field_prefix}HSCODE": "1001",
                f"{field_prefix}Month": str(month),
                f"{field_prefix}Year": str(year),
                f"{field_prefix}ReportVal": "3",
                f"{field_prefix}ReportYear": "2",
            }
            response = session.post(url, data=payload, timeout=60)
            if response.status_code == 419:
                html = session.get(url, timeout=30).text
                soup = BeautifulSoup(html, "html.parser")
                csrf = soup.find("input", {"name": "_token"})
                if not csrf:
                    continue
                payload["_token"] = csrf.get("value")
                response = session.post(url, data=payload, timeout=60)
            response.raise_for_status()
            table = BeautifulSoup(response.text, "html.parser").find("table", {"id": "example1"})
            if table is None:
                continue
            rows = table.find_all("tr")
            if not rows:
                continue
            header = [cell.get_text(" ", strip=True) for cell in rows[0].find_all(["th", "td"])]
            total_row = None
            for row in rows[1:]:
                cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
                if len(cells) >= 4 and cells[1].strip().lower() == "total":
                    total_row = cells
                    break
            if not total_row:
                continue
            current_column_index = None
            for idx, column_name in enumerate(header):
                normalized = " ".join(column_name.split()).lower()
                if f"{date(year, month, 1).strftime('%b').lower()}-{year}".lower() in normalized:
                    current_column_index = idx
                    break
            if current_column_index is None:
                continue
            raw_value = total_row[current_column_index].replace(",", "").strip()
            try:
                thousand_tonnes = float(raw_value)
            except ValueError:
                continue
            metric_month = date(year, month, 1).isoformat()
            data[metric_month] = round(thousand_tonnes / 1000.0, 6)
    return data


def normalize(weights: dict[int, float]) -> dict[int, float]:
    total = sum(weights.values()) or 1.0
    return {month: value / total for month, value in weights.items()}


CONSUMPTION_WEIGHTS = normalize(CONSUMPTION_WEIGHTS)
SEED_WEIGHTS = normalize(SEED_WEIGHTS)
TRADE_WEIGHTS = normalize(TRADE_WEIGHTS)
IMPORT_WEIGHTS = normalize(IMPORT_WEIGHTS)


def private_stock_build_annual(current: AnnualWheatBalance, previous: AnnualWheatBalance | None) -> float:
    if previous is None:
        return max(0.0, current.ending_stock_mmt * 0.22)
    return max(0.0, (current.ending_stock_mmt - previous.ending_stock_mmt) * 0.45)


def private_stock_month_share(month: int) -> float:
    shares = {4: 0.42, 5: 0.28, 6: 0.18, 7: 0.08, 8: 0.04}
    return shares.get(month, 0.0)


def festival_index(month: int) -> float:
    seasonal = {
        1: 103.0, 2: 101.0, 3: 104.0, 4: 98.0, 5: 97.0, 6: 97.0,
        7: 98.0, 8: 100.0, 9: 102.0, 10: 106.0, 11: 108.0, 12: 105.0,
    }
    return seasonal[month]


def build_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS factor_definitions (
            factor_key TEXT PRIMARY KEY,
            factor_name TEXT NOT NULL,
            description TEXT NOT NULL,
            why_it_matters TEXT NOT NULL,
            default_unit TEXT NOT NULL
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


def upsert_reference_tables(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """
        INSERT INTO factor_definitions (factor_key, factor_name, description, why_it_matters, default_unit)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(factor_key) DO UPDATE SET
            factor_name=excluded.factor_name,
            description=excluded.description,
            why_it_matters=excluded.why_it_matters,
            default_unit=excluded.default_unit
        """,
        FACTOR_DEFINITIONS,
    )

    sources = [
        ("usda_2017", ANNUAL_WHEAT["2016/17"].source_name, ANNUAL_WHEAT["2016/17"].source_url, "annual", "Wheat PSD table with imports, exports, feed, FSI, and total consumption."),
        ("usda_2019", ANNUAL_WHEAT["2017/18"].source_name, ANNUAL_WHEAT["2017/18"].source_url, "annual", "Wheat PSD table with imports, exports, feed, FSI, and total consumption."),
        ("usda_2021", ANNUAL_WHEAT["2019/20"].source_name, ANNUAL_WHEAT["2019/20"].source_url, "annual", "Wheat PSD table with revised 2019/20-2021/22 balance values."),
        ("usda_2026", ANNUAL_WHEAT["2022/23"].source_name, ANNUAL_WHEAT["2022/23"].source_url, "annual", "March 2026 grain circular used for latest demand / carry context."),
        ("world_bank_population", "World Bank population API", WORLD_BANK_POP_URL, "annual", "Annual India total population interpolated into monthly trend values."),
        ("agmarknet_local", "Local AGMARKNET monthly mandi price lake", None, "monthly", "Used for substitution-effect and wheat price pressure proxies from local historical prices."),
        ("curated_policy", "Curated wheat policy timeline", None, "event", "Policy change and OMSS release score series built from official wheat-policy milestones."),
    ]
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
        sources,
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


def build_rows() -> list[tuple[Any, ...]]:
    months = month_range(date(2016, 4, 1), date(2026, 3, 1))
    population = interpolate_population_monthly(months, fetch_population_series())
    substitution_index, price_pressure_index = load_monthly_price_ratios()
    monthly_exports = fetch_tradestat_monthly("export")
    monthly_imports = fetch_tradestat_monthly("import")

    rows: list[tuple[Any, ...]] = []
    previous_balance: AnnualWheatBalance | None = None
    annual_private_stock_map: dict[str, float] = {}
    for marketing_year, annual in ANNUAL_WHEAT.items():
        annual_private_stock_map[marketing_year] = private_stock_build_annual(annual, previous_balance)
        previous_balance = annual

    for d in months:
        ym = d.strftime("%Y-%m")
        marketing_year = marketing_year_for_month(d)
        annual = ANNUAL_WHEAT[marketing_year]
        month = d.month

        annual_seed = annual.fsi_consumption_mmt * 0.018
        annual_industrial = annual.fsi_consumption_mmt * 0.062
        annual_domestic_food = max(0.0, annual.fsi_consumption_mmt - annual_seed - annual_industrial)
        annual_pds = annual_domestic_food * 0.36
        annual_private_trade = annual_domestic_food - annual_pds
        annual_private_stock = annual_private_stock_map[marketing_year]

        values = {
            "domestic_consumption": (
                annual_domestic_food * CONSUMPTION_WEIGHTS[month],
                "million_tonnes",
                annual.source_name,
                annual.source_url,
                "annual_usda_fsi_to_monthly_food_proxy",
                "medium",
                "Built from USDA FSI consumption with seed and industrial shares separated before monthly seasonality is applied.",
            ),
            "pds_government_offtake": (
                annual_pds * CONSUMPTION_WEIGHTS[month],
                "million_tonnes",
                annual.source_name,
                annual.source_url,
                "derived_monthly_offtake_share_proxy",
                "low",
                "Institutional offtake proxy using a fixed share of domestic food demand because a clean 10-year monthly official series was not available.",
            ),
            "open_market_sales_release": (
                POLICY_EVENTS.get(ym, {}).get("open_market_sales_release", 0.0),
                "policy_index",
                "Curated wheat policy timeline",
                None,
                "curated_policy_event_score",
                "low",
                POLICY_EVENTS.get(ym, {}).get("notes", "No major OMSS release signal captured for this month."),
            ),
            "private_trade_demand": (
                annual_private_trade * CONSUMPTION_WEIGHTS[month],
                "million_tonnes",
                annual.source_name,
                annual.source_url,
                "derived_private_trade_residual",
                "low",
                "Private trade demand is treated as the residual after proxy government offtake is removed from domestic food demand.",
            ),
            "exports": (
                monthly_exports.get(
                    d.isoformat(),
                    annual.exports_mmt * TRADE_WEIGHTS[month],
                ),
                "million_tonnes",
                "DGCI&S TradeStat" if d.isoformat() in monthly_exports else annual.source_name,
                TRADESTAT_EXPORT_URL if d.isoformat() in monthly_exports else annual.source_url,
                "tradestat_monthly_total_hs1001" if d.isoformat() in monthly_exports else "annual_exports_to_monthly_proxy",
                "high" if d.isoformat() in monthly_exports else "medium",
                "Monthly wheat exports from TradeStat HS 1001 all-countries quantity table."
                if d.isoformat() in monthly_exports
                else "USDA marketing-year exports distributed into months with a trade-shape proxy.",
            ),
            "feed_use": (
                annual.feed_residual_mmt * CONSUMPTION_WEIGHTS[month],
                "million_tonnes",
                annual.source_name,
                annual.source_url,
                "annual_feed_residual_to_monthly_proxy",
                "medium",
                "Feed and residual is sourced annually from USDA where available and distributed monthly.",
            ),
            "seed_use": (
                annual_seed * SEED_WEIGHTS[month],
                "million_tonnes",
                annual.source_name,
                annual.source_url,
                "derived_seed_seasonality_proxy",
                "low",
                "Seed use is estimated from FSI consumption and concentrated in sowing months.",
            ),
            "industrial_use": (
                annual_industrial * CONSUMPTION_WEIGHTS[month],
                "million_tonnes",
                annual.source_name,
                annual.source_url,
                "derived_industrial_share_proxy",
                "low",
                "Industrial use is estimated as a smooth share of FSI consumption.",
            ),
            "private_stock_build": (
                annual_private_stock * private_stock_month_share(month),
                "million_tonnes",
                annual.source_name,
                annual.source_url,
                "carry_change_to_harvest_stock_build_proxy",
                "low",
                "Private stock build is proxied from annual carry change and concentrated into harvest months.",
            ),
            "substitution_effect": (
                substitution_index.get(ym, 100.0),
                "index_100",
                "Local AGMARKNET monthly mandi price lake",
                None,
                "relative_price_index_proxy",
                "medium" if ym in substitution_index else "low",
                "Index above 100 means wheat is relatively expensive against rice/maize peers; months before local monthly peer history default to neutral 100.",
            ),
            "population_trend": (
                population[d.isoformat()],
                "million_people",
                "World Bank population API",
                WORLD_BANK_POP_URL,
                "monthly_interpolation_from_annual_population",
                "high",
                "Annual World Bank population interpolated linearly across months.",
            ),
            "festival_seasonal_demand": (
                festival_index(month),
                "index_100",
                "Curated seasonal demand calendar",
                None,
                "calendar_seasonality_index",
                "medium",
                "Fixed monthly demand-seasonality index used to capture festive and winter consumption bias.",
            ),
            "retail_price_cpi_wheat_pressure": (
                price_pressure_index.get(ym, 100.0),
                "index_100",
                "Local AGMARKNET monthly mandi price lake",
                None,
                "monthly_price_pressure_proxy",
                "medium" if ym in price_pressure_index else "low",
                "Wheat mandi price index used as a retail/CPI pressure proxy where no clean 10-year monthly wheat CPI series was available.",
            ),
            "imports": (
                monthly_imports.get(
                    d.isoformat(),
                    annual.imports_mmt * IMPORT_WEIGHTS[month],
                ),
                "million_tonnes",
                "DGCI&S TradeStat" if d.isoformat() in monthly_imports else annual.source_name,
                TRADESTAT_IMPORT_URL if d.isoformat() in monthly_imports else annual.source_url,
                "tradestat_monthly_total_hs1001" if d.isoformat() in monthly_imports else "annual_imports_to_monthly_proxy",
                "high" if d.isoformat() in monthly_imports else "medium",
                "Monthly wheat imports from TradeStat HS 1001 all-countries quantity table."
                if d.isoformat() in monthly_imports
                else "USDA marketing-year imports distributed into months with a port-arrival shape proxy.",
            ),
            "policy_changes": (
                POLICY_EVENTS.get(ym, {}).get("policy_changes", 0.0),
                "policy_index",
                "Curated wheat policy timeline",
                None,
                "curated_policy_event_score",
                "medium" if ym in POLICY_EVENTS else "low",
                POLICY_EVENTS.get(ym, {}).get("notes", "No major tracked policy shock recorded for this month."),
            ),
        }

        total_demand_monthly = (
            values["domestic_consumption"][0]
            + values["exports"][0]
            + values["feed_use"][0]
            + values["seed_use"][0]
            + values["industrial_use"][0]
            + values["private_stock_build"][0]
        )
        values["total_demand_monthly"] = (
            total_demand_monthly,
            "million_tonnes",
            annual.source_name,
            annual.source_url,
            "domestic_consumption_plus_exports_plus_feed_plus_seed_plus_industrial_plus_private_stock_build",
            "medium",
            "Derived additive wheat demand total for monthly S&D balance. PDS and private trade demand are explanatory splits of domestic consumption and are not added again.",
        )

        for factor_key, (value, unit, source_name, source_url, method, confidence, notes) in values.items():
            rows.append(
                (
                    f"{factor_key}:{d.isoformat()}",
                    factor_key,
                    d.isoformat(),
                    marketing_year,
                    None if value is None or (isinstance(value, float) and math.isnan(value)) else round(float(value), 6),
                    unit,
                    source_name,
                    source_url,
                    method,
                    confidence,
                    notes,
                    UPDATED_AT,
                )
            )
    return rows


def write_db() -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    with sqlite3.connect(str(OUTPUT_DB)) as conn:
        build_schema(conn)
        upsert_reference_tables(conn)
        conn.execute("DELETE FROM factor_monthly_values")
        conn.executemany(
            """
            INSERT INTO factor_monthly_values (
                id, factor_key, metric_month, marketing_year, value, unit,
                source_name, source_url, method, confidence, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        summary = conn.execute(
            """
            SELECT COUNT(*) AS row_count, MIN(metric_month) AS min_month, MAX(metric_month) AS max_month
            FROM factor_monthly_values
            """
        ).fetchone()
        factor_counts = conn.execute(
            """
            SELECT factor_key, COUNT(*) AS row_count
            FROM factor_monthly_values
            GROUP BY factor_key
            ORDER BY factor_key
            """
        ).fetchall()
        factor_status_rows = conn.execute(
            """
            SELECT factor_key, monthly_source_status, current_load_mode
            FROM factor_status
            ORDER BY factor_key
            """
        ).fetchall()
        conn.commit()
    return {
        "status": "success",
        "db_path": str(OUTPUT_DB),
        "rows_written": int(summary[0]),
        "from": summary[1],
        "to": summary[2],
        "factor_counts": {row[0]: row[1] for row in factor_counts},
        "monthly_status": {row[0]: {"source_status": row[1], "load_mode": row[2]} for row in factor_status_rows},
    }


if __name__ == "__main__":
    print(json.dumps(write_db(), indent=2))
