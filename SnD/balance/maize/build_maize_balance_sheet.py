from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / 'maize_balance_sheet.db'
SUPPLY_DB = ROOT / 'SnD' / 'supply' / 'maize' / 'maize_supply_factors.db'
DEMAND_DB = ROOT / 'SnD' / 'demand' / 'maize' / 'maize_demand_monthly.db'
UPDATED_AT = datetime.now(UTC).isoformat().replace('+00:00', 'Z')


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def crop_year_from_month(month_iso: str) -> str:
    year = int(month_iso[:4])
    month = int(month_iso[5:7])
    if month >= 10:
        start_year = year
    else:
        start_year = year - 1
    return f"{start_year}/{str(start_year + 1)[-2:]}"


def month_num(month_iso: str) -> int:
    return int(month_iso[5:7])


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS maize_balance_monthly (
            id TEXT PRIMARY KEY,
            metric_month TEXT NOT NULL,
            marketing_year TEXT NOT NULL,
            crop_year TEXT NOT NULL,
            opening_stock REAL NOT NULL,
            domestic_production REAL NOT NULL,
            imports REAL NOT NULL,
            total_availability REAL NOT NULL,
            total_demand_monthly REAL NOT NULL,
            delta REAL NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(metric_month)
        );

        CREATE TABLE IF NOT EXISTS maize_balance_annual (
            crop_year TEXT PRIMARY KEY,
            year_start_month TEXT NOT NULL,
            year_end_month TEXT NOT NULL,
            month_count INTEGER NOT NULL,
            is_full_crop_year INTEGER NOT NULL,
            opening_stock_start REAL NOT NULL,
            domestic_production_sum REAL NOT NULL,
            imports_sum REAL NOT NULL,
            total_availability_sum REAL NOT NULL,
            total_demand_sum REAL NOT NULL,
            delta_sum REAL NOT NULL,
            ending_stock_end REAL NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_stocks_to_use (
            crop_year TEXT PRIMARY KEY,
            month_count INTEGER NOT NULL,
            is_full_crop_year INTEGER NOT NULL,
            ending_stock REAL NOT NULL,
            total_demand REAL NOT NULL,
            stocks_to_use_ratio REAL,
            stocks_to_use_pct REAL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def reset(conn: sqlite3.Connection) -> None:
    for table in ('maize_balance_monthly', 'maize_balance_annual', 'maize_stocks_to_use'):
        conn.execute(f'DELETE FROM {table}')
    conn.commit()


def load_monthly_components() -> list[sqlite3.Row]:
    supply = connect(SUPPLY_DB)
    demand = connect(DEMAND_DB)

    supply_rows = supply.execute(
        """
        SELECT metric_month,
               MAX(CASE WHEN factor_key = 'opening_stock' THEN value END) AS opening_stock,
               MAX(CASE WHEN factor_key = 'domestic_production' THEN value END) AS domestic_production,
               MAX(CASE WHEN factor_key = 'imports' THEN value END) AS imports,
               MAX(CASE WHEN factor_key = 'total_availability' THEN value END) AS total_availability
        FROM maize_factor_monthly_values
        WHERE geography = 'India'
          AND factor_key IN ('opening_stock', 'domestic_production', 'imports', 'total_availability')
        GROUP BY metric_month
        ORDER BY metric_month
        """
    ).fetchall()

    demand_map = {
        row['metric_month']: float(row['value'] or 0.0)
        for row in demand.execute(
            """
            SELECT metric_month, value
            FROM maize_factor_monthly_values
            WHERE factor_key = 'total_demand_monthly'
            ORDER BY metric_month
            """
        ).fetchall()
    }

    supply.close()
    demand.close()

    merged: list[dict] = []
    for row in supply_rows:
        metric_month = row['metric_month']
        opening_stock = float(row['opening_stock'] or 0.0)
        domestic_production = float(row['domestic_production'] or 0.0)
        imports = float(row['imports'] or 0.0)
        total_availability = float(row['total_availability'] or (opening_stock + domestic_production + imports))
        total_demand = float(demand_map.get(metric_month, 0.0))
        merged.append(
            {
                'metric_month': metric_month,
                'marketing_year': f"{metric_month[:4]}/{str(int(metric_month[:4]) + 1)[-2:]}",
                'crop_year': crop_year_from_month(metric_month),
                'opening_stock': round(opening_stock, 6),
                'domestic_production': round(domestic_production, 6),
                'imports': round(imports, 6),
                'total_availability': round(total_availability, 6),
                'total_demand_monthly': round(total_demand, 6),
                'delta': round(total_availability - total_demand, 6),
            }
        )

    return merged


def build_monthly_rows(conn: sqlite3.Connection, monthly_rows: list[dict]) -> None:
    conn.executemany(
        """
        INSERT INTO maize_balance_monthly (
            id, metric_month, marketing_year, crop_year,
            opening_stock, domestic_production, imports,
            total_availability, total_demand_monthly, delta, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                f"maize-balance-monthly-{idx:04d}",
                row['metric_month'],
                row['marketing_year'],
                row['crop_year'],
                row['opening_stock'],
                row['domestic_production'],
                row['imports'],
                row['total_availability'],
                row['total_demand_monthly'],
                row['delta'],
                UPDATED_AT,
            )
            for idx, row in enumerate(monthly_rows, start=1)
        ],
    )
    conn.commit()


def build_annual_rows(conn: sqlite3.Connection, monthly_rows: list[dict]) -> None:
    by_year: dict[str, list[dict]] = {}
    for row in monthly_rows:
        by_year.setdefault(row['crop_year'], []).append(row)

    annual_payload = []
    stocks_payload = []

    for crop_year, rows in sorted(by_year.items(), key=lambda x: x[0]):
        rows_sorted = sorted(rows, key=lambda x: x['metric_month'])
        start = rows_sorted[0]['metric_month']
        end = rows_sorted[-1]['metric_month']
        month_count = len(rows_sorted)

        months_present = {month_num(r['metric_month']) for r in rows_sorted}
        full_set = {10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9}
        is_full = 1 if month_count == 12 and months_present == full_set else 0

        opening_start = float(rows_sorted[0]['opening_stock'])
        production_sum = round(sum(float(r['domestic_production']) for r in rows_sorted), 6)
        imports_sum = round(sum(float(r['imports']) for r in rows_sorted), 6)
        availability_sum = round(sum(float(r['total_availability']) for r in rows_sorted), 6)
        demand_sum = round(sum(float(r['total_demand_monthly']) for r in rows_sorted), 6)
        delta_sum = round(sum(float(r['delta']) for r in rows_sorted), 6)
        ending_stock = round(float(rows_sorted[-1]['opening_stock']), 6)

        annual_payload.append(
            (
                crop_year,
                start,
                end,
                month_count,
                is_full,
                opening_start,
                production_sum,
                imports_sum,
                availability_sum,
                demand_sum,
                delta_sum,
                ending_stock,
                UPDATED_AT,
            )
        )

        ratio = None
        pct = None
        if demand_sum > 0:
            ratio = round(ending_stock / demand_sum, 6)
            pct = round(ratio * 100.0, 4)

        stocks_payload.append(
            (
                crop_year,
                month_count,
                is_full,
                ending_stock,
                demand_sum,
                ratio,
                pct,
                UPDATED_AT,
            )
        )

    conn.executemany(
        """
        INSERT INTO maize_balance_annual (
            crop_year, year_start_month, year_end_month, month_count, is_full_crop_year,
            opening_stock_start, domestic_production_sum, imports_sum,
            total_availability_sum, total_demand_sum, delta_sum, ending_stock_end, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        annual_payload,
    )

    conn.executemany(
        """
        INSERT INTO maize_stocks_to_use (
            crop_year, month_count, is_full_crop_year, ending_stock, total_demand,
            stocks_to_use_ratio, stocks_to_use_pct, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        stocks_payload,
    )
    conn.commit()


def build() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect(OUTPUT_DB)
    ensure_schema(conn)
    reset(conn)

    monthly_rows = load_monthly_components()
    build_monthly_rows(conn, monthly_rows)
    build_annual_rows(conn, monthly_rows)

    monthly_range = conn.execute("SELECT MIN(metric_month), MAX(metric_month), COUNT(*) FROM maize_balance_monthly").fetchone()
    annual_count = conn.execute("SELECT COUNT(*) FROM maize_balance_annual").fetchone()[0]
    stu_count = conn.execute("SELECT COUNT(*) FROM maize_stocks_to_use").fetchone()[0]
    conn.close()

    print(
        {
            'db_path': str(OUTPUT_DB),
            'maize_balance_monthly': monthly_range[2],
            'monthly_range': [monthly_range[0], monthly_range[1]],
            'maize_balance_annual': annual_count,
            'maize_stocks_to_use': stu_count,
        }
    )


if __name__ == '__main__':
    build()
