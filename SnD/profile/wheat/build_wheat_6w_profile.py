from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / "wheat_6w_profile.db"
WHEAT_SUPPORT_DB = ROOT / "backend" / "data" / "wheat_model_support.db"
UPDATED_AT = datetime.now(UTC).isoformat().replace("+00:00", "Z")


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

        CREATE TABLE IF NOT EXISTS commodity_master (
            commodity_key TEXT PRIMARY KEY,
            commodity_name TEXT NOT NULL,
            scientific_name TEXT,
            commodity_group TEXT NOT NULL,
            primary_uses TEXT NOT NULL,
            benchmark_context TEXT,
            default_unit TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS hs_code_register (
            commodity_key TEXT NOT NULL,
            hs_code TEXT NOT NULL,
            hs_description TEXT NOT NULL,
            trade_scope TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (commodity_key, hs_code)
        );

        CREATE TABLE IF NOT EXISTS crop_year_calendar (
            id TEXT PRIMARY KEY,
            commodity_key TEXT NOT NULL,
            calendar_type TEXT NOT NULL,
            stage_name TEXT NOT NULL,
            start_month INTEGER NOT NULL,
            end_month INTEGER NOT NULL,
            geography_scope TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS six_w_output (
            id TEXT PRIMARY KEY,
            commodity_key TEXT NOT NULL,
            dimension_key TEXT NOT NULL,
            item_key TEXT NOT NULL,
            item_label TEXT NOT NULL,
            item_value TEXT NOT NULL,
            geography_scope TEXT,
            source_name TEXT NOT NULL,
            source_url TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS national_trend_10y (
            id TEXT PRIMARY KEY,
            commodity_key TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            marketing_year TEXT NOT NULL,
            metric_date TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS state_production_map (
            state_name TEXT PRIMARY KEY,
            commodity_key TEXT NOT NULL,
            production_role TEXT NOT NULL,
            indicative_share_pct REAL,
            acreage_strength TEXT,
            yield_strength TEXT,
            major_varieties TEXT,
            end_use_orientation TEXT,
            source_name TEXT NOT NULL,
            source_url TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS harvest_calendar (
            id TEXT PRIMARY KEY,
            commodity_key TEXT NOT NULL,
            state_name TEXT NOT NULL,
            stage_name TEXT NOT NULL,
            start_month INTEGER NOT NULL,
            end_month INTEGER NOT NULL,
            season_name TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS key_player_register (
            id TEXT PRIMARY KEY,
            commodity_key TEXT NOT NULL,
            player_name TEXT NOT NULL,
            player_type TEXT NOT NULL,
            role_description TEXT NOT NULL,
            geography_scope TEXT,
            source_name TEXT NOT NULL,
            source_url TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def wipe(conn: sqlite3.Connection) -> None:
    for table in (
        "source_inventory",
        "commodity_master",
        "hs_code_register",
        "crop_year_calendar",
        "six_w_output",
        "national_trend_10y",
        "state_production_map",
        "harvest_calendar",
        "key_player_register",
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


def load_national_trends() -> list[dict]:
    conn = connect(WHEAT_SUPPORT_DB)
    indicator_rows = conn.execute(
        """
        SELECT indicator_key, indicator_name, indicator_date, period_label, value, unit, source_name, source_url, notes
        FROM wheat_indicator_history
        WHERE indicator_key IN ('wheat_area_million_hectare', 'wheat_production_million_tonnes', 'wheat_yield_kg_per_hectare')
        ORDER BY indicator_key, indicator_date
        """
    ).fetchall()
    procurement_rows = conn.execute(
        """
        SELECT signal_date, marketing_season, value, unit, source_name, source_url, notes
        FROM wheat_support_signals
        WHERE signal_group='procurement' AND signal_name='Actual wheat procurement'
        ORDER BY signal_date
        """
    ).fetchall()
    conn.close()

    rows = []
    for idx, row in enumerate(indicator_rows, start=1):
        metric_key = row["indicator_key"].replace("wheat_", "")
        rows.append(
            {
                "id": f"trend-{metric_key}-{idx}",
                "commodity_key": "wheat",
                "metric_key": metric_key,
                "metric_name": row["indicator_name"],
                "marketing_year": row["period_label"],
                "metric_date": row["indicator_date"],
                "value": float(row["value"]),
                "unit": row["unit"],
                "source_name": row["source_name"],
                "source_url": row["source_url"],
                "notes": row["notes"],
                "updated_at": UPDATED_AT,
            }
        )
    for idx, row in enumerate(procurement_rows, start=1):
        rows.append(
            {
                "id": f"trend-procurement-{idx}",
                "commodity_key": "wheat",
                "metric_key": "procurement_actual_lmt",
                "metric_name": "Actual wheat procurement",
                "marketing_year": row["marketing_season"],
                "metric_date": row["signal_date"],
                "value": float(row["value"]),
                "unit": row["unit"],
                "source_name": row["source_name"],
                "source_url": row["source_url"],
                "notes": row["notes"],
                "updated_at": UPDATED_AT,
            }
        )
    return rows


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
                "source_key": "economic_survey",
                "source_name": "Economic Survey Statistical Appendix",
                "source_url": "https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf",
                "source_type": "pdf",
                "notes": "Official annual area, production, and yield backbone for wheat.",
                "updated_at": UPDATED_AT,
            },
            {
                "source_key": "wheat_support",
                "source_name": "Local wheat support store",
                "source_url": str(WHEAT_SUPPORT_DB),
                "source_type": "db",
                "notes": "Support store used for trend, procurement, and policy context.",
                "updated_at": UPDATED_AT,
            },
            {
                "source_key": "pib",
                "source_name": "PIB",
                "source_url": "https://www.pib.gov.in/",
                "source_type": "web",
                "notes": "MSP and policy context.",
                "updated_at": UPDATED_AT,
            },
            {
                "source_key": "doc_profile",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "source_type": "docx",
                "notes": "Guiding profile brief for the 6W structure.",
                "updated_at": UPDATED_AT,
            },
        ],
    )

    insert_many(
        conn,
        "commodity_master",
        [
            {
                "commodity_key": "wheat",
                "commodity_name": "Wheat",
                "scientific_name": "Triticum aestivum",
                "commodity_group": "cereal",
                "primary_uses": "atta and flour milling, bakery, feed, industrial starch, public distribution",
                "benchmark_context": "India domestic mandi market with global benchmark sensitivity to Black Sea and major exporter flows",
                "default_unit": "million_tonnes",
                "notes": "Step 2 commodity context layer for Wheat.",
                "updated_at": UPDATED_AT,
            }
        ],
    )

    insert_many(
        conn,
        "hs_code_register",
        [
            {
                "commodity_key": "wheat",
                "hs_code": "1001",
                "hs_description": "Wheat and meslin",
                "trade_scope": "primary trade code",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Primary HS code used throughout Wheat trade analysis.",
                "updated_at": UPDATED_AT,
            }
        ],
    )

    insert_many(
        conn,
        "crop_year_calendar",
        [
            {
                "id": "wheat-crop-year-1",
                "commodity_key": "wheat",
                "calendar_type": "marketing_year",
                "stage_name": "India wheat crop year",
                "start_month": 4,
                "end_month": 3,
                "geography_scope": "India",
                "notes": "Apr-Mar marketing year used across the Wheat S&D stack.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "wheat-crop-stage-sowing",
                "commodity_key": "wheat",
                "calendar_type": "crop_stage",
                "stage_name": "Rabi sowing",
                "start_month": 10,
                "end_month": 12,
                "geography_scope": "India wheat belt",
                "notes": "Primary sowing window.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "wheat-crop-stage-growth",
                "commodity_key": "wheat",
                "calendar_type": "crop_stage",
                "stage_name": "Vegetative and grain-fill",
                "start_month": 1,
                "end_month": 3,
                "geography_scope": "India wheat belt",
                "notes": "Winter temperature and frost sensitivity window.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "wheat-crop-stage-harvest",
                "commodity_key": "wheat",
                "calendar_type": "crop_stage",
                "stage_name": "Harvest and arrivals",
                "start_month": 3,
                "end_month": 6,
                "geography_scope": "India wheat belt",
                "notes": "Harvest starts in March and fresh arrivals dominate in April-June.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "wheat-crop-stage-procurement",
                "commodity_key": "wheat",
                "calendar_type": "market_stage",
                "stage_name": "FCI and state procurement",
                "start_month": 4,
                "end_month": 6,
                "geography_scope": "Punjab, Haryana, MP, UP",
                "notes": "Main procurement window after harvest.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "wheat-crop-stage-export",
                "commodity_key": "wheat",
                "calendar_type": "trade_stage",
                "stage_name": "Peak export window",
                "start_month": 5,
                "end_month": 9,
                "geography_scope": "India ports",
                "notes": "Indicative export window when domestic availability is strongest after harvest.",
                "updated_at": UPDATED_AT,
            },
        ],
    )

    insert_many(
        conn,
        "six_w_output",
        [
            {
                "id": "6w-where-1",
                "commodity_key": "wheat",
                "dimension_key": "where",
                "item_key": "core_states",
                "item_label": "Core wheat states",
                "item_value": "Punjab; Haryana; Uttar Pradesh; Madhya Pradesh",
                "geography_scope": "India",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Primary geography focus defined in the doc.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "6w-what-1",
                "commodity_key": "wheat",
                "dimension_key": "what",
                "item_key": "grades_varieties",
                "item_label": "Grades and varieties",
                "item_value": "Milling wheat; feed wheat; Sharbati wheat; standard FAQ wheat",
                "geography_scope": "India",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Variety and end-use framing for the profile layer.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "6w-when-1",
                "commodity_key": "wheat",
                "dimension_key": "when",
                "item_key": "season_timeline",
                "item_label": "Season timeline",
                "item_value": "Harvest -> mandi arrivals -> procurement -> port shipment",
                "geography_scope": "India",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Explicit workflow stated in the doc.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "6w-howmuch-1",
                "commodity_key": "wheat",
                "dimension_key": "how_much",
                "item_key": "metrics_backbone",
                "item_label": "10-year metrics backbone",
                "item_value": "Area (Mha), production (MnT), yield (kg/ha), procurement (LMT)",
                "geography_scope": "India",
                "source_name": "Economic Survey Statistical Appendix",
                "source_url": "https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf",
                "notes": "National trend series loaded from support stores and used throughout the Wheat system.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "6w-why-1",
                "commodity_key": "wheat",
                "dimension_key": "why",
                "item_key": "price_drivers",
                "item_label": "Key price drivers",
                "item_value": "MSP linkage; procurement intensity; winter temperature and frost; export policy; Black Sea disruption",
                "geography_scope": "India + Global",
                "source_name": "Wheat price drivers DB",
                "source_url": str(ROOT / "SnD" / "price_drivers" / "wheat" / "wheat_price_drivers.db"),
                "notes": "Summarizes the Step 5 driver layer into the profile context.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "6w-whom-1",
                "commodity_key": "wheat",
                "dimension_key": "whom",
                "item_key": "key_actors",
                "item_label": "Key institutions and market actors",
                "item_value": "FCI; state procurement agencies; flour millers; cooperative exporters; private traders",
                "geography_scope": "India",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Key participants in the wheat value chain and policy system.",
                "updated_at": UPDATED_AT,
            },
        ],
    )

    insert_many(conn, "national_trend_10y", load_national_trends())

    insert_many(
        conn,
        "state_production_map",
        [
            {
                "state_name": "Punjab",
                "commodity_key": "wheat",
                "production_role": "high procurement anchor",
                "indicative_share_pct": 15.0,
                "acreage_strength": "high",
                "yield_strength": "very_high",
                "major_varieties": "FAQ milling wheat",
                "end_use_orientation": "public procurement and milling",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Core wheat state with heavy procurement importance.",
                "updated_at": UPDATED_AT,
            },
            {
                "state_name": "Haryana",
                "commodity_key": "wheat",
                "production_role": "procurement-intensive producer",
                "indicative_share_pct": 11.0,
                "acreage_strength": "medium_high",
                "yield_strength": "very_high",
                "major_varieties": "FAQ milling wheat",
                "end_use_orientation": "public procurement and milling",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Important procurement and surplus-market state.",
                "updated_at": UPDATED_AT,
            },
            {
                "state_name": "Uttar Pradesh",
                "commodity_key": "wheat",
                "production_role": "largest broad-base producer",
                "indicative_share_pct": 31.0,
                "acreage_strength": "very_high",
                "yield_strength": "medium",
                "major_varieties": "milling wheat and local consumption grades",
                "end_use_orientation": "domestic food use and procurement",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Largest broad-base wheat state by output scale.",
                "updated_at": UPDATED_AT,
            },
            {
                "state_name": "Madhya Pradesh",
                "commodity_key": "wheat",
                "production_role": "surplus and Sharbati-linked producer",
                "indicative_share_pct": 21.0,
                "acreage_strength": "high",
                "yield_strength": "medium_high",
                "major_varieties": "Sharbati wheat; milling wheat",
                "end_use_orientation": "premium wheat, procurement, interstate trade",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Important for premium wheat context and central Indian supply.",
                "updated_at": UPDATED_AT,
            },
        ],
    )

    harvest_rows = []
    harvest_specs = [
        ("Punjab", "Rabi sowing", 10, 12, "rabi"),
        ("Punjab", "Harvest", 3, 4, "rabi"),
        ("Punjab", "Mandi arrivals", 4, 6, "rabi"),
        ("Punjab", "Procurement", 4, 6, "rabi"),
        ("Haryana", "Rabi sowing", 10, 12, "rabi"),
        ("Haryana", "Harvest", 3, 4, "rabi"),
        ("Haryana", "Mandi arrivals", 4, 6, "rabi"),
        ("Haryana", "Procurement", 4, 6, "rabi"),
        ("Uttar Pradesh", "Rabi sowing", 10, 12, "rabi"),
        ("Uttar Pradesh", "Harvest", 3, 4, "rabi"),
        ("Uttar Pradesh", "Mandi arrivals", 4, 6, "rabi"),
        ("Uttar Pradesh", "Procurement", 4, 6, "rabi"),
        ("Madhya Pradesh", "Rabi sowing", 10, 12, "rabi"),
        ("Madhya Pradesh", "Harvest", 3, 4, "rabi"),
        ("Madhya Pradesh", "Mandi arrivals", 4, 6, "rabi"),
        ("Madhya Pradesh", "Procurement", 4, 6, "rabi"),
    ]
    for idx, (state, stage, start_month, end_month, season_name) in enumerate(harvest_specs, start=1):
        harvest_rows.append(
            {
                "id": f"harvest-{idx}",
                "commodity_key": "wheat",
                "state_name": state,
                "stage_name": stage,
                "start_month": start_month,
                "end_month": end_month,
                "season_name": season_name,
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Step 2 harvest and market calendar for core wheat states.",
                "updated_at": UPDATED_AT,
            }
        )
    insert_many(conn, "harvest_calendar", harvest_rows)

    insert_many(
        conn,
        "key_player_register",
        [
            {
                "id": "player-1",
                "commodity_key": "wheat",
                "player_name": "Food Corporation of India",
                "player_type": "public_agency",
                "role_description": "Central buffer stock holder, procurement anchor, and release decision maker.",
                "geography_scope": "India",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Primary institutional actor for wheat stocks and procurement.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "player-2",
                "commodity_key": "wheat",
                "player_name": "State procurement agencies",
                "player_type": "state_agency",
                "role_description": "State-level procurement and handling in major wheat belts.",
                "geography_scope": "Punjab; Haryana; Madhya Pradesh; Uttar Pradesh",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Operational extension of public procurement.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "player-3",
                "commodity_key": "wheat",
                "player_name": "Private flour millers",
                "player_type": "private_buyer",
                "role_description": "Core commercial buyers for milling wheat and atta demand.",
                "geography_scope": "India",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Important for private trade demand and price transmission.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "player-4",
                "commodity_key": "wheat",
                "player_name": "Cooperative exporters",
                "player_type": "exporter",
                "role_description": "Structured export participants when policy allows wheat exports.",
                "geography_scope": "India ports",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Relevant in export windows and policy regime changes.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "player-5",
                "commodity_key": "wheat",
                "player_name": "Private traders and stockists",
                "player_type": "trade",
                "role_description": "Open-market inventory, inter-state arbitrage, and mandi participation.",
                "geography_scope": "India",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(ROOT.parent / "Downloads" / "NCEL_Wheat_Maize_SD_Process.docx"),
                "notes": "Key private market layer outside the public system.",
                "updated_at": UPDATED_AT,
            },
        ],
    )

    conn.close()


if __name__ == "__main__":
    build()
