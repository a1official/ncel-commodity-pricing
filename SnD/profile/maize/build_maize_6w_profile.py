from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / "maize_6w_profile.db"
MAIZE_SUPPORT_DB = ROOT / "backend" / "data" / "maize_model_support.db"
PROCESS_DOC = Path(r"C:\Users\akash2000.at\Downloads\NCEL_Wheat_Maize_SD_Process.docx")
UPDATED_AT = datetime.now(UTC).isoformat().replace("+00:00", "Z")


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS maize_source_inventory (
            source_key TEXT PRIMARY KEY,
            source_name TEXT NOT NULL,
            source_url TEXT,
            source_type TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_commodity_master (
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

        CREATE TABLE IF NOT EXISTS maize_hs_code_register (
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

        CREATE TABLE IF NOT EXISTS maize_crop_year_calendar (
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

        CREATE TABLE IF NOT EXISTS maize_six_w_output (
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

        CREATE TABLE IF NOT EXISTS maize_national_trend_10y (
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

        CREATE TABLE IF NOT EXISTS maize_state_production_map (
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

        CREATE TABLE IF NOT EXISTS maize_harvest_calendar (
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

        CREATE TABLE IF NOT EXISTS maize_key_player_register (
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
        "maize_source_inventory",
        "maize_commodity_master",
        "maize_hs_code_register",
        "maize_crop_year_calendar",
        "maize_six_w_output",
        "maize_national_trend_10y",
        "maize_state_production_map",
        "maize_harvest_calendar",
        "maize_key_player_register",
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
        [tuple(row[column] for column in columns) for row in rows],
    )
    conn.commit()


def load_national_trends() -> list[dict]:
    conn = connect(MAIZE_SUPPORT_DB)
    rows = conn.execute(
        """
        SELECT indicator_key, indicator_name, indicator_date, period_label, value, unit, source_name, source_url, notes
        FROM maize_indicator_history
        WHERE indicator_key IN (
            'maize_area',
            'maize_production',
            'maize_yield_kg_per_hectare',
            'maize_msp'
        )
        ORDER BY indicator_key, indicator_date
        """
    ).fetchall()
    conn.close()

    metric_name_map = {
        "maize_area": "gross_area",
        "maize_production": "production",
        "maize_yield_kg_per_hectare": "yield_kg_per_hectare",
        "maize_msp": "msp_inr_quintal",
    }
    result = []
    for idx, row in enumerate(rows, start=1):
        metric_key = metric_name_map.get(row["indicator_key"], row["indicator_key"])
        result.append(
            {
                "id": f"trend-{metric_key}-{idx}",
                "commodity_key": "maize",
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
    return result


def build() -> None:
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()
    conn = connect(OUTPUT_DB)
    ensure_schema(conn)
    wipe(conn)

    insert_many(
        conn,
        "maize_source_inventory",
        [
            {
                "source_key": "economic_survey",
                "source_name": "Economic Survey Statistical Appendix",
                "source_url": "https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf",
                "source_type": "pdf",
                "notes": "Official annual Maize area, production, and yield backbone.",
                "updated_at": UPDATED_AT,
            },
            {
                "source_key": "maize_support",
                "source_name": "Local maize support store",
                "source_url": str(MAIZE_SUPPORT_DB),
                "source_type": "db",
                "notes": "Support store used for Maize indicator history and benchmark context.",
                "updated_at": UPDATED_AT,
            },
            {
                "source_key": "trade_stat",
                "source_name": "DGCI&S TradeStat",
                "source_url": "https://tradestat.commerce.gov.in/",
                "source_type": "web",
                "notes": "Official India trade system for HS-linked Maize import/export mapping.",
                "updated_at": UPDATED_AT,
            },
            {
                "source_key": "world_bank",
                "source_name": "World Bank Pink Sheet / World Bank API",
                "source_url": "https://www.worldbank.org/",
                "source_type": "api",
                "notes": "Used for benchmark and macro context in the Maize support layer.",
                "updated_at": UPDATED_AT,
            },
            {
                "source_key": "process_doc",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(PROCESS_DOC),
                "source_type": "docx",
                "notes": "Guiding 6W process document for the commodity profile layer.",
                "updated_at": UPDATED_AT,
            },
        ],
    )

    insert_many(
        conn,
        "maize_commodity_master",
        [
            {
                "commodity_key": "maize",
                "commodity_name": "Maize",
                "scientific_name": "Zea mays",
                "commodity_group": "cereal",
                "primary_uses": "poultry and livestock feed, starch, food processing, industrial use, ethanol-linked demand",
                "benchmark_context": "India domestic mandi market with strong sensitivity to poultry feed demand, monsoon-linked acreage, and global corn benchmarks led by the US and Brazil",
                "default_unit": "million_tonnes",
                "notes": "Step 2 commodity context layer for Maize.",
                "updated_at": UPDATED_AT,
            }
        ],
    )

    insert_many(
        conn,
        "maize_hs_code_register",
        [
            {
                "commodity_key": "maize",
                "hs_code": "1005",
                "hs_description": "Maize (corn)",
                "trade_scope": "primary trade code",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(PROCESS_DOC),
                "notes": "Primary HS code used throughout Maize trade analysis.",
                "updated_at": UPDATED_AT,
            }
        ],
    )

    insert_many(
        conn,
        "maize_crop_year_calendar",
        [
            {
                "id": "maize-crop-year",
                "commodity_key": "maize",
                "calendar_type": "marketing_year",
                "stage_name": "India Maize crop year",
                "start_month": 10,
                "end_month": 9,
                "geography_scope": "India",
                "notes": "Oct-Sep crop-year view aligned to kharif-dominant Maize availability.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "maize-kharif-sowing",
                "commodity_key": "maize",
                "calendar_type": "crop_stage",
                "stage_name": "Kharif sowing",
                "start_month": 6,
                "end_month": 7,
                "geography_scope": "India Maize belt",
                "notes": "Monsoon-linked sowing window for the dominant Maize crop.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "maize-kharif-growth",
                "commodity_key": "maize",
                "calendar_type": "crop_stage",
                "stage_name": "Kharif vegetative and grain-fill",
                "start_month": 8,
                "end_month": 9,
                "geography_scope": "India Maize belt",
                "notes": "Weather-sensitive crop development period.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "maize-kharif-harvest",
                "commodity_key": "maize",
                "calendar_type": "crop_stage",
                "stage_name": "Kharif harvest and arrivals",
                "start_month": 9,
                "end_month": 1,
                "geography_scope": "India Maize belt",
                "notes": "Main domestic arrival window.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "maize-rabi-sowing",
                "commodity_key": "maize",
                "calendar_type": "crop_stage",
                "stage_name": "Rabi sowing",
                "start_month": 10,
                "end_month": 12,
                "geography_scope": "Rabi Maize pockets",
                "notes": "Secondary seasonal crop in states like Bihar and Telangana.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "maize-rabi-harvest",
                "commodity_key": "maize",
                "calendar_type": "crop_stage",
                "stage_name": "Rabi harvest",
                "start_month": 2,
                "end_month": 4,
                "geography_scope": "Rabi Maize pockets",
                "notes": "Secondary harvest window that smooths supply after kharif.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "maize-feed-cycle",
                "commodity_key": "maize",
                "calendar_type": "demand_cycle",
                "stage_name": "Poultry feed demand cycle",
                "start_month": 1,
                "end_month": 12,
                "geography_scope": "India feed belt",
                "notes": "Feed demand is continuous but varies with poultry placement and price spreads.",
                "updated_at": UPDATED_AT,
            },
        ],
    )

    insert_many(
        conn,
        "maize_six_w_output",
        [
            {
                "id": "maize-where",
                "commodity_key": "maize",
                "dimension_key": "where",
                "item_key": "where_india",
                "item_label": "Where",
                "item_value": "Karnataka; Madhya Pradesh; Maharashtra; Bihar; Telangana; Rajasthan; Andhra Pradesh; Uttar Pradesh",
                "geography_scope": "India",
                "source_name": "Curated from Maize production structure",
                "source_url": str(MAIZE_SUPPORT_DB),
                "notes": "Core producing and demand-linked Maize states for the first profile version.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "maize-what",
                "commodity_key": "maize",
                "dimension_key": "what",
                "item_key": "what_product",
                "item_label": "What",
                "item_value": "Feed maize; industrial maize; starch and processing-grade maize; poultry-linked demand crop",
                "geography_scope": "India",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(PROCESS_DOC),
                "notes": "Functional product view for the Maize market.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "maize-when",
                "commodity_key": "maize",
                "dimension_key": "when",
                "item_key": "when_calendar",
                "item_label": "When",
                "item_value": "Kharif sowing Jun-Jul; kharif harvest and arrivals Sep-Jan; rabi harvest Feb-Apr; Brazil safrinha and US crop cycles shape global price timing",
                "geography_scope": "India + Global",
                "source_name": "Curated crop calendar",
                "source_url": str(MAIZE_SUPPORT_DB),
                "notes": "Operational calendar for Maize supply and benchmark sensitivity.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "maize-how-much",
                "commodity_key": "maize",
                "dimension_key": "how_much",
                "item_key": "how_much_metrics",
                "item_label": "How Much",
                "item_value": "Area (million hectare), production (million tonnes), yield (kg/ha), imports, exports, MSP",
                "geography_scope": "India",
                "source_name": "Economic Survey Statistical Appendix",
                "source_url": "https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf",
                "notes": "Primary quantitative profile metrics for Maize.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "maize-why",
                "commodity_key": "maize",
                "dimension_key": "why",
                "item_key": "why_price_moves",
                "item_label": "Why",
                "item_value": "Poultry feed demand; monsoon distribution; kharif acreage; US corn crop; Brazil safrinha crop; export policy; ethanol and industrial demand signals",
                "geography_scope": "India + Global",
                "source_name": "NCEL Wheat Maize SD Process doc",
                "source_url": str(PROCESS_DOC),
                "notes": "Structural reasons Maize prices move in the first framework version.",
                "updated_at": UPDATED_AT,
            },
            {
                "id": "maize-whom",
                "commodity_key": "maize",
                "dimension_key": "whom",
                "item_key": "whom_market",
                "item_label": "Whom",
                "item_value": "Farmers; feed millers; poultry integrators; starch industry; ethanol-linked buyers; traders; exporters and importers",
                "geography_scope": "India",
                "source_name": "Curated market structure",
                "source_url": str(PROCESS_DOC),
                "notes": "Key actors in the Maize market chain.",
                "updated_at": UPDATED_AT,
            },
        ],
    )

    insert_many(conn, "maize_national_trend_10y", load_national_trends())

    insert_many(
        conn,
        "maize_state_production_map",
        [
            {
                "state_name": "Karnataka",
                "commodity_key": "maize",
                "production_role": "core producer and feed-linked market",
                "indicative_share_pct": 16.0,
                "acreage_strength": "high",
                "yield_strength": "high",
                "major_varieties": "feed maize, hybrid maize",
                "end_use_orientation": "feed and poultry belt",
                "source_name": "Curated Maize profile context",
                "source_url": str(MAIZE_SUPPORT_DB),
                "notes": "Indicative role-based state map entry for Maize.",
                "updated_at": UPDATED_AT,
            },
            {
                "state_name": "Madhya Pradesh",
                "commodity_key": "maize",
                "production_role": "large kharif producer",
                "indicative_share_pct": 15.0,
                "acreage_strength": "high",
                "yield_strength": "medium",
                "major_varieties": "hybrid maize",
                "end_use_orientation": "feed and inter-state trade",
                "source_name": "Curated Maize profile context",
                "source_url": str(MAIZE_SUPPORT_DB),
                "notes": "Indicative role-based state map entry for Maize.",
                "updated_at": UPDATED_AT,
            },
            {
                "state_name": "Maharashtra",
                "commodity_key": "maize",
                "production_role": "major producer and feed market",
                "indicative_share_pct": 11.0,
                "acreage_strength": "medium",
                "yield_strength": "medium",
                "major_varieties": "feed maize",
                "end_use_orientation": "feed and industrial use",
                "source_name": "Curated Maize profile context",
                "source_url": str(MAIZE_SUPPORT_DB),
                "notes": "Indicative role-based state map entry for Maize.",
                "updated_at": UPDATED_AT,
            },
            {
                "state_name": "Bihar",
                "commodity_key": "maize",
                "production_role": "important rabi maize producer",
                "indicative_share_pct": 9.0,
                "acreage_strength": "medium",
                "yield_strength": "high",
                "major_varieties": "rabi maize, seed and feed maize",
                "end_use_orientation": "feed and trade",
                "source_name": "Curated Maize profile context",
                "source_url": str(MAIZE_SUPPORT_DB),
                "notes": "Indicative role-based state map entry for Maize.",
                "updated_at": UPDATED_AT,
            },
            {
                "state_name": "Telangana",
                "commodity_key": "maize",
                "production_role": "feed-linked producer",
                "indicative_share_pct": 8.0,
                "acreage_strength": "medium",
                "yield_strength": "medium",
                "major_varieties": "feed maize",
                "end_use_orientation": "poultry and feed",
                "source_name": "Curated Maize profile context",
                "source_url": str(MAIZE_SUPPORT_DB),
                "notes": "Indicative role-based state map entry for Maize.",
                "updated_at": UPDATED_AT,
            },
            {
                "state_name": "Rajasthan",
                "commodity_key": "maize",
                "production_role": "large kharif producer",
                "indicative_share_pct": 7.0,
                "acreage_strength": "high",
                "yield_strength": "medium",
                "major_varieties": "hybrid maize",
                "end_use_orientation": "trade and feed",
                "source_name": "Curated Maize profile context",
                "source_url": str(MAIZE_SUPPORT_DB),
                "notes": "Indicative role-based state map entry for Maize.",
                "updated_at": UPDATED_AT,
            },
        ],
    )

    insert_many(
        conn,
        "maize_harvest_calendar",
        [
            {"id": "maize-kar-kharif-sowing", "commodity_key": "maize", "state_name": "Karnataka", "stage_name": "Kharif sowing", "start_month": 6, "end_month": 7, "season_name": "kharif", "source_name": "Curated Maize calendar", "source_url": str(PROCESS_DOC), "notes": "Main monsoon sowing window.", "updated_at": UPDATED_AT},
            {"id": "maize-kar-kharif-harvest", "commodity_key": "maize", "state_name": "Karnataka", "stage_name": "Kharif harvest and arrivals", "start_month": 9, "end_month": 11, "season_name": "kharif", "source_name": "Curated Maize calendar", "source_url": str(PROCESS_DOC), "notes": "Primary arrival window.", "updated_at": UPDATED_AT},
            {"id": "maize-mp-kharif-sowing", "commodity_key": "maize", "state_name": "Madhya Pradesh", "stage_name": "Kharif sowing", "start_month": 6, "end_month": 7, "season_name": "kharif", "source_name": "Curated Maize calendar", "source_url": str(PROCESS_DOC), "notes": "Main sowing window.", "updated_at": UPDATED_AT},
            {"id": "maize-mp-kharif-harvest", "commodity_key": "maize", "state_name": "Madhya Pradesh", "stage_name": "Kharif harvest and arrivals", "start_month": 9, "end_month": 11, "season_name": "kharif", "source_name": "Curated Maize calendar", "source_url": str(PROCESS_DOC), "notes": "Main arrival window.", "updated_at": UPDATED_AT},
            {"id": "maize-mh-kharif-sowing", "commodity_key": "maize", "state_name": "Maharashtra", "stage_name": "Kharif sowing", "start_month": 6, "end_month": 7, "season_name": "kharif", "source_name": "Curated Maize calendar", "source_url": str(PROCESS_DOC), "notes": "Main sowing window.", "updated_at": UPDATED_AT},
            {"id": "maize-mh-kharif-harvest", "commodity_key": "maize", "state_name": "Maharashtra", "stage_name": "Kharif harvest and arrivals", "start_month": 9, "end_month": 11, "season_name": "kharif", "source_name": "Curated Maize calendar", "source_url": str(PROCESS_DOC), "notes": "Main arrival window.", "updated_at": UPDATED_AT},
            {"id": "maize-bh-rabi-sowing", "commodity_key": "maize", "state_name": "Bihar", "stage_name": "Rabi sowing", "start_month": 10, "end_month": 11, "season_name": "rabi", "source_name": "Curated Maize calendar", "source_url": str(PROCESS_DOC), "notes": "Important rabi maize sowing window.", "updated_at": UPDATED_AT},
            {"id": "maize-bh-rabi-harvest", "commodity_key": "maize", "state_name": "Bihar", "stage_name": "Rabi harvest", "start_month": 2, "end_month": 4, "season_name": "rabi", "source_name": "Curated Maize calendar", "source_url": str(PROCESS_DOC), "notes": "Important rabi maize harvest window.", "updated_at": UPDATED_AT},
            {"id": "maize-ts-kharif-sowing", "commodity_key": "maize", "state_name": "Telangana", "stage_name": "Kharif sowing", "start_month": 6, "end_month": 7, "season_name": "kharif", "source_name": "Curated Maize calendar", "source_url": str(PROCESS_DOC), "notes": "Main sowing window.", "updated_at": UPDATED_AT},
            {"id": "maize-ts-kharif-harvest", "commodity_key": "maize", "state_name": "Telangana", "stage_name": "Kharif harvest and arrivals", "start_month": 9, "end_month": 10, "season_name": "kharif", "source_name": "Curated Maize calendar", "source_url": str(PROCESS_DOC), "notes": "Main arrival window.", "updated_at": UPDATED_AT},
            {"id": "maize-ts-rabi-sowing", "commodity_key": "maize", "state_name": "Telangana", "stage_name": "Rabi sowing", "start_month": 10, "end_month": 11, "season_name": "rabi", "source_name": "Curated Maize calendar", "source_url": str(PROCESS_DOC), "notes": "Secondary sowing window.", "updated_at": UPDATED_AT},
            {"id": "maize-ts-rabi-harvest", "commodity_key": "maize", "state_name": "Telangana", "stage_name": "Rabi harvest", "start_month": 2, "end_month": 3, "season_name": "rabi", "source_name": "Curated Maize calendar", "source_url": str(PROCESS_DOC), "notes": "Secondary harvest window.", "updated_at": UPDATED_AT},
        ],
    )

    insert_many(
        conn,
        "maize_key_player_register",
        [
            {"id": "maize-player-farmers", "commodity_key": "maize", "player_name": "Maize farmers", "player_type": "producer", "role_description": "Primary suppliers of kharif and rabi Maize into mandi and private trade channels.", "geography_scope": "India", "source_name": "Curated Maize market structure", "source_url": str(PROCESS_DOC), "notes": "Core upstream market actor.", "updated_at": UPDATED_AT},
            {"id": "maize-player-feed", "commodity_key": "maize", "player_name": "Feed millers and poultry integrators", "player_type": "consumer", "role_description": "Largest organised demand block for Maize, highly sensitive to feed economics and placement cycles.", "geography_scope": "India feed belt", "source_name": "Curated Maize market structure", "source_url": str(PROCESS_DOC), "notes": "Key demand-side actor.", "updated_at": UPDATED_AT},
            {"id": "maize-player-starch", "commodity_key": "maize", "player_name": "Starch and processing industry", "player_type": "industrial_consumer", "role_description": "Industrial user group for starch, food ingredients, and processing-linked Maize demand.", "geography_scope": "India", "source_name": "Curated Maize market structure", "source_url": str(PROCESS_DOC), "notes": "Important industrial user block.", "updated_at": UPDATED_AT},
            {"id": "maize-player-ethanol", "commodity_key": "maize", "player_name": "Ethanol-linked buyers", "player_type": "policy_linked_consumer", "role_description": "Policy-sensitive industrial demand linked to blending and alternate feedstock economics.", "geography_scope": "India", "source_name": "Curated Maize market structure", "source_url": str(PROCESS_DOC), "notes": "Growing demand-side sensitivity block.", "updated_at": UPDATED_AT},
            {"id": "maize-player-traders", "commodity_key": "maize", "player_name": "Private traders and stockists", "player_type": "trade", "role_description": "Move Maize across states, manage stock positions, and connect mandi arrivals to end-use channels.", "geography_scope": "India", "source_name": "Curated Maize market structure", "source_url": str(PROCESS_DOC), "notes": "Core physical market intermediary.", "updated_at": UPDATED_AT},
            {"id": "maize-player-exporters", "commodity_key": "maize", "player_name": "Exporters and importers", "player_type": "trade", "role_description": "Link domestic Maize pricing to international corridor opportunities and import pressure when needed.", "geography_scope": "India + Global", "source_name": "DGCI&S TradeStat", "source_url": "https://tradestat.commerce.gov.in/", "notes": "Trade-linked external-facing market actor.", "updated_at": UPDATED_AT},
        ],
    )

    conn.close()


if __name__ == "__main__":
    build()
    print(f"Built {OUTPUT_DB}")
