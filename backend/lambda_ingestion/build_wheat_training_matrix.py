from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


FEATURE_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "wheat_model_support.db"
TRAINING_CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "wheat_training_matrix_daily.csv"
WHEAT_DRIVER_DB_PATH = Path(__file__).resolve().parents[2] / "SnD" / "price_drivers" / "wheat" / "wheat_price_drivers.db"
WHEAT_TRADE_FLOW_DB_PATH = Path(__file__).resolve().parents[2] / "SnD" / "trade_flow" / "wheat" / "wheat_trade_flow.db"
WHEAT_RISK_DB_PATH = Path(__file__).resolve().parents[2] / "SnD" / "risk_register" / "wheat" / "wheat_risk_register.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(FEATURE_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS wheat_training_matrix_daily (
            state TEXT NOT NULL,
            date TEXT NOT NULL,
            modal_price REAL NOT NULL,
            normalized_price_per_kg REAL,
            arrival_quantity REAL NOT NULL,
            market_count INTEGER NOT NULL,
            variety_count INTEGER NOT NULL,
            record_count INTEGER NOT NULL,
            price_lag_1 REAL,
            price_lag_7 REAL,
            price_lag_14 REAL,
            price_lag_30 REAL,
            price_rolling_mean_7 REAL,
            price_rolling_mean_30 REAL,
            price_rolling_std_7 REAL,
            price_rolling_std_30 REAL,
            arrival_lag_1 REAL,
            arrival_rolling_mean_7 REAL,
            arrival_rolling_mean_30 REAL,
            arrival_momentum_7 REAL,
            temperature_2m_mean REAL,
            temperature_2m_max REAL,
            temperature_2m_min REAL,
            precipitation_sum REAL,
            rain_sum REAL,
            wind_speed_10m_max REAL,
            shortwave_radiation_sum REAL,
            et0_fao_evapotranspiration REAL,
            relative_humidity_2m_mean REAL,
            soil_moisture_0_to_7cm_mean REAL,
            soil_moisture_7_to_28cm_mean REAL,
            soil_temperature_0_to_7cm_mean REAL,
            precipitation_rolling_sum_7 REAL,
            temp_rolling_mean_7 REAL,
            humidity_rolling_mean_7 REAL,
            soil_moisture_rolling_mean_7 REAL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL,
            iso_week INTEGER NOT NULL,
            day_of_year INTEGER NOT NULL,
            quarter INTEGER NOT NULL,
            is_weekend INTEGER NOT NULL,
            month_sin REAL NOT NULL,
            month_cos REAL NOT NULL,
            day_of_year_sin REAL NOT NULL,
            day_of_year_cos REAL NOT NULL,
            is_rabi_sowing_window INTEGER NOT NULL,
            is_rabi_growth_window INTEGER NOT NULL,
            is_rabi_harvest_window INTEGER NOT NULL,
            is_procurement_window INTEGER NOT NULL,
            target_next_day_price REAL,
            target_next_7d_avg_price REAL,
            wheat_yield_kg_per_hectare REAL,
            wheat_production_million_tonnes REAL,
            wheat_area_million_hectare REAL,
            cpi_inflation_rate REAL,
            policy_repo_rate REAL,
            government_buffer_wheat_stock REAL,
            government_buffer_wheat_stock_norm REAL,
            wheat_central_pool_exports REAL,
            global_wheat_benchmark_avg_usd_mt REAL,
            global_wheat_benchmark_srw_usd_mt REAL,
            global_wheat_benchmark_hrw_usd_mt REAL,
            msp_inr_quintal REAL,
            cost_of_production_inr_quintal REAL,
            margin_over_cost_percent REAL,
            procurement_actual_lmt REAL,
            procurement_estimated_lmt REAL,
            progressive_area_sown_lakh_hectare REAL,
            final_area_previous_season_lakh_hectare REAL,
            wheat_driver_composite_score REAL,
            wheat_driver_domestic_score REAL,
            wheat_driver_weather_score REAL,
            wheat_driver_global_score REAL,
            wheat_driver_policy_score REAL,
            wheat_driver_price_adjustment_pct REAL,
            wheat_export_quantity_monthly REAL,
            wheat_import_quantity_monthly REAL,
            wheat_export_value_inr_crore_monthly REAL,
            wheat_import_value_inr_crore_monthly REAL,
            wheat_export_concentration_hhi REAL,
            wheat_import_concentration_hhi REAL,
            wheat_export_seasonality_share_pct REAL,
            wheat_risk_price_volatility_score REAL,
            wheat_risk_weather_climate_score REAL,
            wheat_risk_geopolitical_black_sea_score REAL,
            wheat_risk_policy_trade_restriction_score REAL,
            wheat_risk_supply_stock_tightness_score REAL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (state, date)
        );
        """
    )
    existing_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(wheat_training_matrix_daily)").fetchall()
    }
    required_columns = {
        "wheat_driver_composite_score": "REAL",
        "wheat_driver_domestic_score": "REAL",
        "wheat_driver_weather_score": "REAL",
        "wheat_driver_global_score": "REAL",
        "wheat_driver_policy_score": "REAL",
        "wheat_driver_price_adjustment_pct": "REAL",
        "wheat_export_quantity_monthly": "REAL",
        "wheat_import_quantity_monthly": "REAL",
        "wheat_export_value_inr_crore_monthly": "REAL",
        "wheat_import_value_inr_crore_monthly": "REAL",
        "wheat_export_concentration_hhi": "REAL",
        "wheat_import_concentration_hhi": "REAL",
        "wheat_export_seasonality_share_pct": "REAL",
        "wheat_risk_price_volatility_score": "REAL",
        "wheat_risk_weather_climate_score": "REAL",
        "wheat_risk_geopolitical_black_sea_score": "REAL",
        "wheat_risk_policy_trade_restriction_score": "REAL",
        "wheat_risk_supply_stock_tightness_score": "REAL",
    }
    for column_name, column_type in required_columns.items():
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE wheat_training_matrix_daily ADD COLUMN {column_name} {column_type}")
    conn.commit()


def _read_feature_frame(conn: sqlite3.Connection) -> pd.DataFrame:
    frame = pd.read_sql_query(
        """
        SELECT *
        FROM wheat_feature_daily
        ORDER BY state, date
        """,
        conn,
    )
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


def _read_indicator_frame(conn: sqlite3.Connection) -> pd.DataFrame:
    frame = pd.read_sql_query(
        """
        SELECT indicator_key, indicator_date, value
        FROM wheat_indicator_history
        ORDER BY indicator_date
        """,
        conn,
    )
    frame["indicator_date"] = pd.to_datetime(frame["indicator_date"])
    return frame


def _read_benchmark_frame(conn: sqlite3.Connection) -> pd.DataFrame:
    frame = pd.read_sql_query(
        """
        SELECT benchmark_month, wheat_us_srw, wheat_us_hrw, benchmark_average
        FROM global_wheat_benchmark_monthly
        ORDER BY benchmark_month
        """,
        conn,
    )
    frame["benchmark_month"] = pd.to_datetime(frame["benchmark_month"])
    return frame.rename(
        columns={
            "benchmark_month": "date",
            "benchmark_average": "global_wheat_benchmark_avg_usd_mt",
            "wheat_us_srw": "global_wheat_benchmark_srw_usd_mt",
            "wheat_us_hrw": "global_wheat_benchmark_hrw_usd_mt",
        }
    )


def _read_support_signal_frame(conn: sqlite3.Connection) -> pd.DataFrame:
    frame = pd.read_sql_query(
        """
        SELECT signal_date, signal_name, value
        FROM wheat_support_signals
        ORDER BY signal_date
        """,
        conn,
    )
    frame["signal_date"] = pd.to_datetime(frame["signal_date"])
    return frame


def _read_driver_frame() -> pd.DataFrame:
    if not WHEAT_DRIVER_DB_PATH.exists():
        return pd.DataFrame(
            columns=[
                "metric_month",
                "wheat_driver_composite_score",
                "wheat_driver_domestic_score",
                "wheat_driver_weather_score",
                "wheat_driver_global_score",
                "wheat_driver_policy_score",
                "wheat_driver_price_adjustment_pct",
            ]
        )
    with sqlite3.connect(WHEAT_DRIVER_DB_PATH) as driver_conn:
        frame = pd.read_sql_query(
            """
            SELECT
                metric_month,
                composite_score AS wheat_driver_composite_score,
                domestic_score AS wheat_driver_domestic_score,
                weather_score AS wheat_driver_weather_score,
                global_score AS wheat_driver_global_score,
                policy_score AS wheat_driver_policy_score,
                implied_price_adjustment_pct AS wheat_driver_price_adjustment_pct
            FROM driver_impact_score
            ORDER BY metric_month
            """,
            driver_conn,
        )
    frame["metric_month"] = pd.to_datetime(frame["metric_month"])
    return frame


def _read_trade_feature_frame() -> pd.DataFrame:
    if not WHEAT_TRADE_FLOW_DB_PATH.exists():
        return pd.DataFrame(
            columns=[
                "metric_month",
                "wheat_export_quantity_monthly",
                "wheat_import_quantity_monthly",
                "wheat_export_value_inr_crore_monthly",
                "wheat_import_value_inr_crore_monthly",
                "wheat_export_concentration_hhi",
                "wheat_import_concentration_hhi",
                "wheat_export_seasonality_share_pct",
            ]
        )
    with sqlite3.connect(WHEAT_TRADE_FLOW_DB_PATH) as trade_conn:
        monthly_totals = pd.read_sql_query(
            """
            SELECT
                metric_month,
                flow_type,
                SUM(quantity) AS quantity,
                SUM(value_inr_crore) AS value_inr_crore,
                SUM(quantity * quantity) / NULLIF(SUM(quantity) * SUM(quantity), 0) AS concentration_hhi
            FROM bilateral_monthly_flows
            GROUP BY metric_month, flow_type
            ORDER BY metric_month, flow_type
            """,
            trade_conn,
        )
        seasonality = pd.read_sql_query(
            """
            SELECT
                month,
                avg_5y_share_pct AS wheat_export_seasonality_share_pct
            FROM seasonal_export_chart
            """,
            trade_conn,
        )
    if monthly_totals.empty:
        return pd.DataFrame(
            columns=[
                "metric_month",
                "wheat_export_quantity_monthly",
                "wheat_import_quantity_monthly",
                "wheat_export_value_inr_crore_monthly",
                "wheat_import_value_inr_crore_monthly",
                "wheat_export_concentration_hhi",
                "wheat_import_concentration_hhi",
                "wheat_export_seasonality_share_pct",
            ]
        )
    monthly_totals["metric_month"] = pd.to_datetime(monthly_totals["metric_month"])
    pivot = monthly_totals.pivot_table(
        index="metric_month",
        columns="flow_type",
        values=["quantity", "value_inr_crore", "concentration_hhi"],
        aggfunc="first",
    )
    pivot.columns = [
        {
            ("quantity", "export"): "wheat_export_quantity_monthly",
            ("quantity", "import"): "wheat_import_quantity_monthly",
            ("value_inr_crore", "export"): "wheat_export_value_inr_crore_monthly",
            ("value_inr_crore", "import"): "wheat_import_value_inr_crore_monthly",
            ("concentration_hhi", "export"): "wheat_export_concentration_hhi",
            ("concentration_hhi", "import"): "wheat_import_concentration_hhi",
        }.get((metric, flow), f"{flow}_{metric}")
        for metric, flow in pivot.columns
    ]
    frame = pivot.reset_index()
    frame["month"] = frame["metric_month"].dt.month
    frame = frame.merge(seasonality, on="month", how="left").drop(columns=["month"])
    return frame


def _read_risk_feature_frame() -> pd.DataFrame:
    if not WHEAT_RISK_DB_PATH.exists():
        return pd.DataFrame(
            columns=[
                "metric_month",
                "wheat_risk_price_volatility_score",
                "wheat_risk_weather_climate_score",
                "wheat_risk_geopolitical_black_sea_score",
                "wheat_risk_policy_trade_restriction_score",
                "wheat_risk_supply_stock_tightness_score",
            ]
        )
    with sqlite3.connect(WHEAT_RISK_DB_PATH) as risk_conn:
        frame = pd.read_sql_query(
            """
            SELECT
                metric_month,
                risk_key,
                composite_risk_score
            FROM risk_register_history
            ORDER BY metric_month, risk_key
            """,
            risk_conn,
        )
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "metric_month",
                "wheat_risk_price_volatility_score",
                "wheat_risk_weather_climate_score",
                "wheat_risk_geopolitical_black_sea_score",
                "wheat_risk_policy_trade_restriction_score",
                "wheat_risk_supply_stock_tightness_score",
            ]
        )
    frame["metric_month"] = pd.to_datetime(frame["metric_month"])
    pivot = frame.pivot_table(
        index="metric_month",
        columns="risk_key",
        values="composite_risk_score",
        aggfunc="first",
    ).reset_index()
    return pivot.rename(
        columns={
            "price_volatility": "wheat_risk_price_volatility_score",
            "weather_climate": "wheat_risk_weather_climate_score",
            "geopolitical_black_sea": "wheat_risk_geopolitical_black_sea_score",
            "policy_trade_restriction": "wheat_risk_policy_trade_restriction_score",
            "supply_stock_tightness": "wheat_risk_supply_stock_tightness_score",
        }
    )


def _attach_indicator_asof(base: pd.DataFrame, indicator_frame: pd.DataFrame, source_key: str, target_column: str) -> pd.DataFrame:
    subset = indicator_frame[indicator_frame["indicator_key"] == source_key][["indicator_date", "value"]].copy()
    if subset.empty:
        base[target_column] = pd.NA
        return base
    subset = subset.sort_values("indicator_date").rename(columns={"indicator_date": "asof_date", "value": target_column})
    base = pd.merge_asof(
        base.sort_values("date"),
        subset,
        left_on="date",
        right_on="asof_date",
        direction="backward",
    )
    return base.drop(columns=["asof_date"])


def _attach_support_signal_asof(base: pd.DataFrame, support_frame: pd.DataFrame, signal_name: str, target_column: str) -> pd.DataFrame:
    subset = support_frame[support_frame["signal_name"] == signal_name][["signal_date", "value"]].copy()
    if subset.empty:
        base[target_column] = pd.NA
        return base
    subset = subset.sort_values("signal_date").rename(columns={"signal_date": "asof_date", "value": target_column})
    base = pd.merge_asof(
        base.sort_values("date"),
        subset,
        left_on="date",
        right_on="asof_date",
        direction="backward",
    )
    return base.drop(columns=["asof_date"])


def _build_training_frame(conn: sqlite3.Connection) -> pd.DataFrame:
    base = _read_feature_frame(conn).sort_values(["state", "date"]).reset_index(drop=True)
    indicators = _read_indicator_frame(conn)
    benchmarks = _read_benchmark_frame(conn)
    support_signals = _read_support_signal_frame(conn)
    driver_scores = _read_driver_frame()
    trade_features = _read_trade_feature_frame()
    risk_features = _read_risk_feature_frame()

    for source_key, target_column in [
        ("wheat_yield_kg_per_hectare", "wheat_yield_kg_per_hectare"),
        ("wheat_production", "wheat_production_million_tonnes"),
        ("wheat_area", "wheat_area_million_hectare"),
        ("cpi_inflation_rate", "cpi_inflation_rate"),
        ("policy_repo_rate", "policy_repo_rate"),
        ("government_buffer_wheat_stock", "government_buffer_wheat_stock"),
        ("government_buffer_wheat_stock_norm", "government_buffer_wheat_stock_norm"),
        ("wheat_central_pool_exports", "wheat_central_pool_exports"),
    ]:
        base = _attach_indicator_asof(base, indicators, source_key, target_column)

    base["month_start"] = base["date"].dt.to_period("M").dt.to_timestamp()
    base = base.merge(
        benchmarks.rename(columns={"date": "month_start"}),
        on="month_start",
        how="left",
    )
    if not driver_scores.empty:
        base = base.merge(
            driver_scores.rename(columns={"metric_month": "month_start"}),
            on="month_start",
            how="left",
        )
    else:
        for column in [
            "wheat_driver_composite_score",
            "wheat_driver_domestic_score",
            "wheat_driver_weather_score",
            "wheat_driver_global_score",
            "wheat_driver_policy_score",
            "wheat_driver_price_adjustment_pct",
        ]:
            base[column] = pd.NA
    if not trade_features.empty:
        base = base.merge(
            trade_features.rename(columns={"metric_month": "month_start"}),
            on="month_start",
            how="left",
        )
    else:
        for column in [
            "wheat_export_quantity_monthly",
            "wheat_import_quantity_monthly",
            "wheat_export_value_inr_crore_monthly",
            "wheat_import_value_inr_crore_monthly",
            "wheat_export_concentration_hhi",
            "wheat_import_concentration_hhi",
            "wheat_export_seasonality_share_pct",
        ]:
            base[column] = pd.NA
    if not risk_features.empty:
        base = base.merge(
            risk_features.rename(columns={"metric_month": "month_start"}),
            on="month_start",
            how="left",
        )
    else:
        for column in [
            "wheat_risk_price_volatility_score",
            "wheat_risk_weather_climate_score",
            "wheat_risk_geopolitical_black_sea_score",
            "wheat_risk_policy_trade_restriction_score",
            "wheat_risk_supply_stock_tightness_score",
        ]:
            base[column] = pd.NA
    base = base.drop(columns=["month_start"])

    for signal_name, target_column in [
        ("MSP", "msp_inr_quintal"),
        ("Cost of production", "cost_of_production_inr_quintal"),
        ("Margin over cost", "margin_over_cost_percent"),
        ("Actual wheat procurement", "procurement_actual_lmt"),
        ("Estimated wheat procurement", "procurement_estimated_lmt"),
        ("Progressive area sown", "progressive_area_sown_lakh_hectare"),
        ("Final area previous season", "final_area_previous_season_lakh_hectare"),
    ]:
        base = _attach_support_signal_asof(base, support_signals, signal_name, target_column)

    base["created_at"] = datetime.utcnow().isoformat() + "Z"
    return base


def _persist_training_frame(conn: sqlite3.Connection, frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0
    writable = frame.copy()
    if "id" in writable.columns:
        writable = writable.drop(columns=["id"])
    writable["date"] = writable["date"].dt.strftime("%Y-%m-%d")
    conn.execute("DELETE FROM wheat_training_matrix_daily")
    writable.to_sql("wheat_training_matrix_daily", conn, if_exists="append", index=False)
    conn.commit()
    return int(len(writable))


def _export_csv(frame: pd.DataFrame) -> str:
    export = frame.copy()
    if "id" in export.columns:
        export = export.drop(columns=["id"])
    export["date"] = export["date"].dt.strftime("%Y-%m-%d")
    export.to_csv(TRAINING_CSV_PATH, index=False)
    return str(TRAINING_CSV_PATH)


def run() -> dict[str, Any]:
    with _connect() as conn:
        _ensure_schema(conn)
        frame = _build_training_frame(conn)
        written_rows = _persist_training_frame(conn, frame)
        csv_path = _export_csv(frame)

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM wheat_training_matrix_daily")
        count, min_date, max_date = cur.fetchone()
        cur.execute("SELECT COUNT(DISTINCT state) FROM wheat_training_matrix_daily")
        state_count = cur.fetchone()[0]

    return {
        "status": "success",
        "feature_db_path": str(FEATURE_DB_PATH),
        "training_csv_path": csv_path,
        "rows_written": written_rows,
        "date_range": [min_date, max_date],
        "state_count": state_count,
        "feature_columns": list(frame.columns),
        "sample_columns": [
            "state",
            "date",
            "modal_price",
            "arrival_quantity",
            "temperature_2m_mean",
            "wheat_yield_kg_per_hectare",
            "cpi_inflation_rate",
            "policy_repo_rate",
            "government_buffer_wheat_stock",
            "global_wheat_benchmark_avg_usd_mt",
            "msp_inr_quintal",
            "procurement_actual_lmt",
            "wheat_driver_composite_score",
            "wheat_driver_domestic_score",
            "wheat_driver_weather_score",
            "wheat_driver_global_score",
            "wheat_driver_policy_score",
            "wheat_driver_price_adjustment_pct",
            "wheat_export_quantity_monthly",
            "wheat_import_quantity_monthly",
            "wheat_export_concentration_hhi",
            "wheat_export_seasonality_share_pct",
            "wheat_risk_price_volatility_score",
            "wheat_risk_weather_climate_score",
            "wheat_risk_geopolitical_black_sea_score",
            "wheat_risk_policy_trade_restriction_score",
            "wheat_risk_supply_stock_tightness_score",
            "target_next_day_price",
            "target_next_7d_avg_price",
        ],
        "summary": {
            "training_rows": count,
            "training_start": min_date,
            "training_end": max_date,
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
