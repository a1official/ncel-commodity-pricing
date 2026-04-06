from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / 'wheat_price_drivers.db'
WHEAT_SUPPORT_DB = ROOT / 'backend' / 'data' / 'wheat_model_support.db'
UPDATED_AT = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
START_MONTH = date(2016, 4, 1)
END_MONTH = date(2026, 3, 1)

FACTOR_DEFINITIONS = [
    ('msp', 'MSP', 'Domestic', 'INR/quintal', 'Minimum support price policy floor for wheat.'),
    ('fci_procurement', 'FCI procurement', 'Domestic', 'LMT', 'Public procurement intensity; stronger procurement can tighten open-market supply.'),
    ('rabi_sowing_area', 'Rabi sowing area', 'Domestic', 'lakh_hectare', 'Sowing progress / acreage context for the next crop.'),
    ('north_india_winter_temperature', 'North India winter temperature', 'Weather', 'celsius', 'Average wheat-belt temperature across North India states.'),
    ('frost_risk', 'Frost risk', 'Weather', 'index', 'Monthly frost-risk index from cold-minimum days in the wheat belt.'),
    ('black_sea_corridor', 'Black Sea corridor', 'Global', 'policy_index', 'Global wheat flow shock index linked to Black Sea corridor events.'),
    ('russian_export_policy', 'Russian export policy', 'Global', 'policy_index', 'Monthly policy pressure index for Russian export taxes, quotas, or tightening.'),
    ('india_export_policy', 'India export ban / duty', 'Policy', 'policy_index', 'Monthly policy pressure index for Indian wheat export restrictions.'),
]

FACTOR_STATUS = [
    ('msp', 'mixed', 'official_history_plus_step_series', 'Recent years come from local wheat support signals; older years are filled from curated official MSP history.'),
    ('fci_procurement', 'mixed', 'recent_actual_plus_historical_proxy', 'Recent procurement values use local official rows; older years are proxied into marketing-year monthly pulses.'),
    ('rabi_sowing_area', 'mixed', 'recent_signal_plus_annual_area_proxy', 'Recent progressive sowing rows use local signals; older years use annual wheat area as a sowing reference.'),
    ('north_india_winter_temperature', 'mixed', 'actual_recent_plus_backfilled_month_normals', '2024 onward uses actual weather; older years are backfilled from calendar-month normals.'),
    ('frost_risk', 'mixed', 'actual_recent_plus_backfilled_month_normals', '2024 onward uses actual cold-day counts; older years are backfilled from calendar-month normals.'),
    ('black_sea_corridor', 'curated', 'event_timeline_index', 'Curated monthly event index from major Black Sea corridor milestones.'),
    ('russian_export_policy', 'curated', 'event_timeline_index', 'Curated monthly event index from major Russian wheat export policy shifts.'),
    ('india_export_policy', 'curated', 'event_timeline_index', 'Curated monthly event index from Indian wheat export restriction milestones.'),
]

DRIVER_REFERENCE = [
    (
        'msp',
        'https://www.pib.gov.in/',
        'MSP monthly step series from official announcement dates; higher MSP tends to support mandi prices.',
        'high',
    ),
    (
        'fci_procurement',
        'https://dfpd.gov.in/',
        'Use actual monthly procurement where available; else allocate annual procurement into Apr-Aug pulses. Higher procurement tightens open-market supply.',
        'medium',
    ),
    (
        'rabi_sowing_area',
        'https://desagri.gov.in/',
        'Use progressive sowing rows where available; else annual wheat area as proxy. Higher sowing/acreage is bearish because it points to larger future production.',
        'medium',
    ),
    (
        'north_india_winter_temperature',
        'https://open-meteo.com/',
        'Monthly average across North India wheat-belt states. Positive anomaly versus the same calendar month is treated as bullish supply stress.',
        'medium',
    ),
    (
        'frost_risk',
        'https://open-meteo.com/',
        'Index from cold-day counts with min temperature <= 5C. Higher frost risk is bullish because it threatens yield/quality.',
        'medium',
    ),
    (
        'black_sea_corridor',
        'https://www.un.org/',
        'Curated event-decay index of Black Sea corridor disruptions. Higher disruption score is bullish for global wheat prices.',
        'medium',
    ),
    (
        'russian_export_policy',
        'https://www.reuters.com/markets/commodities/',
        'Curated event-decay index for Russian export taxes/quotas/tightening. Higher score is bullish for world wheat prices.',
        'medium',
    ),
    (
        'india_export_policy',
        'https://dgft.gov.in/',
        'Curated event-decay index for Indian export bans/restrictions. Higher score is bearish domestically because it keeps wheat inside India.',
        'high',
    ),
]

SOURCE_INVENTORY = [
    ('wheat_support_db', 'Local wheat support store', str(WHEAT_SUPPORT_DB), 'monthly / seasonal', 'Used for MSP, procurement, acreage, and weather.'),
    ('pib', 'Press Information Bureau', 'https://www.pib.gov.in/', 'event / seasonal', 'Source family for MSP, sowing, and policy announcements.'),
    ('dfpd', 'Department of Food and Public Distribution', 'https://dfpd.gov.in/', 'monthly', 'Source family for procurement and stock context.'),
    ('curated_global_policy', 'Curated global policy/event timeline', None, 'event', 'Used for Black Sea and Russian export-policy monthly scores.'),
]

MSP_HISTORY = {
    '2016/17': 1625.0, '2017/18': 1735.0, '2018/19': 1840.0, '2019/20': 1840.0,
    '2020/21': 1925.0, '2021/22': 1975.0, '2022/23': 2015.0, '2023/24': 2125.0,
    '2024/25': 2275.0, '2025/26': 2425.0, '2026/27': 2585.0,
}
MSP_STEP_DATES = {
    '2016-04-01': 1525.0,
    '2016-10-01': 1625.0,
    '2017-10-01': 1735.0,
    '2018-10-01': 1840.0,
    '2019-10-01': 1840.0,
    '2020-10-01': 1925.0,
    '2021-10-01': 1975.0,
    '2022-10-01': 2125.0,
    '2023-10-18': 2275.0,
    '2024-10-16': 2425.0,
    '2025-10-01': 2585.0,
}
PROCUREMENT_HISTORY = {
    '2016/17': 229.62, '2017/18': 308.24, '2018/19': 357.95, '2019/20': 341.32,
    '2020/21': 389.92, '2021/22': 433.44, '2022/23': 187.92, '2023/24': 262.02,
    '2024/25': 266.0, '2025/26': 300.35,
}
BLACK_SEA_EVENTS = {
    '2022-07': 25.0, '2022-10': 75.0, '2022-11': 40.0, '2023-05': 55.0, '2023-07': 95.0,
}
RUSSIA_POLICY_EVENTS = {
    '2021-02': 70.0, '2021-06': 55.0, '2022-02': 85.0, '2023-07': 72.0, '2024-06': 60.0, '2025-07': 58.0,
}
INDIA_EXPORT_POLICY_EVENTS = {
    '2022-05': 100.0, '2023-01': 82.0, '2024-01': 78.0, '2025-01': 74.0,
}
PROCUREMENT_WEIGHTS = {4: 0.38, 5: 0.34, 6: 0.18, 7: 0.08, 8: 0.02}
NORTH_INDIA_STATES = ('Punjab', 'Haryana', 'Uttar Pradesh', 'Rajasthan', 'Madhya Pradesh', 'Delhi')
DRIVER_DIRECTIONS = {
    'msp': 1.0,
    'fci_procurement': 1.0,
    'rabi_sowing_area': -1.0,
    'north_india_winter_temperature': 1.0,
    'frost_risk': 1.0,
    'black_sea_corridor': 1.0,
    'russian_export_policy': 1.0,
    'india_export_policy': -1.0,
}
DRIVER_WEIGHTS = {
    'msp': 0.22,
    'fci_procurement': 0.18,
    'rabi_sowing_area': 0.14,
    'north_india_winter_temperature': 0.10,
    'frost_risk': 0.10,
    'black_sea_corridor': 0.10,
    'russian_export_policy': 0.08,
    'india_export_policy': 0.08,
}
BUCKET_WEIGHTS = {
    'Domestic': 1.0,
    'Weather': 1.0,
    'Global': 1.0,
    'Policy': 1.0,
}


def month_range(start: date, end: date) -> list[date]:
    current = date(start.year, start.month, 1)
    out = []
    while current <= end:
        out.append(current)
        current = date(current.year + (current.month // 12), (current.month % 12) + 1, 1)
    return out


def marketing_year_for_month(d: date) -> str:
    start_year = d.year if d.month >= 4 else d.year - 1
    return f"{start_year}/{str(start_year + 1)[-2:]}"


def normalize(weights: dict[int, float]) -> dict[int, float]:
    total = sum(weights.values()) or 1.0
    return {k: v / total for k, v in weights.items()}


def build_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS factor_definitions (
            factor_key TEXT PRIMARY KEY,
            factor_name TEXT NOT NULL,
            driver_bucket TEXT NOT NULL,
            default_unit TEXT NOT NULL,
            description TEXT NOT NULL
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
            monthly_availability TEXT NOT NULL,
            load_mode TEXT NOT NULL,
            notes TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS driver_reference (
            factor_key TEXT PRIMARY KEY,
            source_website TEXT,
            formula TEXT NOT NULL,
            confidence TEXT NOT NULL
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
        CREATE TABLE IF NOT EXISTS driver_impact_score (
            metric_month TEXT PRIMARY KEY,
            marketing_year TEXT NOT NULL,
            composite_score REAL NOT NULL,
            domestic_score REAL NOT NULL,
            weather_score REAL NOT NULL,
            global_score REAL NOT NULL,
            policy_score REAL NOT NULL,
            implied_price_adjustment_pct REAL NOT NULL,
            bullish_drivers_json TEXT NOT NULL,
            bearish_drivers_json TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS driver_impact_score_annual (
            marketing_year TEXT PRIMARY KEY,
            months_covered INTEGER NOT NULL,
            composite_score_avg REAL NOT NULL,
            domestic_score_avg REAL NOT NULL,
            weather_score_avg REAL NOT NULL,
            global_score_avg REAL NOT NULL,
            policy_score_avg REAL NOT NULL,
            implied_price_adjustment_pct_avg REAL NOT NULL,
            peak_bullish_month TEXT,
            peak_bearish_month TEXT,
            bullish_drivers_json TEXT NOT NULL,
            bearish_drivers_json TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )


def load_local_signals() -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    msp = {}
    procurement_actual = {}
    sowing = {}
    temp = {}
    frost = {}
    heat = {}
    with sqlite3.connect(str(WHEAT_SUPPORT_DB)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        for row in cur.execute("SELECT signal_date, marketing_season, value FROM wheat_support_signals WHERE signal_group='policy' AND signal_name='MSP' ORDER BY signal_date"):
            msp[str(row['signal_date'])] = float(row['value'])
        for row in cur.execute("SELECT signal_date, marketing_season, value FROM wheat_support_signals WHERE signal_group='procurement' AND signal_name='Actual wheat procurement' ORDER BY signal_date"):
            procurement_actual[str(row['signal_date'])[:7] + '-01'] = float(row['value'])
        for row in cur.execute("SELECT signal_date, signal_name, value FROM wheat_support_signals WHERE signal_group='acreage' AND signal_name='Progressive area sown' ORDER BY signal_date"):
            sowing[str(row['signal_date'])[:7] + '-01'] = float(row['value'])
        placeholders = ','.join('?' for _ in NORTH_INDIA_STATES)
        q = f"""
        SELECT substr(date,1,7)||'-01' AS metric_month,
               AVG(temperature_2m_mean) AS mean_temp,
               SUM(CASE WHEN temperature_2m_min <= 5 THEN 1 ELSE 0 END) AS frost_risk_days,
               SUM(CASE WHEN temperature_2m_max >= 32 AND substr(date,6,2) IN ('02','03') THEN 1 ELSE 0 END) AS heat_days
        FROM weather_daily
        WHERE state IN ({placeholders})
        GROUP BY substr(date,1,7)
        ORDER BY metric_month
        """
        rows = cur.execute(q, NORTH_INDIA_STATES).fetchall()
    for row in rows:
        month = str(row['metric_month'])
        temp[month] = round(float(row['mean_temp']), 6)
        frost[month] = float(row['frost_risk_days'])
        heat[month] = float(row['heat_days'])
    return msp, procurement_actual, sowing, temp, frost, heat


def load_annual_area_series() -> dict[str, float]:
    result = {}
    with sqlite3.connect(str(WHEAT_SUPPORT_DB)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT indicator_date, value FROM wheat_indicator_history WHERE indicator_key='wheat_area' ORDER BY indicator_date"
        ).fetchall()
    for row in rows:
        year = int(str(row['indicator_date'])[:4]) - 1
        result[f"{year}/{str(year + 1)[-2:]}"] = float(row['value']) * 10.0
    return result


def forward_fill_series(changes: dict[str, float], months: list[date], fallback: float) -> dict[str, float]:
    result = {}
    current = fallback
    change_map = {k[:10]: v for k, v in changes.items()}
    for d in months:
        month_key = d.isoformat()
        for key, value in change_map.items():
            if key <= month_key:
                current = value
        result[month_key] = current
    return result


def monthly_normals(series: dict[str, float]) -> dict[int, float]:
    buckets: dict[int, list[float]] = {}
    for key, value in series.items():
        month = int(key[5:7])
        buckets.setdefault(month, []).append(value)
    return {month: sum(vals) / len(vals) for month, vals in buckets.items()}


def event_series(months: list[date], events: dict[str, float], decay: float = 0.85) -> dict[str, float]:
    result = {}
    active = 0.0
    event_map = {f'{k}-01': v for k, v in events.items()}
    for d in months:
        key = d.isoformat()
        active *= decay
        if key in event_map:
            active = max(active, event_map[key])
        result[key] = round(active, 6)
    return result


def build_rows() -> list[tuple]:
    months = month_range(START_MONTH, END_MONTH)
    weights = normalize(PROCUREMENT_WEIGHTS)
    msp_rows, procurement_actual, sowing_actual, temp_actual, frost_actual, heat_actual = load_local_signals()
    annual_area_series = load_annual_area_series()
    temp_normals = monthly_normals(temp_actual)
    frost_normals = monthly_normals(frost_actual)
    heat_normals = monthly_normals(heat_actual)
    msp_series = forward_fill_series({**MSP_STEP_DATES, **msp_rows}, months, MSP_STEP_DATES['2016-04-01'])
    rows = []

    black_sea = event_series(months, BLACK_SEA_EVENTS, decay=0.90)
    russian_policy = event_series(months, RUSSIA_POLICY_EVENTS, decay=0.92)
    india_export = event_series(months, INDIA_EXPORT_POLICY_EVENTS, decay=0.94)

    for d in months:
        metric_month = d.isoformat()
        my = marketing_year_for_month(d)

        if metric_month in msp_rows:
            msp_value = msp_series[metric_month]
            msp_method = 'loaded_from_wheat_support_signals_step_series'
            msp_conf = 'high'
            msp_source = 'PIB'
            msp_url = 'https://www.pib.gov.in/'
            msp_note = 'Official MSP row carried forward as a monthly step series.'
        else:
            msp_value = msp_series[metric_month]
            msp_method = 'curated_official_history_step_series'
            msp_conf = 'medium'
            msp_source = 'Curated MSP history from official announcements'
            msp_url = 'https://www.pib.gov.in/'
            msp_note = 'Historical MSP carried forward as a monthly step series from annual announcement dates.'
        rows.append((f'msp:{metric_month}', 'msp', metric_month, my, round(msp_value, 6), 'INR/quintal', msp_source, msp_url, msp_method, msp_conf, msp_note, UPDATED_AT))

        annual_proc = PROCUREMENT_HISTORY.get(my, 0.0)
        if metric_month in procurement_actual:
            proc_value = procurement_actual[metric_month]
            proc_method = 'loaded_from_wheat_support_signals'
            proc_conf = 'high'
            proc_source = 'DFPD / PIB'
            proc_url = 'https://dfpd.gov.in/'
            proc_note = 'Official procurement row from local wheat support store.'
        else:
            proc_value = round(annual_proc * weights.get(d.month, 0.0), 6)
            proc_method = 'annual_procurement_to_monthly_peak_proxy'
            proc_conf = 'medium' if annual_proc else 'low'
            proc_source = 'Curated procurement history + local support rows'
            proc_url = 'https://dfpd.gov.in/'
            proc_note = 'Annual procurement distributed into Apr-Aug pulse months.'
        rows.append((f'proc:{metric_month}', 'fci_procurement', metric_month, my, proc_value, 'LMT', proc_source, proc_url, proc_method, proc_conf, proc_note, UPDATED_AT))

        if metric_month in sowing_actual:
            sow_value = sowing_actual[metric_month]
            sow_method = 'loaded_from_wheat_support_signals'
            sow_conf = 'high'
            sow_source = 'PIB'
            sow_url = 'https://www.pib.gov.in/'
            sow_note = 'Official progressive sowing row from local support store.'
        else:
            area_proxy = annual_area_series.get(my, 0.0)
            sow_value = round(area_proxy, 6)
            sow_method = 'annual_area_as_sowing_proxy'
            sow_conf = 'medium' if area_proxy else 'low'
            sow_source = 'Economic Survey Statistical Appendix'
            sow_url = 'https://desagri.gov.in/'
            sow_note = 'Annual wheat area expressed in lakh hectare and used as a sowing reference where progressive monthly sowing is unavailable.'
        rows.append((f'sow:{metric_month}', 'rabi_sowing_area', metric_month, my, sow_value, 'lakh_hectare', sow_source, sow_url, sow_method, sow_conf, sow_note, UPDATED_AT))

        if metric_month in temp_actual:
            temp_value = temp_actual[metric_month]
            temp_method = 'actual_weather_monthly_average'
            temp_conf = 'high'
            temp_note = 'Actual monthly mean temperature across major North India wheat states.'
        else:
            temp_value = round(temp_normals.get(d.month, 0.0), 6)
            temp_method = 'calendar_month_normal_backfill'
            temp_conf = 'medium'
            temp_note = 'Backfilled from available calendar-month normals in the local weather store.'
        rows.append((f'temp:{metric_month}', 'north_india_winter_temperature', metric_month, my, temp_value, 'celsius', 'Open-Meteo via local weather store', None, temp_method, temp_conf, temp_note, UPDATED_AT))

        if metric_month in frost_actual:
            frost_value = round(min(100.0, frost_actual[metric_month] * 2.5), 6)
            frost_method = 'actual_frost_risk_index'
            frost_conf = 'high'
            frost_note = 'Index from count of wheat-belt days with min temperature <= 5C.'
        else:
            frost_value = round(min(100.0, frost_normals.get(d.month, 0.0) * 2.5), 6)
            frost_method = 'calendar_month_normal_backfill'
            frost_conf = 'medium'
            frost_note = 'Backfilled frost-risk index from calendar-month normals.'
        rows.append((f'frost:{metric_month}', 'frost_risk', metric_month, my, frost_value, 'index', 'Open-Meteo via local weather store', None, frost_method, frost_conf, frost_note, UPDATED_AT))

        rows.append((f'blacksea:{metric_month}', 'black_sea_corridor', metric_month, my, black_sea[metric_month], 'policy_index', 'Curated Black Sea event timeline', 'https://www.un.org/', 'curated_event_decay_index', 'medium', 'Monthly event-decay index for Black Sea corridor disruption/reopening risk.', UPDATED_AT))
        rows.append((f'russia:{metric_month}', 'russian_export_policy', metric_month, my, russian_policy[metric_month], 'policy_index', 'Curated Russian policy timeline', None, 'curated_event_decay_index', 'medium', 'Monthly event-decay index for Russian wheat export policy pressure.', UPDATED_AT))
        rows.append((f'indiaexport:{metric_month}', 'india_export_policy', metric_month, my, india_export[metric_month], 'policy_index', 'Curated India export policy timeline', 'https://dgft.gov.in/', 'curated_event_decay_index', 'high', 'Monthly event-decay index for Indian wheat export bans / restrictions.', UPDATED_AT))
    return rows


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def build_driver_impact_rows(rows: list[tuple]) -> list[tuple]:
    value_by_factor: dict[str, list[tuple[str, str, float]]] = {}
    factor_bucket = {factor_key: bucket for factor_key, _, bucket, _, _ in FACTOR_DEFINITIONS}
    factor_name = {factor_key: name for factor_key, name, _, _, _ in FACTOR_DEFINITIONS}

    for _, factor_key, metric_month, marketing_year, value, *_rest in rows:
        value_by_factor.setdefault(factor_key, []).append((metric_month, marketing_year, float(value)))

    standardized: dict[str, dict[str, float]] = {}
    for factor_key, series in value_by_factor.items():
        values = [value for _, _, value in series]
        mean_value = sum(values) / len(values) if values else 0.0
        variance = sum((value - mean_value) ** 2 for value in values) / len(values) if values else 0.0
        std_value = variance ** 0.5
        standardized[factor_key] = {}
        for metric_month, _marketing_year, value in series:
            if std_value <= 1e-9:
                z_score = 0.0
            else:
                z_score = (value - mean_value) / std_value
            contribution = DRIVER_DIRECTIONS.get(factor_key, 1.0) * DRIVER_WEIGHTS.get(factor_key, 0.1) * z_score
            standardized[factor_key][metric_month] = float(contribution)

    months = sorted({metric_month for factor_rows in value_by_factor.values() for metric_month, _, _ in factor_rows})
    marketing_year_lookup = {
        metric_month: marketing_year
        for factor_rows in value_by_factor.values()
        for metric_month, marketing_year, _value in factor_rows
    }

    impact_rows: list[tuple] = []
    for metric_month in months:
        bucket_sums = {'Domestic': 0.0, 'Weather': 0.0, 'Global': 0.0, 'Policy': 0.0}
        factor_effects = []
        for factor_key, month_map in standardized.items():
            contribution = month_map.get(metric_month, 0.0)
            bucket = factor_bucket.get(factor_key, 'Domestic')
            bucket_sums[bucket] += contribution
            factor_effects.append(
                {
                    'factor_key': factor_key,
                    'factor_name': factor_name.get(factor_key, factor_key),
                    'bucket': bucket,
                    'contribution': round(contribution, 6),
                }
            )

        raw_score = sum(bucket_sums.values())
        composite_score = clamp(50.0 + raw_score * 18.0, 0.0, 100.0)
        bucket_scores = {
            bucket: clamp(50.0 + bucket_sums[bucket] * 30.0 * BUCKET_WEIGHTS.get(bucket, 1.0), 0.0, 100.0)
            for bucket in bucket_sums
        }
        implied_adjustment = clamp(raw_score * 1.15, -4.0, 4.0)
        bullish = sorted(
            [item for item in factor_effects if item['contribution'] > 0],
            key=lambda item: item['contribution'],
            reverse=True,
        )[:3]
        bearish = sorted(
            [item for item in factor_effects if item['contribution'] < 0],
            key=lambda item: item['contribution'],
        )[:3]

        impact_rows.append(
            (
                metric_month,
                marketing_year_lookup[metric_month],
                round(composite_score, 6),
                round(bucket_scores['Domestic'], 6),
                round(bucket_scores['Weather'], 6),
                round(bucket_scores['Global'], 6),
                round(bucket_scores['Policy'], 6),
                round(implied_adjustment, 6),
                json.dumps(bullish),
                json.dumps(bearish),
                'Composite Wheat driver overlay built from standardized monthly driver contributions.',
                UPDATED_AT,
            )
        )
    return impact_rows


def build_driver_impact_annual_rows(rows: list[tuple], impact_rows: list[tuple]) -> list[tuple]:
    factor_bucket = {factor_key: bucket for factor_key, _, bucket, _, _ in FACTOR_DEFINITIONS}
    factor_name = {factor_key: name for factor_key, name, _, _, _ in FACTOR_DEFINITIONS}
    by_factor: dict[str, dict[str, float]] = {}
    for _, factor_key, metric_month, marketing_year, value, *_ in rows:
        by_factor.setdefault(marketing_year, {})
        by_factor[marketing_year].setdefault(factor_key, [])
        by_factor[marketing_year][factor_key].append(float(value))

    annual_groups: dict[str, list[tuple]] = {}
    for row in impact_rows:
        marketing_year = row[1]
        annual_groups.setdefault(marketing_year, []).append(row)

    annual_rows: list[tuple] = []
    for marketing_year, monthly_rows in sorted(annual_groups.items()):
        months_covered = len(monthly_rows)
        composite_avg = sum(r[2] for r in monthly_rows) / months_covered
        domestic_avg = sum(r[3] for r in monthly_rows) / months_covered
        weather_avg = sum(r[4] for r in monthly_rows) / months_covered
        global_avg = sum(r[5] for r in monthly_rows) / months_covered
        policy_avg = sum(r[6] for r in monthly_rows) / months_covered
        implied_avg = sum(r[7] for r in monthly_rows) / months_covered
        peak_bullish = max(monthly_rows, key=lambda item: item[7])[0]
        peak_bearish = min(monthly_rows, key=lambda item: item[7])[0]

        factor_effects = []
        for factor_key, values in by_factor.get(marketing_year, {}).items():
            avg_value = sum(values) / len(values) if values else 0.0
            direction = DRIVER_DIRECTIONS.get(factor_key, 1.0)
            weight = DRIVER_WEIGHTS.get(factor_key, 0.1)
            signed_level = direction * weight * avg_value
            factor_effects.append(
                {
                    "factor_key": factor_key,
                    "factor_name": factor_name.get(factor_key, factor_key),
                    "bucket": factor_bucket.get(factor_key, "Domestic"),
                    "signed_level": round(signed_level, 6),
                    "avg_value": round(avg_value, 6),
                }
            )
        bullish = sorted(
            [item for item in factor_effects if item["signed_level"] > 0],
            key=lambda item: item["signed_level"],
            reverse=True,
        )[:3]
        bearish = sorted(
            [item for item in factor_effects if item["signed_level"] < 0],
            key=lambda item: item["signed_level"],
        )[:3]
        annual_rows.append(
            (
                marketing_year,
                months_covered,
                round(composite_avg, 6),
                round(domestic_avg, 6),
                round(weather_avg, 6),
                round(global_avg, 6),
                round(policy_avg, 6),
                round(implied_avg, 6),
                peak_bullish,
                peak_bearish,
                json.dumps(bullish),
                json.dumps(bearish),
                "Annual Wheat driver score summary for S&D reporting, aggregated from monthly impact scores.",
                UPDATED_AT,
            )
        )
    return annual_rows


def build_db() -> dict:
    months = month_range(START_MONTH, END_MONTH)
    rows = build_rows()
    impact_rows = build_driver_impact_rows(rows)
    impact_annual_rows = build_driver_impact_annual_rows(rows, impact_rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(OUTPUT_DB)) as conn:
        build_schema(conn)
        conn.executemany("INSERT INTO factor_definitions VALUES (?, ?, ?, ?, ?) ON CONFLICT(factor_key) DO UPDATE SET factor_name=excluded.factor_name, driver_bucket=excluded.driver_bucket, default_unit=excluded.default_unit, description=excluded.description", FACTOR_DEFINITIONS)
        conn.executemany("INSERT INTO source_inventory VALUES (?, ?, ?, ?, ?) ON CONFLICT(source_key) DO UPDATE SET source_name=excluded.source_name, source_url=excluded.source_url, cadence=excluded.cadence, notes=excluded.notes", SOURCE_INVENTORY)
        conn.executemany("INSERT INTO factor_status VALUES (?, ?, ?, ?) ON CONFLICT(factor_key) DO UPDATE SET monthly_availability=excluded.monthly_availability, load_mode=excluded.load_mode, notes=excluded.notes", FACTOR_STATUS)
        conn.executemany("INSERT INTO driver_reference VALUES (?, ?, ?, ?) ON CONFLICT(factor_key) DO UPDATE SET source_website=excluded.source_website, formula=excluded.formula, confidence=excluded.confidence", DRIVER_REFERENCE)
        conn.execute('DELETE FROM factor_monthly_values')
        conn.execute('DELETE FROM driver_impact_score')
        conn.execute('DELETE FROM driver_impact_score_annual')
        conn.executemany("INSERT INTO factor_monthly_values (id, factor_key, metric_month, marketing_year, value, unit, source_name, source_url, method, confidence, notes, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
        conn.executemany("INSERT INTO driver_impact_score (metric_month, marketing_year, composite_score, domestic_score, weather_score, global_score, policy_score, implied_price_adjustment_pct, bullish_drivers_json, bearish_drivers_json, notes, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", impact_rows)
        conn.executemany("INSERT INTO driver_impact_score_annual (marketing_year, months_covered, composite_score_avg, domestic_score_avg, weather_score_avg, global_score_avg, policy_score_avg, implied_price_adjustment_pct_avg, peak_bullish_month, peak_bearish_month, bullish_drivers_json, bearish_drivers_json, notes, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", impact_annual_rows)
        conn.commit()
        factor_counts = dict(conn.execute("SELECT factor_key, COUNT(*) FROM factor_monthly_values GROUP BY factor_key").fetchall())
        impact_range = conn.execute("SELECT MIN(metric_month), MAX(metric_month), COUNT(*) FROM driver_impact_score").fetchone()
        annual_count = conn.execute("SELECT COUNT(*) FROM driver_impact_score_annual").fetchone()[0]
    return {'status':'success','db_path':str(OUTPUT_DB),'from':months[0].isoformat(),'to':months[-1].isoformat(),'rows_written':len(rows),'factor_counts':factor_counts,'impact_rows_written':int(impact_range[2]),'impact_annual_rows_written':int(annual_count)}


if __name__ == '__main__':
    print(json.dumps(build_db(), indent=2))
