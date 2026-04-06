from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


FEATURE_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "wheat_model_support.db"
START_MONTH = "2016-04-01"
WORLD_BANK_PINK_SHEET_URL = (
    "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
    "CMO-Historical-Data-Monthly.xlsx"
)

PROCUREMENT_ROWS = [
    {
        "signal_date": "2024-09-01",
        "signal_group": "procurement",
        "signal_name": "Actual wheat procurement",
        "marketing_season": "RMS 2023-24",
        "value": 262.02,
        "unit": "LMT",
        "source_name": "DFPD Bulletin",
        "source_url": "https://dfpd.gov.in/WriteReadData/FoodBulletinUploadDocuments/b14c0cd3-c3dd-4e36-8cdd-26542a7b237f_FoodgrainBulletinforSeptember23.pdf",
        "notes": "Official bulletin reference showing previous season procurement of 262.02 LMT.",
    },
    {
        "signal_date": "2025-10-27",
        "signal_group": "procurement",
        "signal_name": "Actual wheat procurement",
        "marketing_season": "RMS 2024-25",
        "value": 266.00,
        "unit": "LMT",
        "source_name": "PIB",
        "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2177219",
        "notes": "Official PIB note stating FCI procured 266 LMT during RMS 2024-25.",
    },
    {
        "signal_date": "2025-10-01",
        "signal_group": "procurement",
        "signal_name": "Estimated wheat procurement",
        "marketing_season": "RMS 2026-27",
        "value": 297.00,
        "unit": "LMT",
        "source_name": "PIB",
        "source_url": "https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/oct/doc20251010662401.pdf",
        "notes": "Official procurement estimate for RMS 2026-27 used with MSP announcement.",
    },
    {
        "signal_date": "2026-03-22",
        "signal_group": "procurement",
        "signal_name": "Actual wheat procurement",
        "marketing_season": "RMS 2025-26",
        "value": 300.35,
        "unit": "LMT",
        "source_name": "PIB",
        "source_url": "https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/mar/doc2026315825201.pdf",
        "notes": "Official PIB document describing 300.35 LMT procured in RMS 2025-26.",
    },
]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(FEATURE_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS global_wheat_benchmark_monthly (
            benchmark_month TEXT PRIMARY KEY,
            wheat_us_srw REAL,
            wheat_us_hrw REAL,
            benchmark_average REAL,
            unit TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def _load_world_bank_wheat_series() -> pd.DataFrame:
    raw = pd.read_excel(
        WORLD_BANK_PINK_SHEET_URL,
        sheet_name="Monthly Prices",
        header=4,
    )
    raw = raw.iloc[2:].copy()
    date_column = raw.columns[0]
    srw_column = "Wheat, US SRW"
    hrw_column = "Wheat, US HRW"
    frame = raw[[date_column, srw_column, hrw_column]].copy()
    frame = frame.rename(
        columns={
            date_column: "benchmark_month",
            srw_column: "wheat_us_srw",
            hrw_column: "wheat_us_hrw",
        }
    )
    frame = frame[frame["benchmark_month"].astype(str).str.match(r"^\d{4}M\d{2}$", na=False)]
    frame["benchmark_month"] = pd.to_datetime(frame["benchmark_month"], format="%YM%m").dt.strftime("%Y-%m-01")
    frame["wheat_us_srw"] = pd.to_numeric(frame["wheat_us_srw"], errors="coerce")
    frame["wheat_us_hrw"] = pd.to_numeric(frame["wheat_us_hrw"], errors="coerce")
    frame = frame.dropna(subset=["wheat_us_srw", "wheat_us_hrw"], how="all")
    frame = frame[frame["benchmark_month"] >= START_MONTH].copy()
    frame["benchmark_average"] = frame[["wheat_us_srw", "wheat_us_hrw"]].mean(axis=1, skipna=True)
    frame["unit"] = "USD/MT"
    frame["source_name"] = "World Bank Pink Sheet"
    frame["source_url"] = WORLD_BANK_PINK_SHEET_URL
    frame["updated_at"] = datetime.utcnow().isoformat() + "Z"
    return frame


def _upsert_global_benchmark(conn: sqlite3.Connection, frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0
    conn.executemany(
        """
        INSERT INTO global_wheat_benchmark_monthly
        (benchmark_month, wheat_us_srw, wheat_us_hrw, benchmark_average, unit, source_name, source_url, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(benchmark_month) DO UPDATE SET
            wheat_us_srw=excluded.wheat_us_srw,
            wheat_us_hrw=excluded.wheat_us_hrw,
            benchmark_average=excluded.benchmark_average,
            unit=excluded.unit,
            source_name=excluded.source_name,
            source_url=excluded.source_url,
            updated_at=excluded.updated_at
        """,
        frame.itertuples(index=False, name=None),
    )
    conn.commit()
    return int(len(frame))


def _upsert_procurement_signals(conn: sqlite3.Connection) -> int:
    now = datetime.utcnow().isoformat() + "Z"
    payload = [
        {
            **row,
            "id": str(uuid.uuid4()),
            "created_at": now,
        }
        for row in PROCUREMENT_ROWS
    ]
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
        payload,
    )
    conn.execute(
        """
        UPDATE wheat_data_inventory
        SET status = ?, notes = ?, updated_at = ?
        WHERE signal_key = 'procurement_volumes'
        """,
        (
            "loaded",
            "Historical seasonal procurement references plus latest official PIB/DFPD procurement updates are loaded.",
            now,
        ),
    )
    conn.execute(
        """
        UPDATE wheat_data_inventory
        SET status = ?, notes = ?, updated_at = ?
        WHERE signal_key = 'global_wheat_benchmark'
        """,
        (
            "loaded",
            f"Monthly World Bank Pink Sheet wheat benchmarks loaded from {START_MONTH} onward.",
            now,
        ),
    )
    conn.commit()
    return len(payload)


def run() -> dict[str, Any]:
    benchmark = _load_world_bank_wheat_series()
    with _connect() as conn:
        _ensure_schema(conn)
        benchmark_rows = _upsert_global_benchmark(conn, benchmark)
        procurement_rows = _upsert_procurement_signals(conn)

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM global_wheat_benchmark_monthly")
        benchmark_total = cur.fetchone()[0]
        cur.execute("SELECT MIN(benchmark_month), MAX(benchmark_month) FROM global_wheat_benchmark_monthly")
        benchmark_range = cur.fetchone()
        cur.execute(
            "SELECT signal_key, status FROM wheat_data_inventory WHERE signal_key IN ('procurement_volumes','global_wheat_benchmark') ORDER BY signal_key"
        )
        inventory_status = cur.fetchall()

    return {
        "status": "success",
        "feature_db_path": str(FEATURE_DB_PATH),
        "loaded_benchmark_rows": benchmark_rows,
        "loaded_procurement_rows": procurement_rows,
        "benchmark_total_rows": benchmark_total,
        "benchmark_date_range": benchmark_range,
        "inventory_status": inventory_status,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
