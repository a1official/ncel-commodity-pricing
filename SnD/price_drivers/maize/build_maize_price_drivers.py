from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / 'maize_price_drivers.db'
SUPPLY_DB = ROOT / 'SnD' / 'supply' / 'maize' / 'maize_supply_factors.db'
DEMAND_DB = ROOT / 'SnD' / 'demand' / 'maize' / 'maize_demand_monthly.db'
PROFILE_DB = ROOT / 'SnD' / 'profile' / 'maize' / 'maize_6w_profile.db'
UPDATED_AT = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
START_MONTH = date(2016, 4, 1)
END_MONTH = date(2026, 3, 1)

DRIVER_DEFINITIONS = [
    ('msp_maize', 'MSP (Maize)', 'Domestic', 'INR/quintal', 'Minimum support price policy floor for maize.'),
    ('kharif_arrival_intensity', 'Kharif arrival intensity', 'Domestic', 'index_100', 'Monthly maize arrival pressure proxy from domestic production release profile.'),
    ('poultry_demand_cycle', 'Poultry demand cycle', 'Domestic', 'index_100', 'Feed-cycle demand pressure from poultry placement seasonality.'),
    ('us_corn_crop_outlook', 'US corn crop outlook', 'Global', 'index_100', 'US corn production pressure index from USDA global production series.'),
    ('brazil_safrinha_pressure', 'Brazil safrinha pressure', 'Global', 'index_100', 'Brazil safrinha harvest intensity index.'),
    ('monsoon_distribution_risk', 'Monsoon distribution risk', 'Weather', 'index_100', 'Curated monthly monsoon distribution risk for Kharif maize.'),
    ('export_policy_restriction', 'Export policy restriction', 'Policy', 'policy_index', 'Monthly export-policy tightness signal for Indian maize.'),
    ('ethanol_blending_push', 'Ethanol blending push', 'Policy', 'index_100', 'Policy-linked ethanol demand intensity signal.'),
    ('substitution_vs_wheat', 'Substitution vs wheat', 'Market', 'index_100', 'Relative demand pressure from maize vs wheat economics.'),
]

DRIVER_STATUS = [
    ('msp_maize', 'annual_only', 'annual_to_monthly_step_series', 'Annual MSP mapped into monthly step series by crop year.'),
    ('kharif_arrival_intensity', 'available', 'derived_from_supply_monthly', 'Derived from domestic production monthly profile.'),
    ('poultry_demand_cycle', 'available', 'loaded_from_demand_monthly', 'Loaded from demand factor monthly values.'),
    ('us_corn_crop_outlook', 'partial', 'loaded_from_supply_global_monthly', 'Loaded from USDA global production monthly rows for US geography.'),
    ('brazil_safrinha_pressure', 'available', 'loaded_from_supply_monthly', 'Loaded from curated supply calendar monthly rows.'),
    ('monsoon_distribution_risk', 'curated', 'curated_monthly_profile', 'Curated recurring monthly monsoon risk profile.'),
    ('export_policy_restriction', 'curated', 'loaded_from_demand_policy_series', 'Loaded from policy_changes monthly series as export-policy proxy.'),
    ('ethanol_blending_push', 'available', 'loaded_from_demand_monthly', 'Loaded from ethanol_demand_signal monthly series.'),
    ('substitution_vs_wheat', 'available', 'loaded_from_demand_monthly', 'Loaded from substitution_effect monthly series.'),
]

DRIVER_SOURCES = [
    ('economic_survey', 'Economic Survey Statistical Appendix', 'https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf', 'annual pdf', 'MSP and annual crop context.'),
    ('usda_psd', 'USDA PSD', 'https://apps.fas.usda.gov/psdonline/app/index.html#/app/home', 'monthly', 'Global corn production context.'),
    ('usda_wasde', 'USDA WASDE', 'https://www.usda.gov/oce/commodity/wasde', 'monthly', 'Global market context and revisions.'),
    ('apeda', 'APEDA', 'https://apeda.gov.in/', 'web/pdf', 'Trade and export context.'),
    ('agmarknet', 'Agmarknet', 'https://agmarknet.gov.in/', 'daily', 'Domestic mandi price context and substitution signal support.'),
    ('imd', 'India Meteorological Department', 'https://mausam.imd.gov.in/', 'seasonal/weekly', 'Monsoon distribution and rainfall risk context.'),
]

DRIVER_REFERENCE = [
    ('msp_maize', 'https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf', 'Monthly MSP step series from annual MSP values.'),
    ('kharif_arrival_intensity', 'https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf', 'Arrival pressure index from monthly domestic production release.'),
    ('poultry_demand_cycle', 'https://apeda.gov.in/', 'Direct monthly poultry-demand cycle signal from demand layer.'),
    ('us_corn_crop_outlook', 'https://www.usda.gov/oce/commodity/wasde', 'US-only monthly global production index from USDA series.'),
    ('brazil_safrinha_pressure', 'https://www.fao.org/', 'Monthly safrinha harvest intensity signal.'),
    ('monsoon_distribution_risk', 'https://mausam.imd.gov.in/', 'Curated monthly monsoon risk profile with Kharif concentration.'),
    ('export_policy_restriction', 'https://www.dgft.gov.in/CP/', 'Policy-event proxy from monthly policy series.'),
    ('ethanol_blending_push', 'https://mopng.gov.in/', 'Monthly ethanol policy-demand signal.'),
    ('substitution_vs_wheat', 'https://agmarknet.gov.in/', 'Monthly substitution index from maize-vs-wheat economics.'),
]

DRIVER_DIRECTIONS = {
    'msp_maize': 1.0,
    'kharif_arrival_intensity': -1.0,
    'poultry_demand_cycle': 1.0,
    'us_corn_crop_outlook': -1.0,
    'brazil_safrinha_pressure': -1.0,
    'monsoon_distribution_risk': 1.0,
    'export_policy_restriction': -1.0,
    'ethanol_blending_push': 1.0,
    'substitution_vs_wheat': 1.0,
}

DRIVER_WEIGHTS = {
    'msp_maize': 0.17,
    'kharif_arrival_intensity': 0.14,
    'poultry_demand_cycle': 0.15,
    'us_corn_crop_outlook': 0.12,
    'brazil_safrinha_pressure': 0.10,
    'monsoon_distribution_risk': 0.12,
    'export_policy_restriction': 0.08,
    'ethanol_blending_push': 0.07,
    'substitution_vs_wheat': 0.05,
}


def month_range(start: date, end: date) -> list[date]:
    current = date(start.year, start.month, 1)
    out: list[date] = []
    while current <= end:
        out.append(current)
        current = date(current.year + (current.month // 12), (current.month % 12) + 1, 1)
    return out


def marketing_year_for_month(d: date) -> str:
    start_year = d.year if d.month >= 4 else d.year - 1
    return f"{start_year}/{str(start_year + 1)[-2:]}"


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS maize_driver_definitions (
            driver_key TEXT PRIMARY KEY,
            driver_name TEXT NOT NULL,
            driver_bucket TEXT NOT NULL,
            default_unit TEXT NOT NULL,
            description TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS maize_driver_source_inventory (
            source_key TEXT PRIMARY KEY,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            cadence TEXT,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS maize_driver_status (
            driver_key TEXT PRIMARY KEY,
            monthly_status TEXT NOT NULL,
            load_mode TEXT NOT NULL,
            notes TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS maize_driver_reference (
            driver_key TEXT PRIMARY KEY,
            source_website TEXT,
            formula_note TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS maize_driver_monthly_values (
            id TEXT PRIMARY KEY,
            driver_key TEXT NOT NULL,
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
            UNIQUE(driver_key, metric_month)
        );
        CREATE TABLE IF NOT EXISTS maize_driver_impact_score (
            metric_month TEXT PRIMARY KEY,
            marketing_year TEXT NOT NULL,
            composite_score REAL NOT NULL,
            domestic_score REAL NOT NULL,
            global_score REAL NOT NULL,
            weather_score REAL NOT NULL,
            policy_score REAL NOT NULL,
            market_score REAL NOT NULL,
            implied_price_adjustment_pct REAL NOT NULL,
            bullish_drivers_json TEXT NOT NULL,
            bearish_drivers_json TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def reset(conn: sqlite3.Connection) -> None:
    for table in (
        'maize_driver_definitions',
        'maize_driver_source_inventory',
        'maize_driver_status',
        'maize_driver_reference',
        'maize_driver_monthly_values',
        'maize_driver_impact_score',
    ):
        conn.execute(f'DELETE FROM {table}')
    conn.commit()


def load_msp_step(months: list[date]) -> dict[str, float]:
    conn = connect(PROFILE_DB)
    rows = conn.execute(
        """
        SELECT marketing_year, value
        FROM maize_national_trend_10y
        WHERE metric_key='msp_inr_quintal'
        ORDER BY marketing_year
        """
    ).fetchall()
    conn.close()

    annual = {str(r['marketing_year']).replace('-', '/'): float(r['value']) for r in rows}
    if '2025/26' not in annual and annual:
        annual['2025/26'] = sorted(annual.items())[-1][1]

    out: dict[str, float] = {}
    for d in months:
        my = marketing_year_for_month(d)
        val = annual.get(my)
        if val is None and annual:
            val = sorted(annual.items())[-1][1]
        out[d.isoformat()] = float(val or 0.0)
    return out


def load_series_map(db: Path, factor_key: str, geography: str | None = None) -> dict[str, float]:
    conn = connect(db)
    q = "SELECT metric_month, value FROM maize_factor_monthly_values WHERE factor_key=?"
    params: list[object] = [factor_key]
    if geography is not None:
        q += " AND geography=?"
        params.append(geography)
    q += " ORDER BY metric_month"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return {str(r['metric_month']): float(r['value'] or 0.0) for r in rows}


def normalize_to_index(series: dict[str, float], fallback: float = 100.0) -> dict[str, float]:
    vals = [v for v in series.values() if v is not None]
    if not vals:
        return {k: fallback for k in series}
    mean = sum(vals) / len(vals)
    if abs(mean) < 1e-9:
        return {k: fallback for k in series}
    return {k: round((v / mean) * 100.0, 6) for k, v in series.items()}


def monsoon_risk_profile(month: int) -> float:
    profile = {1: 25.0, 2: 20.0, 3: 18.0, 4: 22.0, 5: 35.0, 6: 60.0, 7: 72.0, 8: 68.0, 9: 55.0, 10: 38.0, 11: 28.0, 12: 24.0}
    return profile[month]


def build_driver_rows() -> list[tuple]:
    months = month_range(START_MONTH, END_MONTH)

    msp = load_msp_step(months)
    domestic_production = load_series_map(SUPPLY_DB, 'domestic_production', geography='India')
    kharif_arrival = normalize_to_index(domestic_production)

    poultry = load_series_map(DEMAND_DB, 'poultry_demand_cycle')
    us_global = load_series_map(SUPPLY_DB, 'usda_global_production', geography='United States')
    us_corn = normalize_to_index(us_global)
    safrinha = load_series_map(SUPPLY_DB, 'brazil_safrinha_harvest_calendar', geography='Global')
    policy = load_series_map(DEMAND_DB, 'policy_changes')
    ethanol = load_series_map(DEMAND_DB, 'ethanol_demand_signal')
    substitution = load_series_map(DEMAND_DB, 'substitution_effect')

    rows: list[tuple] = []
    for i, d in enumerate(months, start=1):
        m = d.isoformat()
        my = marketing_year_for_month(d)

        entries = [
            ('msp_maize', msp.get(m, 0.0), 'INR/quintal', 'Economic Survey Statistical Appendix', 'https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf', 'annual_msp_to_monthly_step_series', 'medium', 'Annual MSP held as monthly step series.'),
            ('kharif_arrival_intensity', kharif_arrival.get(m, 100.0), 'index_100', 'Derived from domestic production monthly profile', 'https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf', 'normalize_domestic_production_to_index_100', 'medium', 'Monthly kharif arrival pressure proxy.'),
            ('poultry_demand_cycle', poultry.get(m, 100.0), 'index_100', 'Curated Maize demand profile', 'https://apeda.gov.in/', 'load_from_demand_factor_monthly_values', 'medium', 'Monthly poultry-demand cycle signal.'),
            ('us_corn_crop_outlook', us_corn.get(m, 100.0), 'index_100', 'USDA WASDE/PSD', 'https://www.usda.gov/oce/commodity/wasde', 'normalize_usda_us_production_to_index_100', 'medium', 'US-only crop outlook proxy index.'),
            ('brazil_safrinha_pressure', safrinha.get(m, 0.0), 'index_100', 'Curated Brazil safrinha harvest calendar', 'https://www.fao.org/', 'load_from_supply_calendar_series', 'medium', 'Monthly safrinha harvest intensity signal.'),
            ('monsoon_distribution_risk', monsoon_risk_profile(d.month), 'index_100', 'Curated IMD-style monsoon risk profile', 'https://mausam.imd.gov.in/', 'curated_recurring_monthly_profile', 'medium', 'Curated monsoon-distribution risk index.'),
            ('export_policy_restriction', policy.get(m, 0.0), 'policy_index', 'Curated policy event profile', 'https://www.dgft.gov.in/CP/', 'load_from_demand_policy_changes_series', 'medium', 'Proxy for export-policy tightness.'),
            ('ethanol_blending_push', ethanol.get(m, 0.0), 'index_100', 'Curated ethanol policy signal', 'https://mopng.gov.in/', 'load_from_ethanol_demand_signal_series', 'medium', 'Monthly ethanol policy demand push signal.'),
            ('substitution_vs_wheat', substitution.get(m, 100.0), 'index_100', 'Agmarknet-based substitution signal', 'https://agmarknet.gov.in/', 'load_from_substitution_effect_series', 'medium', 'Monthly maize-vs-wheat substitution signal.'),
        ]

        for j, e in enumerate(entries, start=1):
            rows.append((f'maize-driver-{i:03d}-{j:02d}', e[0], m, my, round(float(e[1]), 6), e[2], e[3], e[4], e[5], e[6], e[7], UPDATED_AT))
    return rows


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def build_impact_rows(driver_rows: list[tuple]) -> list[tuple]:
    bucket_map = {k: b for k, _n, b, _u, _d in DRIVER_DEFINITIONS}
    name_map = {k: n for k, n, _b, _u, _d in DRIVER_DEFINITIONS}

    by_driver: dict[str, list[tuple[str, str, float]]] = {}
    for _id, driver_key, metric_month, marketing_year, value, *_rest in driver_rows:
        by_driver.setdefault(driver_key, []).append((metric_month, marketing_year, float(value)))

    standardized: dict[str, dict[str, float]] = {}
    for driver_key, series in by_driver.items():
        vals = [v for _m, _y, v in series]
        mean_v = sum(vals) / len(vals) if vals else 0.0
        var = sum((v - mean_v) ** 2 for v in vals) / len(vals) if vals else 0.0
        std = var ** 0.5
        standardized[driver_key] = {}
        for metric_month, _my, value in series:
            z = 0.0 if std <= 1e-9 else (value - mean_v) / std
            standardized[driver_key][metric_month] = DRIVER_DIRECTIONS[driver_key] * DRIVER_WEIGHTS[driver_key] * z

    months = sorted({m for series in by_driver.values() for m, _y, _v in series})
    my_map = {m: y for series in by_driver.values() for m, y, _v in series}

    out: list[tuple] = []
    for m in months:
        bucket_sums = {'Domestic': 0.0, 'Global': 0.0, 'Weather': 0.0, 'Policy': 0.0, 'Market': 0.0}
        effects = []
        for driver_key, month_map in standardized.items():
            c = float(month_map.get(m, 0.0))
            bucket = bucket_map[driver_key]
            bucket_sums[bucket] += c
            effects.append({'driver_key': driver_key, 'driver_name': name_map[driver_key], 'bucket': bucket, 'contribution': round(c, 6)})

        raw = sum(bucket_sums.values())
        composite = clamp(50.0 + raw * 20.0, 0.0, 100.0)
        domestic = clamp(50.0 + bucket_sums['Domestic'] * 35.0, 0.0, 100.0)
        global_s = clamp(50.0 + bucket_sums['Global'] * 35.0, 0.0, 100.0)
        weather = clamp(50.0 + bucket_sums['Weather'] * 35.0, 0.0, 100.0)
        policy = clamp(50.0 + bucket_sums['Policy'] * 35.0, 0.0, 100.0)
        market = clamp(50.0 + bucket_sums['Market'] * 35.0, 0.0, 100.0)
        implied = clamp(raw * 1.2, -4.0, 4.0)

        bullish = sorted([e for e in effects if e['contribution'] > 0], key=lambda x: x['contribution'], reverse=True)[:3]
        bearish = sorted([e for e in effects if e['contribution'] < 0], key=lambda x: x['contribution'])[:3]

        out.append((m, my_map[m], round(composite, 6), round(domestic, 6), round(global_s, 6), round(weather, 6), round(policy, 6), round(market, 6), round(implied, 6), json.dumps(bullish), json.dumps(bearish), 'Composite maize price-driver overlay built from standardized monthly driver contributions.', UPDATED_AT))
    return out


def build_db() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect(OUTPUT_DB)
    ensure_schema(conn)
    reset(conn)

    conn.executemany('INSERT INTO maize_driver_definitions VALUES (?, ?, ?, ?, ?)', DRIVER_DEFINITIONS)
    conn.executemany('INSERT INTO maize_driver_source_inventory VALUES (?, ?, ?, ?, ?)', DRIVER_SOURCES)
    conn.executemany('INSERT INTO maize_driver_status VALUES (?, ?, ?, ?)', DRIVER_STATUS)
    conn.executemany('INSERT INTO maize_driver_reference VALUES (?, ?, ?)', DRIVER_REFERENCE)

    driver_rows = build_driver_rows()
    conn.executemany("INSERT INTO maize_driver_monthly_values (id, driver_key, metric_month, marketing_year, value, unit, source_name, source_url, method, confidence, notes, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", driver_rows)

    impact_rows = build_impact_rows(driver_rows)
    conn.executemany("INSERT INTO maize_driver_impact_score (metric_month, marketing_year, composite_score, domestic_score, global_score, weather_score, policy_score, market_score, implied_price_adjustment_pct, bullish_drivers_json, bearish_drivers_json, notes, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", impact_rows)
    conn.commit()

    c1 = conn.execute('SELECT COUNT(*) FROM maize_driver_monthly_values').fetchone()[0]
    c2 = conn.execute('SELECT COUNT(*) FROM maize_driver_impact_score').fetchone()[0]
    rg = conn.execute('SELECT MIN(metric_month), MAX(metric_month) FROM maize_driver_impact_score').fetchone()
    conn.close()

    return {'db_path': str(OUTPUT_DB), 'maize_driver_monthly_values': c1, 'maize_driver_impact_score': c2, 'range': [rg[0], rg[1]]}


if __name__ == '__main__':
    print(json.dumps(build_db(), indent=2))
