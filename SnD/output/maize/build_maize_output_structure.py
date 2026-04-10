from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / 'maize_output_structure.db'
BALANCE_DB = ROOT / 'SnD' / 'balance' / 'maize' / 'maize_balance_sheet.db'
SCENARIO_DB = ROOT / 'SnD' / 'scenarios' / 'maize' / 'maize_scenarios.db'
DRIVER_DB = ROOT / 'SnD' / 'price_drivers' / 'maize' / 'maize_price_drivers.db'
DEMAND_DB = ROOT / 'SnD' / 'demand' / 'maize' / 'maize_demand_monthly.db'
SUPPLY_DB = ROOT / 'SnD' / 'supply' / 'maize' / 'maize_supply_factors.db'
UPDATED_AT = datetime.now(UTC).isoformat().replace('+00:00', 'Z')


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS maize_output_blocks (
            block_key TEXT PRIMARY KEY,
            block_name TEXT NOT NULL,
            description TEXT NOT NULL,
            primary_source_layer TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_output_balance_sheet (
            id TEXT PRIMARY KEY,
            metric_month TEXT NOT NULL,
            crop_year TEXT NOT NULL,
            opening_stock REAL,
            production REAL,
            imports REAL,
            total_availability REAL,
            total_demand REAL,
            delta REAL,
            ending_stock_sim REAL,
            source_tag TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(metric_month)
        );

        CREATE TABLE IF NOT EXISTS maize_output_stocks_to_use_chart (
            crop_year TEXT PRIMARY KEY,
            month_count INTEGER NOT NULL,
            stocks_to_use_ratio REAL,
            stocks_to_use_pct REAL,
            classification TEXT NOT NULL,
            source_name TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_output_price_correlation (
            metric_month TEXT PRIMARY KEY,
            domestic_price_index REAL NOT NULL,
            global_price_proxy_index REAL NOT NULL,
            rolling_corr_3m REAL,
            rolling_corr_6m REAL,
            source_name TEXT NOT NULL,
            source_url TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_output_risk_flags (
            id TEXT PRIMARY KEY,
            metric_month TEXT NOT NULL,
            risk_type TEXT NOT NULL,
            risk_score REAL NOT NULL,
            severity TEXT NOT NULL,
            trigger_rule TEXT NOT NULL,
            narrative TEXT NOT NULL,
            source_layer TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_output_scenario_summary (
            id TEXT PRIMARY KEY,
            scenario_key TEXT NOT NULL,
            scenario_name TEXT NOT NULL,
            crop_year TEXT NOT NULL,
            price_low REAL NOT NULL,
            price_mid REAL NOT NULL,
            price_high REAL NOT NULL,
            confidence TEXT NOT NULL,
            note TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(scenario_key, crop_year)
        );

        CREATE TABLE IF NOT EXISTS maize_output_snapshot (
            snapshot_date TEXT PRIMARY KEY,
            current_regime TEXT NOT NULL,
            top_bullish_drivers TEXT NOT NULL,
            top_bearish_drivers TEXT NOT NULL,
            suggested_range TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def reset(conn: sqlite3.Connection) -> None:
    for t in [
        'maize_output_blocks',
        'maize_output_balance_sheet',
        'maize_output_stocks_to_use_chart',
        'maize_output_price_correlation',
        'maize_output_risk_flags',
        'maize_output_scenario_summary',
        'maize_output_snapshot',
    ]:
        conn.execute(f'DELETE FROM {t}')
    conn.commit()


def correlation(a: list[float], b: list[float]) -> float | None:
    n = len(a)
    if n == 0 or n != len(b):
        return None
    ma = sum(a) / n
    mb = sum(b) / n
    da = [x - ma for x in a]
    db = [y - mb for y in b]
    va = sum(x * x for x in da)
    vb = sum(y * y for y in db)
    if va <= 1e-12 or vb <= 1e-12:
        return None
    cov = sum(x * y for x, y in zip(da, db))
    return cov / ((va ** 0.5) * (vb ** 0.5))


def classify_stu(stu_pct: float | None) -> str:
    if stu_pct is None:
        return 'unknown'
    if stu_pct < 10:
        return 'tight'
    if stu_pct < 18:
        return 'balanced'
    return 'comfortable'


def build() -> dict:
    oblocks = [
        ('balance_sheet_table', 'Balance sheet table', '10-year monthly maize balance output.', 'Step 4 balance', UPDATED_AT),
        ('stocks_to_use_chart', 'Stocks-to-Use chart', 'Crop-year stocks-to-use output dataset.', 'Step 4 balance', UPDATED_AT),
        ('price_correlation', 'Price correlation', 'Domestic price pressure vs global proxy correlation.', 'Step 3 demand + Step 5 drivers', UPDATED_AT),
        ('risk_flags', 'Risk flags', 'Monthly risk alert rows for weather/policy/trade/tightness.', 'Step 5 + Step 7', UPDATED_AT),
        ('scenario_summary', 'Scenario summary', 'Bull/Base/Bear crop-year price ranges.', 'Step 7 scenarios', UPDATED_AT),
        ('snapshot', 'Output snapshot', 'Latest regime summary row for dashboard.', 'Step 5 + Step 7', UPDATED_AT),
    ]

    bconn = connect(BALANCE_DB)
    dconn = connect(DEMAND_DB)
    sconn = connect(SUPPLY_DB)
    pconn = connect(DRIVER_DB)
    scconn = connect(SCENARIO_DB)

    monthly_balance = bconn.execute(
        """
        SELECT metric_month, crop_year, opening_stock, domestic_production, imports, total_availability, total_demand_monthly, delta
        FROM maize_balance_monthly
        ORDER BY metric_month
        """
    ).fetchall()

    annual_stu = bconn.execute(
        """
        SELECT crop_year, month_count, stocks_to_use_ratio, stocks_to_use_pct
        FROM maize_stocks_to_use
        ORDER BY crop_year
        """
    ).fetchall()

    domestic_price = {
        r['metric_month']: float(r['value'])
        for r in dconn.execute(
            "SELECT metric_month, value FROM maize_factor_monthly_values WHERE factor_key='retail_price_pressure' ORDER BY metric_month"
        ).fetchall()
    }
    global_proxy = {
        r['metric_month']: float(r['value'])
        for r in pconn.execute(
            "SELECT metric_month, value FROM maize_driver_monthly_values WHERE driver_key='us_corn_crop_outlook' ORDER BY metric_month"
        ).fetchall()
    }

    latest_driver = pconn.execute(
        "SELECT metric_month, composite_score, bullish_drivers_json, bearish_drivers_json FROM maize_driver_impact_score ORDER BY metric_month DESC LIMIT 1"
    ).fetchone()

    latest_balance = bconn.execute(
        "SELECT metric_month, crop_year, opening_stock, domestic_production, imports, delta, total_demand_monthly FROM maize_balance_monthly ORDER BY metric_month DESC LIMIT 1"
    ).fetchone()

    scenario_def = {
        r['scenario_key']: r['scenario_name']
        for r in scconn.execute("SELECT scenario_key, scenario_name FROM maize_scenario_definitions")
    }
    scenario_rows = scconn.execute(
        "SELECT scenario_key, crop_year, price_low, price_mid, price_high, confidence FROM maize_scenario_price_range ORDER BY crop_year, scenario_key"
    ).fetchall()

    pconn.close()
    dconn.close()
    sconn.close()
    scconn.close()
    bconn.close()

    balance_rows = [
        (
            f'bal-{i:03d}',
            r['metric_month'],
            r['crop_year'],
            float(r['opening_stock']),
            float(r['domestic_production']),
            float(r['imports']),
            float(r['total_availability']),
            float(r['total_demand_monthly']),
            float(r['delta']),
            float(r['opening_stock']) + float(r['domestic_production']) + float(r['imports']) - float(r['total_demand_monthly']),
            'step4_balance_monthly',
            UPDATED_AT,
        )
        for i, r in enumerate(monthly_balance, start=1)
    ]

    stu_rows = [
        (
            r['crop_year'],
            int(r['month_count']),
            float(r['stocks_to_use_ratio']) if r['stocks_to_use_ratio'] is not None else None,
            float(r['stocks_to_use_pct']) if r['stocks_to_use_pct'] is not None else None,
            classify_stu(float(r['stocks_to_use_pct']) if r['stocks_to_use_pct'] is not None else None),
            'Step 4 maize_stocks_to_use',
            UPDATED_AT,
        )
        for r in annual_stu
    ]

    months = sorted(set(domestic_price.keys()) & set(global_proxy.keys()))
    corr_rows = []
    for m in months:
        idx = months.index(m)
        d_vals = [domestic_price[x] for x in months[max(0, idx - 2): idx + 1]]
        g_vals = [global_proxy[x] for x in months[max(0, idx - 2): idx + 1]]
        c3 = correlation(d_vals, g_vals)

        d_vals6 = [domestic_price[x] for x in months[max(0, idx - 5): idx + 1]]
        g_vals6 = [global_proxy[x] for x in months[max(0, idx - 5): idx + 1]]
        c6 = correlation(d_vals6, g_vals6)

        corr_rows.append(
            (
                m,
                round(domestic_price[m], 6),
                round(global_proxy[m], 6),
                round(c3, 6) if c3 is not None else None,
                round(c6, 6) if c6 is not None else None,
                'Agmarknet + USDA global proxy',
                'https://agmarknet.gov.in/ | https://www.usda.gov/oce/commodity/wasde',
                UPDATED_AT,
            )
        )

    risk_rows = []
    if latest_driver is not None and latest_balance is not None:
        m = str(latest_driver['metric_month'])
        comp = float(latest_driver['composite_score'])
        delta = float(latest_balance['delta'])
        demand = float(latest_balance['total_demand_monthly'])
        ending = float(latest_balance['opening_stock']) + float(latest_balance['domestic_production']) + float(latest_balance['imports']) - float(latest_balance['total_demand_monthly'])
        stu = (ending / demand) * 100.0 if demand > 0 else None

        def sev(score: float) -> str:
            if score >= 75:
                return 'high'
            if score >= 55:
                return 'medium'
            return 'low'

        weather_policy_score = comp
        tightness_score = min(100.0, max(0.0, (20.0 - (stu or 0.0)) * 4.0))
        trade_score = min(100.0, max(0.0, 50.0 + (-delta) * 2.0))

        risk_rows.append((f'risk-001', m, 'weather_policy', round(weather_policy_score, 6), sev(weather_policy_score), 'driver_composite_score >= threshold', f'Composite driver score is {comp:.2f}.', 'step5_driver_impact', UPDATED_AT))
        risk_rows.append((f'risk-002', m, 'balance_tightness', round(tightness_score, 6), sev(tightness_score), 'low_stu_or_negative_delta', f'Delta={delta:.3f}, STU~{stu:.2f}%.', 'step4_balance', UPDATED_AT))
        risk_rows.append((f'risk-003', m, 'trade_global', round(trade_score, 6), sev(trade_score), 'delta_pressure_proxy', f'Trade/global pressure proxy from monthly balance delta ({delta:.3f}).', 'step4_balance', UPDATED_AT))

    scen_rows = [
        (
            f'scen-{i:04d}',
            r['scenario_key'],
            scenario_def.get(r['scenario_key'], r['scenario_key']),
            r['crop_year'],
            float(r['price_low']),
            float(r['price_mid']),
            float(r['price_high']),
            r['confidence'],
            'From Step 7 scenario engine',
            UPDATED_AT,
        )
        for i, r in enumerate(scenario_rows, start=1)
    ]

    snapshot_rows = []
    if latest_driver is not None:
        bull = latest_driver['bullish_drivers_json']
        bear = latest_driver['bearish_drivers_json']
        c = float(latest_driver['composite_score'])
        if c >= 62:
            regime = 'bullish_pressure'
        elif c <= 42:
            regime = 'bearish_pressure'
        else:
            regime = 'balanced'

        # suggested range from latest crop-year base scenario
        latest_cy = str(latest_balance['crop_year']) if latest_balance is not None else None
        suggested = 'n/a'
        if latest_cy is not None:
            with connect(SCENARIO_DB) as tmp:
                r = tmp.execute(
                    "SELECT price_low, price_mid, price_high FROM maize_scenario_price_range WHERE scenario_key='base_normal' AND crop_year=? LIMIT 1",
                    (latest_cy,),
                ).fetchone()
                if r is not None:
                    suggested = f"{float(r['price_low']):.2f}-{float(r['price_mid']):.2f}-{float(r['price_high']):.2f}"

        snapshot_rows.append((datetime.now(UTC).date().isoformat(), regime, bull, bear, suggested, UPDATED_AT))

    oconn = connect(OUTPUT_DB)
    ensure_schema(oconn)
    reset(oconn)

    oconn.executemany('INSERT INTO maize_output_blocks VALUES (?, ?, ?, ?, ?)', oblocks)
    oconn.executemany(
        """
        INSERT INTO maize_output_balance_sheet
        (id, metric_month, crop_year, opening_stock, production, imports, total_availability, total_demand, delta, ending_stock_sim, source_tag, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        balance_rows,
    )
    oconn.executemany(
        """
        INSERT INTO maize_output_stocks_to_use_chart
        (crop_year, month_count, stocks_to_use_ratio, stocks_to_use_pct, classification, source_name, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        stu_rows,
    )
    oconn.executemany(
        """
        INSERT INTO maize_output_price_correlation
        (metric_month, domestic_price_index, global_price_proxy_index, rolling_corr_3m, rolling_corr_6m, source_name, source_url, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        corr_rows,
    )
    oconn.executemany(
        """
        INSERT INTO maize_output_risk_flags
        (id, metric_month, risk_type, risk_score, severity, trigger_rule, narrative, source_layer, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        risk_rows,
    )
    oconn.executemany(
        """
        INSERT INTO maize_output_scenario_summary
        (id, scenario_key, scenario_name, crop_year, price_low, price_mid, price_high, confidence, note, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        scen_rows,
    )
    if snapshot_rows:
        oconn.executemany(
            """
            INSERT INTO maize_output_snapshot
            (snapshot_date, current_regime, top_bullish_drivers, top_bearish_drivers, suggested_range, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            snapshot_rows,
        )

    oconn.commit()

    counts = {
        'maize_output_blocks': oconn.execute('SELECT COUNT(*) FROM maize_output_blocks').fetchone()[0],
        'maize_output_balance_sheet': oconn.execute('SELECT COUNT(*) FROM maize_output_balance_sheet').fetchone()[0],
        'maize_output_stocks_to_use_chart': oconn.execute('SELECT COUNT(*) FROM maize_output_stocks_to_use_chart').fetchone()[0],
        'maize_output_price_correlation': oconn.execute('SELECT COUNT(*) FROM maize_output_price_correlation').fetchone()[0],
        'maize_output_risk_flags': oconn.execute('SELECT COUNT(*) FROM maize_output_risk_flags').fetchone()[0],
        'maize_output_scenario_summary': oconn.execute('SELECT COUNT(*) FROM maize_output_scenario_summary').fetchone()[0],
        'maize_output_snapshot': oconn.execute('SELECT COUNT(*) FROM maize_output_snapshot').fetchone()[0],
    }
    oconn.close()

    return {'db_path': str(OUTPUT_DB), 'counts': counts}


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))

