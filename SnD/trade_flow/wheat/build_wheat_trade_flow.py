from __future__ import annotations

import sqlite3
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / "wheat_trade_flow.db"
UPDATED_AT = datetime.now(UTC).isoformat().replace("+00:00", "Z")

EXPORT_URL = "https://tradestat.commerce.gov.in/meidb/commodity_wise_all_countries_export"
IMPORT_URL = "https://tradestat.commerce.gov.in/meidb/commodity_wise_all_countries_import"
HS_CODE = "1001"
YEARS = list(range(2018, 2027))
MONTHS_BY_YEAR = {
    2018: list(range(1, 13)),
    2019: list(range(1, 13)),
    2020: list(range(1, 13)),
    2021: list(range(1, 13)),
    2022: list(range(1, 13)),
    2023: list(range(1, 13)),
    2024: list(range(1, 13)),
    2025: list(range(1, 13)),
    2026: [1],
}
MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS source_inventory (
            source_key TEXT PRIMARY KEY,
            source_name TEXT NOT NULL,
            source_url TEXT,
            source_type TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bilateral_monthly_flows (
            id TEXT PRIMARY KEY,
            commodity_key TEXT NOT NULL,
            flow_type TEXT NOT NULL,
            partner_country TEXT NOT NULL,
            metric_month TEXT NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            quantity REAL,
            value_inr_crore REAL,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trade_corridor_table (
            id TEXT PRIMARY KEY,
            commodity_key TEXT NOT NULL,
            flow_type TEXT NOT NULL,
            partner_country TEXT NOT NULL,
            latest_complete_year INTEGER NOT NULL,
            latest_year_quantity REAL,
            latest_year_value_inr_crore REAL,
            avg_5y_quantity REAL,
            avg_5y_value_inr_crore REAL,
            cagr_5y_quantity_pct REAL,
            cagr_5y_value_pct REAL,
            rank_latest_year INTEGER NOT NULL,
            source_name TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS over_under_index_matrix (
            id TEXT PRIMARY KEY,
            commodity_key TEXT NOT NULL,
            partner_country TEXT NOT NULL,
            india_export_share_pct REAL,
            destination_import_share_pct REAL,
            india_global_export_share_pct REAL,
            over_under_index REAL,
            status TEXT NOT NULL,
            notes TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS seasonal_export_chart (
            id TEXT PRIMARY KEY,
            commodity_key TEXT NOT NULL,
            month INTEGER NOT NULL,
            month_name TEXT NOT NULL,
            avg_5y_quantity REAL NOT NULL,
            avg_5y_value_inr_crore REAL NOT NULL,
            avg_5y_share_pct REAL NOT NULL,
            peak_window_rank INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS competing_supplier_map (
            id TEXT PRIMARY KEY,
            commodity_key TEXT NOT NULL,
            partner_country TEXT NOT NULL,
            competing_suppliers TEXT NOT NULL,
            rationale TEXT NOT NULL,
            source_name TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS data_gap_log (
            gap_key TEXT PRIMARY KEY,
            commodity_key TEXT NOT NULL,
            source_name TEXT NOT NULL,
            gap_description TEXT NOT NULL,
            impact TEXT NOT NULL,
            handling_approach TEXT NOT NULL,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def wipe(conn: sqlite3.Connection) -> None:
    for table in (
        "source_inventory",
        "bilateral_monthly_flows",
        "trade_corridor_table",
        "over_under_index_matrix",
        "seasonal_export_chart",
        "competing_supplier_map",
        "data_gap_log",
    ):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()


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


def fetch_monthly_country_values(flow_type: str, year: int, month: int, report_val: int) -> dict[str, float]:
    url = EXPORT_URL if flow_type == "export" else IMPORT_URL
    prefix = "cwacex" if flow_type == "export" else "cwacim"
    session = requests.Session()
    resp = session.get(url, timeout=40)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    token = soup.find("input", {"name": "_token"})["value"]
    payload = {
        "_token": token,
        f"{prefix}HSCODE": HS_CODE,
        f"{prefix}Month": str(month),
        f"{prefix}Year": str(year),
        f"{prefix}ReportVal": str(report_val),
        f"{prefix}ReportYear": "1",
    }
    result = session.post(url, data=payload, timeout=60)
    result.raise_for_status()
    parsed = BeautifulSoup(result.text, "html.parser")
    table = parsed.find("table", {"id": "example1"})
    if table is None:
        return {}
    rows = {}
    body = table.find("tbody")
    if body is None:
        return rows
    for tr in body.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(cells) < 4:
            continue
        country = cells[1].strip().upper()
        if country in {"TOTAL", ""}:
            continue
        current_value_text = cells[3].replace(",", "").strip()
        if current_value_text in {"-", ""}:
            current_value = 0.0
        else:
            current_value = float(current_value_text)
        rows[country] = current_value
    return rows


def fetch_all_flows() -> list[dict]:
    all_rows: list[dict] = []
    for flow_type in ("export", "import"):
        for year in YEARS:
            for month in MONTHS_BY_YEAR[year]:
                quantity_rows = fetch_monthly_country_values(flow_type, year, month, report_val=2)
                time.sleep(0.25)
                value_rows = fetch_monthly_country_values(flow_type, year, month, report_val=3)
                time.sleep(0.25)
                countries = sorted(set(quantity_rows) | set(value_rows))
                for country in countries:
                    all_rows.append(
                        {
                            "id": str(uuid.uuid4()),
                            "commodity_key": "wheat",
                            "flow_type": flow_type,
                            "partner_country": country,
                            "metric_month": f"{year}-{month:02d}-01",
                            "year": year,
                            "month": month,
                            "quantity": float(quantity_rows.get(country, 0.0)),
                            "value_inr_crore": float(value_rows.get(country, 0.0)),
                            "source_name": "DGCI&S TradeStat",
                            "source_url": url_for_flow(flow_type),
                            "notes": "Current-month country row from the official TradeStat commodity-wise all countries report.",
                            "updated_at": UPDATED_AT,
                        }
                    )
    return all_rows


def url_for_flow(flow_type: str) -> str:
    return EXPORT_URL if flow_type == "export" else IMPORT_URL


def annual_totals(rows: list[sqlite3.Row], flow_type: str) -> dict[str, dict[int, dict[str, float]]]:
    totals: dict[str, dict[int, dict[str, float]]] = {}
    for row in rows:
        if row["flow_type"] != flow_type:
            continue
        country = row["partner_country"]
        year = int(row["year"])
        totals.setdefault(country, {}).setdefault(year, {"quantity": 0.0, "value": 0.0})
        totals[country][year]["quantity"] += float(row["quantity"] or 0.0)
        totals[country][year]["value"] += float(row["value_inr_crore"] or 0.0)
    return totals


def calc_cagr(start: float, end: float, periods: int) -> float | None:
    if periods <= 0 or start <= 0 or end < 0:
        return None
    return ((end / start) ** (1 / periods) - 1) * 100


def build_corridor_table(rows: list[sqlite3.Row]) -> list[dict]:
    results: list[dict] = []
    latest_complete_year = 2025
    for flow_type in ("export", "import"):
        totals = annual_totals(rows, flow_type)
        ranking = sorted(
            (
                (country, data.get(latest_complete_year, {}).get("value", 0.0))
                for country, data in totals.items()
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        ranks = {country: rank for rank, (country, _value) in enumerate(ranking, start=1)}
        for country, data in totals.items():
            years = [year for year in range(2021, 2026) if year in data]
            qty_values = [data[year]["quantity"] for year in years]
            val_values = [data[year]["value"] for year in years]
            if not years:
                continue
            cagr_qty = calc_cagr(data[2021]["quantity"], data[2025]["quantity"], 4) if 2021 in data and 2025 in data else None
            cagr_val = calc_cagr(data[2021]["value"], data[2025]["value"], 4) if 2021 in data and 2025 in data else None
            results.append(
                {
                    "id": str(uuid.uuid4()),
                    "commodity_key": "wheat",
                    "flow_type": flow_type,
                    "partner_country": country,
                    "latest_complete_year": latest_complete_year,
                    "latest_year_quantity": round(data.get(latest_complete_year, {}).get("quantity", 0.0), 6),
                    "latest_year_value_inr_crore": round(data.get(latest_complete_year, {}).get("value", 0.0), 6),
                    "avg_5y_quantity": round(sum(qty_values) / len(qty_values), 6),
                    "avg_5y_value_inr_crore": round(sum(val_values) / len(val_values), 6),
                    "cagr_5y_quantity_pct": round(cagr_qty, 6) if cagr_qty is not None else None,
                    "cagr_5y_value_pct": round(cagr_val, 6) if cagr_val is not None else None,
                    "rank_latest_year": int(ranks.get(country, 9999)),
                    "source_name": "DGCI&S TradeStat",
                    "notes": "5-year corridor summary using annual sums from monthly TradeStat country rows.",
                    "updated_at": UPDATED_AT,
                }
            )
    return results


def build_over_under_index(rows: list[sqlite3.Row]) -> list[dict]:
    # We can compute India export corridor shares from bilateral flows, but the denominator
    # needed for a true destination-import over/under-index requires external destination-import
    # and global export shares that are not yet loaded. We keep the matrix explicit and honest.
    totals = annual_totals(rows, "export")
    latest_complete_year = 2025
    total_exports = sum(country_data.get(latest_complete_year, {}).get("value", 0.0) for country_data in totals.values()) or 1.0
    output = []
    for country, data in sorted(totals.items()):
        export_share = data.get(latest_complete_year, {}).get("value", 0.0) / total_exports * 100
        output.append(
            {
                "id": str(uuid.uuid4()),
                "commodity_key": "wheat",
                "partner_country": country,
                "india_export_share_pct": round(export_share, 6),
                "destination_import_share_pct": None,
                "india_global_export_share_pct": None,
                "over_under_index": None,
                "status": "partial_pending_external_denominator",
                "notes": "India corridor export share is computed; destination import share and India global export share require UN Comtrade or equivalent denominator data that is not yet loaded.",
                "updated_at": UPDATED_AT,
            }
        )
    return output


def build_seasonal_export_chart(rows: list[sqlite3.Row]) -> list[dict]:
    latest_complete_years = {2021, 2022, 2023, 2024, 2025}
    month_values = {month: {"quantity": 0.0, "value": 0.0} for month in range(1, 13)}
    annual_total_qty = 0.0
    for row in rows:
        if row["flow_type"] != "export" or int(row["year"]) not in latest_complete_years:
            continue
        month = int(row["month"])
        qty = float(row["quantity"] or 0.0)
        val = float(row["value_inr_crore"] or 0.0)
        month_values[month]["quantity"] += qty
        month_values[month]["value"] += val
        annual_total_qty += qty
    avg_rows = []
    ranked = sorted(
        ((month, values["quantity"] / 5.0) for month, values in month_values.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    rank_map = {month: rank for rank, (month, _value) in enumerate(ranked, start=1)}
    for month in range(1, 13):
        avg_qty = month_values[month]["quantity"] / 5.0
        avg_val = month_values[month]["value"] / 5.0
        share = (avg_qty * 5.0 / annual_total_qty * 100.0) if annual_total_qty else 0.0
        avg_rows.append(
            {
                "id": str(uuid.uuid4()),
                "commodity_key": "wheat",
                "month": month,
                "month_name": MONTH_NAMES[month],
                "avg_5y_quantity": round(avg_qty, 6),
                "avg_5y_value_inr_crore": round(avg_val, 6),
                "avg_5y_share_pct": round(share, 6),
                "peak_window_rank": rank_map[month],
                "updated_at": UPDATED_AT,
            }
        )
    return avg_rows


def build_competing_supplier_map() -> list[dict]:
    rows = [
        ("BANGLADESH", "Russia; Ukraine; Australia", "Bangladesh is a core South Asian wheat corridor where Black Sea and Australian exporters compete with India."),
        ("SRI LANKA", "Russia; Ukraine; Australia", "Sri Lanka is served by large low-cost exporters and India competes on proximity and timing."),
        ("U ARAB EMTS", "Russia; Ukraine; Australia; EU", "UAE corridor competition is shaped by Black Sea and other major exporters."),
        ("YEMEN REPUBLIC", "Russia; Ukraine; Australia", "Yemen corridor tends to overlap with Black Sea supplier reach and freight-sensitive competition."),
        ("NEPAL", "Limited direct competition; India dominates proximity advantage", "Nepal is a nearby market where India often has a natural logistics advantage."),
    ]
    return [
        {
            "id": str(uuid.uuid4()),
            "commodity_key": "wheat",
            "partner_country": country,
            "competing_suppliers": suppliers,
            "rationale": rationale,
            "source_name": "NCEL Wheat Maize SD Process doc + curated market structure",
            "notes": "Competing supplier map aligned to the Step 7 brief.",
            "updated_at": UPDATED_AT,
        }
        for country, suppliers, rationale in rows
    ]


def build_gap_log() -> list[dict]:
    return [
        {
            "gap_key": "un_comtrade_destination_denominator",
            "commodity_key": "wheat",
            "source_name": "UN Comtrade",
            "gap_description": "Destination total wheat imports and India global export share denominator are not yet loaded into the local Step 7 build.",
            "impact": "Prevents a full over/under-index calculation from being finalized.",
            "handling_approach": "Matrix is stored as partial with India corridor export share already computed; add UN Comtrade annual bilateral imports to complete the denominator.",
            "status": "open",
            "updated_at": UPDATED_AT,
        },
        {
            "gap_key": "apeda_country_breakdown_wheat",
            "commodity_key": "wheat",
            "source_name": "APEDA",
            "gap_description": "APEDA commodity-level wheat bilateral export breakdown is not yet loaded in this implementation.",
            "impact": "TradeStat remains the primary bilateral source without APEDA cross-checks.",
            "handling_approach": "Use TradeStat as the authoritative monthly corridor layer; add APEDA only as secondary validation if accessible.",
            "status": "open",
            "updated_at": UPDATED_AT,
        },
        {
            "gap_key": "volza_shipment_intelligence",
            "commodity_key": "wheat",
            "source_name": "Volza",
            "gap_description": "Shipment-level buyer/seller and port intelligence is not loaded.",
            "impact": "No buyer/seller micro view or shipment-level corridor drilldown yet.",
            "handling_approach": "Keep Step 7 at corridor-country level for now and add shipment intelligence later if available.",
            "status": "open",
            "updated_at": UPDATED_AT,
        },
    ]


def build() -> None:
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()
    conn = connect(OUTPUT_DB)
    ensure_schema(conn)
    wipe(conn)

    insert_many(
        conn,
        "source_inventory",
        [
            {
                "source_key": "tradestat_exports",
                "source_name": "DGCI&S TradeStat exports",
                "source_url": EXPORT_URL,
                "source_type": "web",
                "notes": "Official monthly country-wise bilateral wheat export data by HS code.",
                "updated_at": UPDATED_AT,
            },
            {
                "source_key": "tradestat_imports",
                "source_name": "DGCI&S TradeStat imports",
                "source_url": IMPORT_URL,
                "source_type": "web",
                "notes": "Official monthly country-wise bilateral wheat import data by HS code.",
                "updated_at": UPDATED_AT,
            },
            {
                "source_key": "process_doc",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": "",
                "source_type": "docx",
                "notes": "Defines Step 7 bilateral trade flow outputs and target corridors.",
                "updated_at": UPDATED_AT,
            },
        ],
    )

    flow_rows = fetch_all_flows()
    insert_many(conn, "bilateral_monthly_flows", flow_rows)

    db_rows = conn.execute("SELECT * FROM bilateral_monthly_flows").fetchall()
    insert_many(conn, "trade_corridor_table", build_corridor_table(db_rows))
    insert_many(conn, "over_under_index_matrix", build_over_under_index(db_rows))
    insert_many(conn, "seasonal_export_chart", build_seasonal_export_chart(db_rows))
    insert_many(conn, "competing_supplier_map", build_competing_supplier_map())
    insert_many(conn, "data_gap_log", build_gap_log())

    conn.close()


if __name__ == "__main__":
    build()
