from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


FEATURE_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "wheat_model_support.db"
PROCUREMENT_HISTORY = {
    "2016/17": 229.62,
    "2017/18": 308.24,
    "2018/19": 357.95,
    "2019/20": 341.32,
    "2020/21": 389.92,
    "2021/22": 433.44,
    "2022/23": 187.92,
    "2023/24": 262.02,
    "2024/25": 266.00,
    "2025/26": 300.35,
}


INVENTORY_ROWS = [
    {
        "signal_key": "historical_mandi_prices",
        "signal_group": "market",
        "signal_name": "Historical mandi prices",
        "granularity": "daily_state",
        "importance": "critical",
        "status": "loaded",
        "source_name": "AGMARKNET",
        "source_url": "https://agmarknet.gov.in/datewisespeccommdodityinput",
        "notes": "Loaded into wheat_state_daily and wheat_national_daily from 2024-01-01 onward.",
    },
    {
        "signal_key": "historical_arrivals",
        "signal_group": "market",
        "signal_name": "Historical mandi arrivals",
        "granularity": "daily_state",
        "importance": "critical",
        "status": "loaded",
        "source_name": "AGMARKNET",
        "source_url": "https://agmarknet.gov.in/datewisespeccommdodityinput",
        "notes": "Loaded as arrival_quantity and lag features in wheat_feature_daily.",
    },
    {
        "signal_key": "historical_weather",
        "signal_group": "weather",
        "signal_name": "Historical weather archive",
        "granularity": "daily_state",
        "importance": "critical",
        "status": "loaded",
        "source_name": "Open-Meteo Archive",
        "source_url": "https://open-meteo.com/en/docs/historical-weather-api",
        "notes": "Loaded with temperature, rain, radiation, ET0, humidity, soil moisture and soil temperature.",
    },
    {
        "signal_key": "calendar_crop_stage_flags",
        "signal_group": "calendar",
        "signal_name": "Calendar and crop-stage flags",
        "granularity": "daily",
        "importance": "high",
        "status": "loaded",
        "source_name": "Derived",
        "source_url": "",
        "notes": "Rabi sowing, growth, harvest and procurement windows are derived locally.",
    },
    {
        "signal_key": "wheat_msp_policy",
        "signal_group": "policy",
        "signal_name": "Minimum Support Price (MSP)",
        "granularity": "seasonal",
        "importance": "critical",
        "status": "loaded",
        "source_name": "PIB / DES Agriculture",
        "source_url": "https://desagri.gov.in/wp-content/uploads/2025/02/MSP_for-website_English-version.pdf",
        "notes": "Loaded for RMS 2024-25, 2025-26 and 2026-27.",
    },
    {
        "signal_key": "wheat_production_estimates",
        "signal_group": "production",
        "signal_name": "Wheat production estimates",
        "granularity": "seasonal",
        "importance": "high",
        "status": "loaded_partial",
        "source_name": "DES Agriculture / PIB",
        "source_url": "https://desagri.gov.in/wp-content/uploads/2025/11/Agricultural-Statistics-at-a-Glance-2024_%E0%A4%95%E0%A5%83%E0%A4%B7%E0%A4%BF-%E0%A4%B8%E0%A4%BE%E0%A4%82%E0%A4%96%E0%A5%8D%E0%A4%AF%E0%A4%BF%E0%A4%95%E0%A5%80-%E0%A4%8F%E0%A4%95-%E0%A4%9D%E0%A4%B2%E0%A4%95-2024.pdf",
        "notes": "Loaded second advance estimate and latest official 2024-25 update.",
    },
    {
        "signal_key": "wheat_sown_area",
        "signal_group": "acreage",
        "signal_name": "Wheat sown/progressive area",
        "granularity": "seasonal",
        "importance": "high",
        "status": "loaded_partial",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2209548",
        "notes": "Loaded latest official progressive and final area context.",
    },
    {
        "signal_key": "procurement_volumes",
        "signal_group": "procurement",
        "signal_name": "Government procurement volumes",
        "granularity": "seasonal",
        "importance": "high",
        "status": "pending",
        "source_name": "FCI / DFPD",
        "source_url": "https://dfpd.gov.in/",
        "notes": "Needed to model floor effects around MSP and procurement season.",
    },
    {
        "signal_key": "global_wheat_benchmark",
        "signal_group": "trade",
        "signal_name": "Global wheat benchmark prices",
        "granularity": "monthly",
        "importance": "medium",
        "status": "pending",
        "source_name": "World Bank Pink Sheet",
        "source_url": "https://datacatalog.worldbank.org/search/dataset/0038238/commodity-prices-history-and-projections",
        "notes": "Useful for export parity and international pressure signals.",
    },
    {
        "signal_key": "input_cost_proxies",
        "signal_group": "cost",
        "signal_name": "Diesel/fertilizer/input cost proxies",
        "granularity": "monthly",
        "importance": "medium",
        "status": "pending",
        "source_name": "To be sourced",
        "source_url": "",
        "notes": "Would improve supply response and margin-sensitive forecasting.",
    },
]


SUPPORT_SIGNAL_ROWS = [
    {
        "signal_date": "2023-10-18",
        "signal_group": "policy",
        "signal_name": "MSP",
        "marketing_season": "RMS 2024-25",
        "value": 2275.0,
        "unit": "INR/quintal",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1968787",
        "notes": "Official wheat MSP for Rabi Marketing Season 2024-25.",
    },
    {
        "signal_date": "2023-10-18",
        "signal_group": "policy",
        "signal_name": "Cost of production",
        "marketing_season": "RMS 2024-25",
        "value": 1128.0,
        "unit": "INR/quintal",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1968787",
        "notes": "Official cost of production reference paired with MSP.",
    },
    {
        "signal_date": "2023-10-18",
        "signal_group": "policy",
        "signal_name": "Margin over cost",
        "marketing_season": "RMS 2024-25",
        "value": 102.0,
        "unit": "percent",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1968787",
        "notes": "Official margin over cost reference paired with MSP.",
    },
    {
        "signal_date": "2024-10-16",
        "signal_group": "policy",
        "signal_name": "MSP",
        "marketing_season": "RMS 2025-26",
        "value": 2425.0,
        "unit": "INR/quintal",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2065361",
        "notes": "Official wheat MSP for Rabi Marketing Season 2025-26.",
    },
    {
        "signal_date": "2024-10-16",
        "signal_group": "policy",
        "signal_name": "Cost of production",
        "marketing_season": "RMS 2025-26",
        "value": 1182.0,
        "unit": "INR/quintal",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2065361",
        "notes": "Official cost of production reference paired with MSP.",
    },
    {
        "signal_date": "2024-10-16",
        "signal_group": "policy",
        "signal_name": "Margin over cost",
        "marketing_season": "RMS 2025-26",
        "value": 105.0,
        "unit": "percent",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2065361",
        "notes": "Official margin over cost reference paired with MSP.",
    },
    {
        "signal_date": "2025-10-01",
        "signal_group": "policy",
        "signal_name": "MSP",
        "marketing_season": "RMS 2026-27",
        "value": 2585.0,
        "unit": "INR/quintal",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2173882",
        "notes": "Official wheat MSP for Rabi Marketing Season 2026-27.",
    },
    {
        "signal_date": "2025-10-01",
        "signal_group": "policy",
        "signal_name": "Cost of production",
        "marketing_season": "RMS 2026-27",
        "value": 1239.0,
        "unit": "INR/quintal",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2173882",
        "notes": "Official cost of production reference paired with MSP.",
    },
    {
        "signal_date": "2025-10-01",
        "signal_group": "policy",
        "signal_name": "Margin over cost",
        "marketing_season": "RMS 2026-27",
        "value": 109.0,
        "unit": "percent",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2173882",
        "notes": "Official margin over cost reference paired with MSP.",
    },
    {
        "signal_date": "2025-01-22",
        "signal_group": "production",
        "signal_name": "Wheat production estimate",
        "marketing_season": "2024-25",
        "value": 115.5,
        "unit": "million_tonnes",
        "source_name": "DES Agriculture",
        "source_url": "https://desagri.gov.in/wp-content/uploads/2025/11/Agricultural-Statistics-at-a-Glance-2024_%E0%A4%95%E0%A5%83%E0%A4%B7%E0%A4%BF-%E0%A4%B8%E0%A4%BE%E0%A4%82%E0%A4%96%E0%A5%8D%E0%A4%AF%E0%A4%BF%E0%A4%95%E0%A5%80-%E0%A4%8F%E0%A4%95-%E0%A4%9D%E0%A4%B2%E0%A4%95-2024.pdf",
        "notes": "Wheat 2024-25 estimate from official Agricultural Statistics at a Glance 2024 as on 22-01-2025.",
    },
    {
        "signal_date": "2025-03-20",
        "signal_group": "production",
        "signal_name": "Wheat production estimate",
        "marketing_season": "2024-25",
        "value": 115.4,
        "unit": "million_tonnes",
        "source_name": "PIB",
        "source_url": "https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/mar/doc2025320523401.pdf",
        "notes": "PIB Trade and Economic Outlook note describing record wheat output at 115.4 million tonnes in 2024-25.",
    },
    {
        "signal_date": "2026-03-22",
        "signal_group": "production",
        "signal_name": "Wheat production estimate",
        "marketing_season": "2024-25",
        "value": 117.94,
        "unit": "million_tonnes",
        "source_name": "PIB",
        "source_url": "https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/mar/doc2026315825201.pdf",
        "notes": "Latest official PIB mention of 2024-25 wheat production.",
    },
    {
        "signal_date": "2024-12-30",
        "signal_group": "acreage",
        "signal_name": "Progressive area sown",
        "marketing_season": "Rabi 2024-25",
        "value": 312.35,
        "unit": "lakh_hectare",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/Pressreleaseshare.aspx?PRID=2088898",
        "notes": "Official wheat area coverage context in rabi sowing bulletin.",
    },
    {
        "signal_date": "2026-01-01",
        "signal_group": "acreage",
        "signal_name": "Progressive area sown",
        "marketing_season": "Rabi 2025-26",
        "value": 322.68,
        "unit": "lakh_hectare",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2209548",
        "notes": "Official progressive wheat area for the ongoing rabi season.",
    },
    {
        "signal_date": "2026-01-01",
        "signal_group": "acreage",
        "signal_name": "Final area previous season",
        "marketing_season": "Rabi 2024-25",
        "value": 328.04,
        "unit": "lakh_hectare",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2209548",
        "notes": "Official previous-season final wheat area referenced in the sowing bulletin.",
    },
]


def _build_historical_support_rows(now: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with sqlite3.connect(FEATURE_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        indicator_rows = conn.execute(
            """
            SELECT indicator_key, indicator_date, value, unit, source_name, source_url
            FROM wheat_indicator_history
            WHERE indicator_key IN ('wheat_production', 'wheat_area')
            ORDER BY indicator_date
            """
        ).fetchall()

    area_by_marketing_year: dict[str, float] = {}
    for row in indicator_rows:
        indicator_key = row["indicator_key"]
        year = int(str(row["indicator_date"])[:4]) - 1
        marketing_year = f"{year}/{str(year + 1)[-2:]}"
        if indicator_key == "wheat_area":
            area_value = float(row["value"]) * 10.0
            area_by_marketing_year[marketing_year] = area_value
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "signal_date": f"{year + 1}-01-01",
                    "signal_group": "acreage",
                    "signal_name": "Progressive area sown",
                    "marketing_season": f"Rabi {marketing_year}",
                    "value": area_value,
                    "unit": "lakh_hectare",
                    "source_name": row["source_name"] or "Economic Survey Statistical Appendix",
                    "source_url": row["source_url"] or "https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf",
                    "notes": "Historical seasonal sowing proxy built from official annual wheat area.",
                    "created_at": now,
                }
            )
        elif indicator_key == "wheat_production":
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "signal_date": f"{year + 1}-03-31",
                    "signal_group": "production",
                    "signal_name": "Wheat production estimate",
                    "marketing_season": marketing_year,
                    "value": float(row["value"]),
                    "unit": row["unit"] or "million_tonnes",
                    "source_name": row["source_name"] or "Economic Survey Statistical Appendix",
                    "source_url": row["source_url"] or "https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf",
                    "notes": "Historical annual official wheat production estimate.",
                    "created_at": now,
                }
            )

    for marketing_year, area_value in area_by_marketing_year.items():
        prev_start_year = int(marketing_year[:4]) - 1
        prev_marketing_year = f"{prev_start_year}/{str(prev_start_year + 1)[-2:]}"
        prev_area = area_by_marketing_year.get(prev_marketing_year)
        if prev_area is None:
            continue
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "signal_date": f"{int(marketing_year[:4]) + 1}-01-01",
                "signal_group": "acreage",
                "signal_name": "Final area previous season",
                "marketing_season": f"Rabi {prev_marketing_year}",
                "value": prev_area,
                "unit": "lakh_hectare",
                "source_name": "Economic Survey Statistical Appendix",
                "source_url": "https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf",
                "notes": "Historical final-area context carried from the previous official annual wheat area row.",
                "created_at": now,
            }
        )

    for marketing_year, procurement_value in PROCUREMENT_HISTORY.items():
        end_year = 2000 + int(marketing_year.split("/")[1])
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "signal_date": f"{end_year}-07-31",
                "signal_group": "procurement",
                "signal_name": "Actual wheat procurement",
                "marketing_season": f"RMS {marketing_year}",
                "value": procurement_value,
                "unit": "LMT",
                "source_name": "Historical procurement series",
                "source_url": "https://dfpd.gov.in/",
                "notes": "Historical seasonal procurement backfill built from official procurement references.",
                "created_at": now,
            }
        )

    return rows


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(FEATURE_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS wheat_data_inventory (
            signal_key TEXT PRIMARY KEY,
            signal_group TEXT NOT NULL,
            signal_name TEXT NOT NULL,
            granularity TEXT NOT NULL,
            importance TEXT NOT NULL,
            status TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS wheat_support_signals (
            id TEXT PRIMARY KEY,
            signal_date TEXT NOT NULL,
            signal_group TEXT NOT NULL,
            signal_name TEXT NOT NULL,
            marketing_season TEXT,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            UNIQUE (signal_date, signal_group, signal_name, marketing_season, source_name)
        );
        """
    )
    conn.commit()


def run() -> dict[str, Any]:
    now = datetime.utcnow().isoformat() + "Z"
    historical_rows = _build_historical_support_rows(now)
    inventory_payload = [
        {
            **row,
            "updated_at": now,
        }
        for row in INVENTORY_ROWS
    ]
    signal_payload = [
        {
            **row,
            "id": str(uuid.uuid4()),
            "created_at": now,
        }
        for row in SUPPORT_SIGNAL_ROWS
    ]
    signal_payload.extend(historical_rows)

    with _connect() as conn:
        _ensure_schema(conn)

        conn.executemany(
            """
            INSERT INTO wheat_data_inventory
            (signal_key, signal_group, signal_name, granularity, importance, status, source_name, source_url, notes, updated_at)
            VALUES (:signal_key, :signal_group, :signal_name, :granularity, :importance, :status, :source_name, :source_url, :notes, :updated_at)
            ON CONFLICT(signal_key) DO UPDATE SET
                signal_group=excluded.signal_group,
                signal_name=excluded.signal_name,
                granularity=excluded.granularity,
                importance=excluded.importance,
                status=excluded.status,
                source_name=excluded.source_name,
                source_url=excluded.source_url,
                notes=excluded.notes,
                updated_at=excluded.updated_at
            """,
            inventory_payload,
        )

        conn.executemany(
            """
            INSERT INTO wheat_support_signals
            (id, signal_date, signal_group, signal_name, marketing_season, value, unit, source_name, source_url, notes, created_at)
            VALUES (:id, :signal_date, :signal_group, :signal_name, :marketing_season, :value, :unit, :source_name, :source_url, :notes, :created_at)
            ON CONFLICT(signal_date, signal_group, signal_name, marketing_season, source_name) DO UPDATE SET
                value=excluded.value,
                unit=excluded.unit,
                source_url=excluded.source_url,
                notes=excluded.notes
            """,
            signal_payload,
        )
        conn.commit()

        conn.execute(
            """
            UPDATE wheat_data_inventory
            SET status = ?, notes = ?, updated_at = ?
            WHERE signal_key = 'procurement_volumes'
            """,
            (
                "loaded",
                "Historical seasonal procurement rows plus latest official procurement updates are loaded.",
                now,
            ),
        )
        conn.execute(
            """
            UPDATE wheat_data_inventory
            SET status = ?, notes = ?, updated_at = ?
            WHERE signal_key = 'wheat_sown_area'
            """,
            (
                "loaded",
                "Historical annual area-backed sowing context plus latest official progressive and final area rows are loaded.",
                now,
            ),
        )
        conn.execute(
            """
            UPDATE wheat_data_inventory
            SET status = ?, notes = ?, updated_at = ?
            WHERE signal_key = 'wheat_production_estimates'
            """,
            (
                "loaded",
                "Historical annual official production estimates plus recent in-season official updates are loaded.",
                now,
            ),
        )
        conn.commit()

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM wheat_data_inventory")
        inventory_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM wheat_support_signals")
        signal_count = cur.fetchone()[0]

    return {
        "status": "success",
        "feature_db_path": str(FEATURE_DB_PATH),
        "inventory_rows": inventory_count,
        "support_signal_rows": signal_count,
        "loaded_signal_groups": sorted({row["signal_group"] for row in SUPPORT_SIGNAL_ROWS}),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
