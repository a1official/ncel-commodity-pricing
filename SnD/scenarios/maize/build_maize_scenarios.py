from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / 'maize_scenarios.db'
BALANCE_DB = ROOT / 'SnD' / 'balance' / 'maize' / 'maize_balance_sheet.db'
DRIVER_DB = ROOT / 'SnD' / 'price_drivers' / 'maize' / 'maize_price_drivers.db'
UPDATED_AT = datetime.now(UTC).isoformat().replace('+00:00', 'Z')

SCENARIOS = [
    ('bull_tight_supply', 'Bull (Tight Supply)', 'Below-normal monsoon/winter, lower production, tighter imports, demand strength.', 'low_to_medium'),
    ('base_normal', 'Base', 'Normal weather, stable policy, trend-line demand.', 'medium_to_high'),
    ('bear_surplus', 'Bear (Surplus)', 'Bumper crop, easier imports, softer demand.', 'low_to_medium'),
]

ASSUMPTIONS = {
    'bull_tight_supply': {
        'production_shock_pct': -0.06,
        'imports_shock_pct': -0.10,
        'demand_shock_pct': 0.04,
        'policy_shock_index': 8.0,
        'weather_shock_index': 10.0,
        'global_shock_index': 6.0,
        'band_width': 0.08,
    },
    'base_normal': {
        'production_shock_pct': 0.00,
        'imports_shock_pct': 0.00,
        'demand_shock_pct': 0.00,
        'policy_shock_index': 0.0,
        'weather_shock_index': 0.0,
        'global_shock_index': 0.0,
        'band_width': 0.06,
    },
    'bear_surplus': {
        'production_shock_pct': 0.06,
        'imports_shock_pct': 0.10,
        'demand_shock_pct': -0.04,
        'policy_shock_index': -8.0,
        'weather_shock_index': -10.0,
        'global_shock_index': -6.0,
        'band_width': 0.08,
    },
}


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS maize_scenario_definitions (
            scenario_key TEXT PRIMARY KEY,
            scenario_name TEXT NOT NULL,
            description TEXT NOT NULL,
            probability_band TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_scenario_assumptions (
            id TEXT PRIMARY KEY,
            scenario_key TEXT NOT NULL,
            variable_key TEXT NOT NULL,
            shock_type TEXT NOT NULL,
            shock_value REAL NOT NULL,
            unit TEXT NOT NULL,
            rationale TEXT NOT NULL,
            source_link TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_scenario_monthly_output (
            id TEXT PRIMARY KEY,
            scenario_key TEXT NOT NULL,
            metric_month TEXT NOT NULL,
            crop_year TEXT NOT NULL,
            availability REAL NOT NULL,
            demand REAL NOT NULL,
            delta REAL NOT NULL,
            ending_stock_sim REAL NOT NULL,
            stu_proxy REAL,
            driver_score_adj REAL NOT NULL,
            implied_price_index REAL NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(scenario_key, metric_month)
        );

        CREATE TABLE IF NOT EXISTS maize_scenario_annual_output (
            id TEXT PRIMARY KEY,
            scenario_key TEXT NOT NULL,
            crop_year TEXT NOT NULL,
            months INTEGER NOT NULL,
            availability_sum REAL NOT NULL,
            demand_sum REAL NOT NULL,
            delta_sum REAL NOT NULL,
            ending_stock REAL NOT NULL,
            stocks_to_use REAL,
            implied_price_index_avg REAL NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(scenario_key, crop_year)
        );

        CREATE TABLE IF NOT EXISTS maize_scenario_price_range (
            id TEXT PRIMARY KEY,
            scenario_key TEXT NOT NULL,
            crop_year TEXT NOT NULL,
            price_low REAL NOT NULL,
            price_mid REAL NOT NULL,
            price_high REAL NOT NULL,
            confidence TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(scenario_key, crop_year)
        );
        """
    )
    conn.commit()


def reset(conn: sqlite3.Connection) -> None:
    for t in [
        'maize_scenario_definitions',
        'maize_scenario_assumptions',
        'maize_scenario_monthly_output',
        'maize_scenario_annual_output',
        'maize_scenario_price_range',
    ]:
        conn.execute(f'DELETE FROM {t}')
    conn.commit()


def load_baseline() -> tuple[list[sqlite3.Row], dict[str, float]]:
    bconn = connect(BALANCE_DB)
    dconn = connect(DRIVER_DB)
    monthly = bconn.execute(
        """
        SELECT metric_month, crop_year, opening_stock, domestic_production, imports, total_availability, total_demand_monthly
        FROM maize_balance_monthly
        ORDER BY metric_month
        """
    ).fetchall()
    driver = {
        row['metric_month']: float(row['composite_score'])
        for row in dconn.execute(
            "SELECT metric_month, composite_score FROM maize_driver_impact_score ORDER BY metric_month"
        ).fetchall()
    }
    bconn.close()
    dconn.close()
    return monthly, driver


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def run_scenario(skey: str, base_rows: list[sqlite3.Row], base_driver: dict[str, float]) -> tuple[list[tuple], list[tuple], list[tuple]]:
    a = ASSUMPTIONS[skey]
    monthly_payload: list[tuple] = []

    annual_acc: dict[str, dict[str, float]] = {}

    for i, r in enumerate(base_rows, start=1):
        month = str(r['metric_month'])
        crop_year = str(r['crop_year'])

        opening = float(r['opening_stock'])
        production = float(r['domestic_production']) * (1.0 + a['production_shock_pct'])
        imports = float(r['imports']) * (1.0 + a['imports_shock_pct'])
        availability = opening + production + imports

        demand = float(r['total_demand_monthly']) * (1.0 + a['demand_shock_pct'])
        delta = availability - demand
        ending_stock = opening + production + imports - demand
        stu_proxy = ending_stock / demand if demand > 0 else None

        base_comp = float(base_driver.get(month, 50.0))
        # policy + weather + global shocks shift baseline driver score
        driver_adj = clamp(base_comp + 0.35 * a['policy_shock_index'] + 0.35 * a['weather_shock_index'] + 0.30 * a['global_shock_index'], 0.0, 100.0)

        tightness_term = (-delta / demand) * 100.0 if demand > 0 else 0.0
        stu_inverse = (1.0 - (stu_proxy if stu_proxy is not None else 0.0)) * 100.0
        driver_term = driver_adj - 50.0
        implied_price_idx = clamp(100.0 + 0.45 * tightness_term + 0.20 * stu_inverse + 0.35 * driver_term, 60.0, 180.0)

        monthly_payload.append(
            (
                f'{skey}-m-{i:03d}',
                skey,
                month,
                crop_year,
                round(availability, 6),
                round(demand, 6),
                round(delta, 6),
                round(ending_stock, 6),
                round(stu_proxy, 6) if stu_proxy is not None else None,
                round(driver_adj, 6),
                round(implied_price_idx, 6),
                UPDATED_AT,
            )
        )

        acc = annual_acc.setdefault(crop_year, {'months': 0, 'availability': 0.0, 'demand': 0.0, 'delta': 0.0, 'ending': 0.0, 'price_sum': 0.0})
        acc['months'] += 1
        acc['availability'] += availability
        acc['demand'] += demand
        acc['delta'] += delta
        acc['ending'] = ending_stock
        acc['price_sum'] += implied_price_idx

    annual_payload: list[tuple] = []
    range_payload: list[tuple] = []
    for j, (cy, acc) in enumerate(sorted(annual_acc.items()), start=1):
        months = int(acc['months'])
        availability_sum = float(acc['availability'])
        demand_sum = float(acc['demand'])
        delta_sum = float(acc['delta'])
        ending = float(acc['ending'])
        stu = ending / demand_sum if demand_sum > 0 else None
        price_mid = acc['price_sum'] / months if months > 0 else 100.0
        bw = a['band_width']
        low = price_mid * (1.0 - bw)
        high = price_mid * (1.0 + bw)

        annual_payload.append(
            (
                f'{skey}-a-{j:03d}',
                skey,
                cy,
                months,
                round(availability_sum, 6),
                round(demand_sum, 6),
                round(delta_sum, 6),
                round(ending, 6),
                round(stu, 6) if stu is not None else None,
                round(price_mid, 6),
                UPDATED_AT,
            )
        )

        range_payload.append(
            (
                f'{skey}-r-{j:03d}',
                skey,
                cy,
                round(low, 6),
                round(price_mid, 6),
                round(high, 6),
                'medium',
                UPDATED_AT,
            )
        )

    return monthly_payload, annual_payload, range_payload


def build() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect(OUTPUT_DB)
    ensure_schema(conn)
    reset(conn)

    conn.executemany('INSERT INTO maize_scenario_definitions VALUES (?, ?, ?, ?)', SCENARIOS)

    assumption_rows = []
    aid = 1
    for skey, _name, _desc, _prob in SCENARIOS:
        a = ASSUMPTIONS[skey]
        entries = [
            ('production_shock_pct', 'percentage', a['production_shock_pct'], 'ratio', 'Production shock vs baseline', 'https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf'),
            ('imports_shock_pct', 'percentage', a['imports_shock_pct'], 'ratio', 'Import shock vs baseline', 'https://apeda.gov.in/'),
            ('demand_shock_pct', 'percentage', a['demand_shock_pct'], 'ratio', 'Demand shock vs baseline', 'https://apeda.gov.in/'),
            ('policy_shock_index', 'index_shift', a['policy_shock_index'], 'index', 'Policy stress shift', 'https://www.dgft.gov.in/CP/'),
            ('weather_shock_index', 'index_shift', a['weather_shock_index'], 'index', 'Weather risk shift', 'https://mausam.imd.gov.in/'),
            ('global_shock_index', 'index_shift', a['global_shock_index'], 'index', 'Global supply shift', 'https://www.usda.gov/oce/commodity/wasde'),
            ('band_width', 'percentage', a['band_width'], 'ratio', 'Price range band width', 'https://agmarknet.gov.in/'),
        ]
        for var, stype, val, unit, rat, src in entries:
            assumption_rows.append((f'a-{aid:03d}', skey, var, stype, float(val), unit, rat, src, UPDATED_AT))
            aid += 1

    conn.executemany(
        """
        INSERT INTO maize_scenario_assumptions
        (id, scenario_key, variable_key, shock_type, shock_value, unit, rationale, source_link, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        assumption_rows,
    )

    base_rows, base_driver = load_baseline()
    monthly_all: list[tuple] = []
    annual_all: list[tuple] = []
    range_all: list[tuple] = []

    for skey, _n, _d, _p in SCENARIOS:
        m, a, r = run_scenario(skey, base_rows, base_driver)
        monthly_all.extend(m)
        annual_all.extend(a)
        range_all.extend(r)

    conn.executemany(
        """
        INSERT INTO maize_scenario_monthly_output
        (id, scenario_key, metric_month, crop_year, availability, demand, delta, ending_stock_sim, stu_proxy, driver_score_adj, implied_price_index, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        monthly_all,
    )
    conn.executemany(
        """
        INSERT INTO maize_scenario_annual_output
        (id, scenario_key, crop_year, months, availability_sum, demand_sum, delta_sum, ending_stock, stocks_to_use, implied_price_index_avg, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        annual_all,
    )
    conn.executemany(
        """
        INSERT INTO maize_scenario_price_range
        (id, scenario_key, crop_year, price_low, price_mid, price_high, confidence, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        range_all,
    )
    conn.commit()

    out = {
        'db_path': str(OUTPUT_DB),
        'maize_scenario_definitions': conn.execute('SELECT COUNT(*) FROM maize_scenario_definitions').fetchone()[0],
        'maize_scenario_assumptions': conn.execute('SELECT COUNT(*) FROM maize_scenario_assumptions').fetchone()[0],
        'maize_scenario_monthly_output': conn.execute('SELECT COUNT(*) FROM maize_scenario_monthly_output').fetchone()[0],
        'maize_scenario_annual_output': conn.execute('SELECT COUNT(*) FROM maize_scenario_annual_output').fetchone()[0],
        'maize_scenario_price_range': conn.execute('SELECT COUNT(*) FROM maize_scenario_price_range').fetchone()[0],
    }

    # quick monotonic check on overall avg price_mid
    rows = conn.execute(
        "SELECT scenario_key, AVG(price_mid) FROM maize_scenario_price_range GROUP BY scenario_key"
    ).fetchall()
    out['avg_price_mid_by_scenario'] = {r[0]: round(float(r[1]), 6) for r in rows}

    conn.close()
    return out


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
