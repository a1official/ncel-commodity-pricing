from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DB = OUTPUT_DIR / 'maize_data_collection_plan.db'
UPDATED_AT = datetime.now(UTC).isoformat().replace('+00:00', 'Z')

DATA_POINTS = [
    ('india_area', 'India maize area', 'supply', 'annual', 'high'),
    ('india_yield', 'India maize yield', 'supply', 'annual', 'high'),
    ('india_production', 'India maize production', 'supply', 'annual', 'high'),
    ('india_opening_stock', 'India opening stock', 'supply', 'monthly', 'high'),
    ('india_imports', 'India maize imports', 'supply/trade', 'monthly', 'medium'),
    ('global_us_corn_production', 'US corn production', 'global_supply', 'monthly', 'high'),
    ('global_brazil_safrinha', 'Brazil safrinha harvest intensity', 'global_supply', 'monthly', 'medium'),
    ('feed_use', 'Maize feed use', 'demand', 'monthly', 'high'),
    ('poultry_cycle', 'Poultry demand cycle', 'demand', 'monthly', 'high'),
    ('industrial_use', 'Maize industrial use', 'demand', 'monthly', 'medium'),
    ('exports', 'India maize exports', 'demand/trade', 'monthly', 'medium'),
    ('ethanol_signal', 'Ethanol demand signal', 'policy_demand', 'monthly', 'medium'),
    ('substitution_effect', 'Maize vs wheat substitution', 'market', 'monthly', 'medium'),
    ('retail_price_pressure', 'Retail/mandi price pressure', 'market', 'monthly', 'high'),
    ('policy_changes', 'Policy event intensity', 'policy', 'monthly', 'medium'),
    ('population_trend', 'Population trend', 'macro', 'annual', 'low'),
    ('msp_maize', 'Maize MSP', 'price_driver', 'annual', 'high'),
    ('monsoon_distribution_risk', 'Monsoon distribution risk', 'weather', 'monthly', 'high'),
    ('driver_composite_score', 'Composite price-driver score', 'price_driver', 'monthly', 'high'),
]

SOURCES = [
    ('economic_survey', 'Economic Survey Statistical Appendix', 'https://www.indiabudget.gov.in/economicsurvey/doc/Statistical-Appendix-in-English.pdf', 'pdf', 'annual'),
    ('usda_psd', 'USDA PSD', 'https://apps.fas.usda.gov/psdonline/app/index.html#/app/home', 'web', 'monthly'),
    ('usda_wasde', 'USDA WASDE', 'https://www.usda.gov/oce/commodity/wasde', 'pdf/web', 'monthly'),
    ('apeda', 'APEDA', 'https://apeda.gov.in/', 'web/pdf', 'monthly'),
    ('agmarknet', 'Agmarknet', 'https://agmarknet.gov.in/', 'web', 'daily'),
    ('imd', 'India Meteorological Department', 'https://mausam.imd.gov.in/', 'web', 'weekly/seasonal'),
    ('dgft', 'DGFT', 'https://www.dgft.gov.in/CP/', 'web', 'event-driven'),
    ('world_bank', 'World Bank Population', 'https://data.worldbank.org/indicator/SP.POP.TOTL', 'api/web', 'annual'),
    ('mopng', 'Ministry of Petroleum and Natural Gas', 'https://mopng.gov.in/', 'web', 'policy updates'),
    ('fao', 'FAO', 'https://www.fao.org/', 'web', 'seasonal'),
]

PLAN_ROWS = [
    ('india_area', 'economic_survey', 'loaded', '2016-04-01', '2026-03-01', 'SnD/supply/maize/maize_supply_factors.db', 'maize_factor_monthly_values', 'annual_to_monthly_hold_constant', 'refresh annually after Economic Survey update', 'coverage_120_months_and_non_null', 'SnD team'),
    ('india_yield', 'economic_survey', 'loaded', '2016-04-01', '2026-03-01', 'SnD/supply/maize/maize_supply_factors.db', 'maize_factor_monthly_values', 'annual_to_monthly_hold_constant', 'refresh annually after Economic Survey update', 'coverage_120_months_and_non_null', 'SnD team'),
    ('india_production', 'economic_survey', 'loaded', '2016-04-01', '2026-03-01', 'SnD/supply/maize/maize_supply_factors.db', 'maize_factor_monthly_values', 'annual_to_monthly_harvest_weights', 'refresh annually + crop-year update', 'weights_sum_to_one_and_coverage_120', 'SnD team'),
    ('india_opening_stock', 'usda_psd', 'loaded', '2016-04-01', '2026-03-01', 'SnD/supply/maize/maize_supply_factors.db', 'maize_factor_monthly_values', 'annual_stock_interpolation', 'refresh monthly', 'coverage_120_months_and_reasonable_bounds', 'SnD team'),
    ('india_imports', 'apeda', 'partial', '2016-04-01', '2026-03-01', 'SnD/supply/maize/maize_supply_factors.db', 'maize_factor_monthly_values', 'annual_to_monthly_uniform_proxy', 'refresh monthly when trade update available', 'coverage_120_and_outlier_check', 'SnD team'),
    ('global_us_corn_production', 'usda_wasde', 'loaded', '2016-04-01', '2026-03-01', 'SnD/supply/maize/maize_supply_factors.db', 'maize_factor_monthly_values', 'marketing_year_hold_constant', 'refresh monthly WASDE release', 'coverage_120_and_country_consistency', 'SnD team'),
    ('global_brazil_safrinha', 'fao', 'loaded', '2016-04-01', '2026-03-01', 'SnD/supply/maize/maize_supply_factors.db', 'maize_factor_monthly_values', 'curated_seasonal_profile', 'refresh pre-season and mid-season', 'profile_shape_and_coverage_120', 'SnD team'),
    ('feed_use', 'economic_survey', 'loaded', '2016-04-01', '2026-03-01', 'SnD/demand/maize/maize_demand_monthly.db', 'maize_factor_monthly_values', 'annual_to_monthly_feed_weights', 'refresh crop-year close', 'coverage_120_and_mass_balance', 'SnD team'),
    ('poultry_cycle', 'apeda', 'loaded', '2016-04-01', '2026-03-01', 'SnD/demand/maize/maize_demand_monthly.db', 'maize_factor_monthly_values', 'curated_monthly_profile', 'refresh quarterly', 'coverage_120_and_range_check', 'SnD team'),
    ('industrial_use', 'economic_survey', 'loaded', '2016-04-01', '2026-03-01', 'SnD/demand/maize/maize_demand_monthly.db', 'maize_factor_monthly_values', 'annual_to_monthly_proxy', 'refresh crop-year close', 'coverage_120_and_non_negative', 'SnD team'),
    ('exports', 'apeda', 'partial', '2016-04-01', '2026-03-01', 'SnD/demand/maize/maize_demand_monthly.db', 'maize_factor_monthly_values', 'annual_exports_to_monthly_proxy', 'refresh monthly', 'coverage_120_and_trade_spike_check', 'SnD team'),
    ('ethanol_signal', 'mopng', 'loaded', '2016-04-01', '2026-03-01', 'SnD/demand/maize/maize_demand_monthly.db', 'maize_factor_monthly_values', 'curated_step_signal', 'refresh on policy change', 'coverage_120_and_step_change_audit', 'SnD team'),
    ('substitution_effect', 'agmarknet', 'loaded', '2016-04-01', '2026-03-01', 'SnD/demand/maize/maize_demand_monthly.db', 'maize_factor_monthly_values', 'monthly_ratio_index', 'refresh monthly', 'coverage_120_and_index_bounds', 'SnD team'),
    ('retail_price_pressure', 'agmarknet', 'loaded', '2016-04-01', '2026-03-01', 'SnD/demand/maize/maize_demand_monthly.db', 'maize_factor_monthly_values', 'monthly_price_index', 'refresh monthly', 'coverage_120_and_outlier_scan', 'SnD team'),
    ('policy_changes', 'dgft', 'loaded', '2016-04-01', '2026-03-01', 'SnD/demand/maize/maize_demand_monthly.db', 'maize_factor_monthly_values', 'curated_event_series', 'refresh on policy notification', 'coverage_120_and_event_log_match', 'SnD team'),
    ('population_trend', 'world_bank', 'loaded', '2016-04-01', '2026-03-01', 'SnD/demand/maize/maize_demand_monthly.db', 'maize_factor_monthly_values', 'annual_to_monthly_interpolation', 'refresh annually', 'coverage_120_and_monotonicity_check', 'SnD team'),
    ('msp_maize', 'economic_survey', 'loaded', '2016-04-01', '2026-03-01', 'SnD/price_drivers/maize/maize_price_drivers.db', 'maize_driver_monthly_values', 'annual_to_monthly_step', 'refresh on MSP announcement', 'coverage_120_and_step_dates_match', 'SnD team'),
    ('monsoon_distribution_risk', 'imd', 'loaded', '2016-04-01', '2026-03-01', 'SnD/price_drivers/maize/maize_price_drivers.db', 'maize_driver_monthly_values', 'curated_monthly_profile', 'refresh pre-monsoon', 'coverage_120_and_profile_bounds', 'SnD team'),
    ('driver_composite_score', 'usda_wasde', 'loaded', '2016-04-01', '2026-03-01', 'SnD/price_drivers/maize/maize_price_drivers.db', 'maize_driver_impact_score', 'weighted_standardized_composite', 'refresh monthly after all inputs update', 'coverage_120_and_bucket_consistency', 'SnD team'),
]


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS maize_data_points (
            data_key TEXT PRIMARY KEY,
            data_name TEXT NOT NULL,
            category TEXT NOT NULL,
            frequency TEXT NOT NULL,
            priority TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS maize_data_sources (
            source_key TEXT PRIMARY KEY,
            source_name TEXT NOT NULL,
            source_link TEXT NOT NULL,
            source_type TEXT NOT NULL,
            cadence TEXT
        );
        CREATE TABLE IF NOT EXISTS maize_collection_plan (
            id TEXT PRIMARY KEY,
            data_key TEXT NOT NULL,
            source_key TEXT NOT NULL,
            status TEXT NOT NULL,
            data_from TEXT,
            data_to TEXT,
            target_db TEXT NOT NULL,
            target_table TEXT NOT NULL,
            method TEXT NOT NULL,
            refresh_rule TEXT NOT NULL,
            qa_rule TEXT NOT NULL,
            owner TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS maize_collection_status_log (
            id TEXT PRIMARY KEY,
            run_date TEXT NOT NULL,
            data_key TEXT NOT NULL,
            status TEXT NOT NULL,
            rows_loaded INTEGER,
            notes TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def reset(conn: sqlite3.Connection) -> None:
    for table in ('maize_data_points', 'maize_data_sources', 'maize_collection_plan', 'maize_collection_status_log'):
        conn.execute(f'DELETE FROM {table}')
    conn.commit()


def build() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect(OUTPUT_DB)
    ensure_schema(conn)
    reset(conn)

    conn.executemany('INSERT INTO maize_data_points VALUES (?, ?, ?, ?, ?)', DATA_POINTS)
    conn.executemany('INSERT INTO maize_data_sources VALUES (?, ?, ?, ?, ?)', SOURCES)

    conn.executemany(
        """
        INSERT INTO maize_collection_plan (
            id, data_key, source_key, status, data_from, data_to, target_db, target_table,
            method, refresh_rule, qa_rule, owner, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                f'maize-plan-{i:03d}', row[0], row[1], row[2], row[3], row[4], row[5], row[6],
                row[7], row[8], row[9], row[10], UPDATED_AT
            )
            for i, row in enumerate(PLAN_ROWS, start=1)
        ],
    )

    run_date = datetime.now(UTC).date().isoformat()
    conn.executemany(
        """
        INSERT INTO maize_collection_status_log (
            id, run_date, data_key, status, rows_loaded, notes, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                f'maize-log-{i:03d}',
                run_date,
                row[0],
                row[2],
                120 if row[2] == 'loaded' else None,
                f"Initial Step 6 status for {row[0]}",
                UPDATED_AT,
            )
            for i, row in enumerate(PLAN_ROWS, start=1)
        ],
    )
    conn.commit()

    out = {
        'db_path': str(OUTPUT_DB),
        'maize_data_points': conn.execute('SELECT COUNT(*) FROM maize_data_points').fetchone()[0],
        'maize_data_sources': conn.execute('SELECT COUNT(*) FROM maize_data_sources').fetchone()[0],
        'maize_collection_plan': conn.execute('SELECT COUNT(*) FROM maize_collection_plan').fetchone()[0],
        'maize_collection_status_log': conn.execute('SELECT COUNT(*) FROM maize_collection_status_log').fetchone()[0],
    }
    conn.close()
    return out


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
