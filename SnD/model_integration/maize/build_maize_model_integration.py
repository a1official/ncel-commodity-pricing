from __future__ import annotations

import json
import math
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUTPUT_DIR / 'models'
OUTPUT_DB = OUTPUT_DIR / 'maize_model_integration.db'
MODEL_PATH = MODEL_DIR / 'maize_price_model.joblib'
MODEL_META_PATH = MODEL_DIR / 'maize_price_model_metadata.json'

BALANCE_DB = ROOT / 'SnD' / 'balance' / 'maize' / 'maize_balance_sheet.db'
DEMAND_DB = ROOT / 'SnD' / 'demand' / 'maize' / 'maize_demand_monthly.db'
DRIVER_DB = ROOT / 'SnD' / 'price_drivers' / 'maize' / 'maize_price_drivers.db'
SCENARIO_DB = ROOT / 'SnD' / 'scenarios' / 'maize' / 'maize_scenarios.db'
OUTPUT_STRUCTURE_DB = ROOT / 'SnD' / 'output' / 'maize' / 'maize_output_structure.db'
UPDATED_AT = datetime.now(UTC).isoformat().replace('+00:00', 'Z')

TRAIN_END = '2022-12-01'
VAL_END = '2024-12-01'


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS maize_model_runs (
            run_id TEXT PRIMARY KEY,
            run_date TEXT NOT NULL,
            model_name TEXT NOT NULL,
            horizon TEXT NOT NULL,
            train_from TEXT NOT NULL,
            train_to TEXT NOT NULL,
            val_from TEXT NOT NULL,
            val_to TEXT NOT NULL,
            test_from TEXT NOT NULL,
            test_to TEXT NOT NULL,
            status TEXT NOT NULL,
            feature_count INTEGER NOT NULL,
            artifact_path TEXT NOT NULL,
            metadata_path TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_model_metrics (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            split TEXT NOT NULL,
            mae REAL NOT NULL,
            rmse REAL NOT NULL,
            mape REAL NOT NULL,
            directional_accuracy REAL NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_feature_importance (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            feature_name TEXT NOT NULL,
            importance REAL NOT NULL,
            rank_no INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_predictions_monthly (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            metric_month TEXT NOT NULL,
            split TEXT NOT NULL,
            current_value REAL NOT NULL,
            actual_next_value REAL,
            predicted_next_value REAL,
            error REAL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_forecast_output (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            forecast_month TEXT NOT NULL,
            scenario_key TEXT NOT NULL,
            forecast_price_index REAL NOT NULL,
            low REAL NOT NULL,
            high REAL NOT NULL,
            confidence TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def reset(conn: sqlite3.Connection) -> None:
    for t in [
        'maize_model_runs',
        'maize_model_metrics',
        'maize_feature_importance',
        'maize_predictions_monthly',
        'maize_forecast_output',
    ]:
        conn.execute(f'DELETE FROM {t}')
    conn.commit()


def month_next(month_iso: str) -> str:
    y = int(month_iso[:4])
    m = int(month_iso[5:7])
    if m == 12:
        return f'{y + 1}-01-01'
    return f'{y:04d}-{m + 1:02d}-01'


def directional_accuracy(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    pred_change = np.sign(df['predicted_next_value'] - df['current_value'])
    actual_change = np.sign(df['actual_next_value'] - df['current_value'])
    return float((pred_change == actual_change).mean() * 100.0)


def mape_safe(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = np.abs(y_true) > 1e-9
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)


def load_factor_map(conn: sqlite3.Connection, factor_key: str) -> dict[str, float]:
    rows = conn.execute(
        "SELECT metric_month, value FROM maize_factor_monthly_values WHERE factor_key=? ORDER BY metric_month",
        (factor_key,),
    ).fetchall()
    return {str(r['metric_month']): float(r['value'] or 0.0) for r in rows}


def build_feature_frame() -> pd.DataFrame:
    with connect(OUTPUT_STRUCTURE_DB) as conn:
        base_rows = conn.execute(
            """
            SELECT metric_month, crop_year, opening_stock, production, imports,
                   total_availability, total_demand, delta, ending_stock_sim,
                   domestic_price_index, global_price_proxy_index,
                   rolling_corr_3m, rolling_corr_6m
            FROM maize_output_balance_sheet b
            JOIN maize_output_price_correlation c USING(metric_month)
            ORDER BY metric_month
            """
        ).fetchall()

    with connect(DRIVER_DB) as conn:
        drows = conn.execute(
            """
            SELECT metric_month, composite_score, domestic_score, global_score,
                   weather_score, policy_score, market_score
            FROM maize_driver_impact_score
            ORDER BY metric_month
            """
        ).fetchall()
    driver_map = {str(r['metric_month']): dict(r) for r in drows}

    with connect(DEMAND_DB) as conn:
        poultry = load_factor_map(conn, 'poultry_demand_cycle')
        ethanol = load_factor_map(conn, 'ethanol_demand_signal')
        substitution = load_factor_map(conn, 'substitution_effect')
        retail = load_factor_map(conn, 'retail_price_pressure')

    rows: list[dict] = []
    for r in base_rows:
        m = str(r['metric_month'])
        d = datetime.strptime(m, '%Y-%m-%d')
        drv = driver_map.get(m, {})
        rows.append(
            {
                'metric_month': m,
                'crop_year': r['crop_year'],
                'opening_stock': float(r['opening_stock'] or 0.0),
                'production': float(r['production'] or 0.0),
                'imports': float(r['imports'] or 0.0),
                'total_availability': float(r['total_availability'] or 0.0),
                'total_demand': float(r['total_demand'] or 0.0),
                'delta': float(r['delta'] or 0.0),
                'ending_stock_sim': float(r['ending_stock_sim'] or 0.0),
                'domestic_price_index': float(r['domestic_price_index'] or 0.0),
                'global_price_proxy_index': float(r['global_price_proxy_index'] or 0.0),
                'rolling_corr_3m': float(r['rolling_corr_3m'] or 0.0),
                'rolling_corr_6m': float(r['rolling_corr_6m'] or 0.0),
                'driver_composite': float(drv.get('composite_score', 50.0)),
                'driver_domestic': float(drv.get('domestic_score', 50.0)),
                'driver_global': float(drv.get('global_score', 50.0)),
                'driver_weather': float(drv.get('weather_score', 50.0)),
                'driver_policy': float(drv.get('policy_score', 50.0)),
                'driver_market': float(drv.get('market_score', 50.0)),
                'poultry_demand_cycle': float(poultry.get(m, 100.0)),
                'ethanol_signal': float(ethanol.get(m, 0.0)),
                'substitution_effect': float(substitution.get(m, 100.0)),
                'retail_price_pressure': float(retail.get(m, 100.0)),
                'month_num': float(d.month),
                'month_sin': float(math.sin(2.0 * math.pi * d.month / 12.0)),
                'month_cos': float(math.cos(2.0 * math.pi * d.month / 12.0)),
            }
        )

    df = pd.DataFrame(rows).sort_values('metric_month').reset_index(drop=True)

    # lag features (known at t)
    df['price_lag_1'] = df['domestic_price_index'].shift(1)
    df['price_lag_3'] = df['domestic_price_index'].shift(3)
    df['price_lag_6'] = df['domestic_price_index'].shift(6)
    df['delta_lag_1'] = df['delta'].shift(1)

    # target: next-month domestic price index
    df['target_next_1m'] = df['domestic_price_index'].shift(-1)

    df = df.dropna().reset_index(drop=True)
    return df


def split_name(metric_month: str) -> str:
    if metric_month <= TRAIN_END:
        return 'train'
    if metric_month <= VAL_END:
        return 'val'
    return 'test'


def build_and_train() -> dict:
    df = build_feature_frame()

    feature_cols = [
        'opening_stock', 'production', 'imports', 'total_availability', 'total_demand', 'delta', 'ending_stock_sim',
        'global_price_proxy_index', 'rolling_corr_3m', 'rolling_corr_6m',
        'driver_composite', 'driver_domestic', 'driver_global', 'driver_weather', 'driver_policy', 'driver_market',
        'poultry_demand_cycle', 'ethanol_signal', 'substitution_effect', 'retail_price_pressure',
        'month_num', 'month_sin', 'month_cos', 'price_lag_1', 'price_lag_3', 'price_lag_6', 'delta_lag_1',
    ]

    df['split'] = df['metric_month'].map(split_name)

    train_df = df[df['split'] == 'train'].copy()
    val_df = df[df['split'] == 'val'].copy()
    test_df = df[df['split'] == 'test'].copy()

    X_train = train_df[feature_cols].to_numpy()
    y_train = train_df['target_next_1m'].to_numpy()

    X_val = val_df[feature_cols].to_numpy()
    y_val = val_df['target_next_1m'].to_numpy()

    X_test = test_df[feature_cols].to_numpy()
    y_test = test_df['target_next_1m'].to_numpy()

    models = {
        'linear': Pipeline([('scaler', StandardScaler()), ('model', LinearRegression())]),
        'ridge': Pipeline([('scaler', StandardScaler()), ('model', Ridge(alpha=1.0, random_state=42))]),
        'rf': RandomForestRegressor(n_estimators=400, random_state=42, min_samples_leaf=2),
    }

    model_results: dict[str, dict] = {}
    for name, model in models.items():
        model.fit(X_train, y_train)

        pred_train = model.predict(X_train)
        pred_val = model.predict(X_val)
        pred_test = model.predict(X_test)

        res = {
            'model': model,
            'train': {
                'mae': float(mean_absolute_error(y_train, pred_train)),
                'rmse': float(math.sqrt(mean_squared_error(y_train, pred_train))),
                'mape': mape_safe(y_train, pred_train),
            },
            'val': {
                'mae': float(mean_absolute_error(y_val, pred_val)),
                'rmse': float(math.sqrt(mean_squared_error(y_val, pred_val))),
                'mape': mape_safe(y_val, pred_val),
            },
            'test': {
                'mae': float(mean_absolute_error(y_test, pred_test)) if len(y_test) else 0.0,
                'rmse': float(math.sqrt(mean_squared_error(y_test, pred_test))) if len(y_test) else 0.0,
                'mape': mape_safe(y_test, pred_test) if len(y_test) else 0.0,
            },
            'pred_train': pred_train,
            'pred_val': pred_val,
            'pred_test': pred_test,
        }

        # directional accuracy by split
        for split_name_local, split_df, preds in [
            ('train', train_df, pred_train),
            ('val', val_df, pred_val),
            ('test', test_df, pred_test),
        ]:
            tmp = split_df[['metric_month', 'domestic_price_index', 'target_next_1m']].copy()
            tmp['predicted_next_value'] = preds
            tmp = tmp.rename(columns={'domestic_price_index': 'current_value', 'target_next_1m': 'actual_next_value'})
            res[split_name_local]['directional_accuracy'] = directional_accuracy(tmp)

        model_results[name] = res

    # champion by validation MAE then RMSE
    ranked = sorted(model_results.items(), key=lambda kv: (kv[1]['val']['mae'], kv[1]['val']['rmse']))
    champion_name, champion = ranked[0]

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(champion['model'], MODEL_PATH)

    meta = {
        'run_at': UPDATED_AT,
        'champion_model': champion_name,
        'feature_columns': feature_cols,
        'train_range': [train_df['metric_month'].min(), train_df['metric_month'].max()],
        'val_range': [val_df['metric_month'].min(), val_df['metric_month'].max()],
        'test_range': [test_df['metric_month'].min(), test_df['metric_month'].max()],
        'metrics': {
            name: {
                'train': vals['train'],
                'val': vals['val'],
                'test': vals['test'],
            }
            for name, vals in model_results.items()
        },
    }
    MODEL_META_PATH.write_text(json.dumps(meta, indent=2), encoding='utf-8')

    return {
        'df': df,
        'train_df': train_df,
        'val_df': val_df,
        'test_df': test_df,
        'feature_cols': feature_cols,
        'model_results': model_results,
        'champion_name': champion_name,
        'champion_model': champion['model'],
    }


def scenario_multipliers() -> dict[str, tuple[float, float, float]]:
    with connect(SCENARIO_DB) as conn:
        latest_cy = conn.execute("SELECT MAX(crop_year) FROM maize_scenario_price_range").fetchone()[0]
        rows = conn.execute(
            "SELECT scenario_key, price_low, price_mid, price_high FROM maize_scenario_price_range WHERE crop_year=?",
            (latest_cy,),
        ).fetchall()
    base = next((r for r in rows if r['scenario_key'] == 'base_normal'), None)
    if base is None:
        return {'base_normal': (1.0, 1.0, 1.0)}
    bmid = float(base['price_mid']) if float(base['price_mid']) != 0 else 1.0
    mult = {}
    for r in rows:
        mult[str(r['scenario_key'])] = (
            float(r['price_low']) / bmid,
            float(r['price_mid']) / bmid,
            float(r['price_high']) / bmid,
        )
    return mult


def build_db() -> dict:
    result = build_and_train()
    df = result['df']
    feature_cols = result['feature_cols']
    model_results = result['model_results']
    champion_name = result['champion_name']
    champion_model = result['champion_model']

    run_id = f"maize-run-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

    # feature importance
    if hasattr(champion_model, 'named_steps') and 'model' in champion_model.named_steps:
        core = champion_model.named_steps['model']
    else:
        core = champion_model

    if hasattr(core, 'feature_importances_'):
        importances = np.asarray(core.feature_importances_, dtype=float)
    elif hasattr(core, 'coef_'):
        coef = np.asarray(core.coef_, dtype=float)
        importances = np.abs(coef)
    else:
        importances = np.zeros(len(feature_cols), dtype=float)

    # predictions table
    pred_rows = []
    metrics_rows = []
    imp_rows = []

    for model_name, vals in model_results.items():
        for split in ['train', 'val', 'test']:
            m = vals[split]
            metrics_rows.append(
                (
                    str(uuid.uuid4()),
                    run_id,
                    model_name,
                    split,
                    round(m['mae'], 6),
                    round(m['rmse'], 6),
                    round(m['mape'], 6),
                    round(m['directional_accuracy'], 6),
                    UPDATED_AT,
                )
            )

    # champion predictions only for storage
    pred_all = champion_model.predict(df[feature_cols].to_numpy())
    for i, row in df.reset_index(drop=True).iterrows():
        pred = float(pred_all[i])
        actual = float(row['target_next_1m'])
        curr = float(row['domestic_price_index'])
        pred_rows.append(
            (
                str(uuid.uuid4()),
                run_id,
                champion_name,
                str(row['metric_month']),
                str(row['split']),
                round(curr, 6),
                round(actual, 6),
                round(pred, 6),
                round(pred - actual, 6),
                UPDATED_AT,
            )
        )

    ordered = sorted(zip(feature_cols, importances.tolist()), key=lambda x: x[1], reverse=True)
    for rank, (fname, imp) in enumerate(ordered, start=1):
        imp_rows.append(
            (
                str(uuid.uuid4()),
                run_id,
                champion_name,
                fname,
                round(float(imp), 10),
                rank,
                UPDATED_AT,
            )
        )

    # forecast output for next month under scenarios
    latest = df.iloc[-1].copy()
    x_latest = latest[feature_cols].to_numpy().reshape(1, -1)
    base_next = float(champion_model.predict(x_latest)[0])
    forecast_month = month_next(str(latest['metric_month']))
    mult = scenario_multipliers()

    forecast_rows = []
    for skey, (mlow, mmid, mhigh) in mult.items():
        forecast_rows.append(
            (
                str(uuid.uuid4()),
                run_id,
                forecast_month,
                skey,
                round(base_next * mmid, 6),
                round(base_next * mlow, 6),
                round(base_next * mhigh, 6),
                'medium',
                UPDATED_AT,
            )
        )

    with connect(OUTPUT_DB) as conn:
        ensure_schema(conn)
        reset(conn)

        train_from = str(df[df['split'] == 'train']['metric_month'].min())
        train_to = str(df[df['split'] == 'train']['metric_month'].max())
        val_from = str(df[df['split'] == 'val']['metric_month'].min())
        val_to = str(df[df['split'] == 'val']['metric_month'].max())
        test_from = str(df[df['split'] == 'test']['metric_month'].min())
        test_to = str(df[df['split'] == 'test']['metric_month'].max())

        conn.execute(
            """
            INSERT INTO maize_model_runs
            (run_id, run_date, model_name, horizon, train_from, train_to, val_from, val_to, test_from, test_to, status, feature_count, artifact_path, metadata_path, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                UPDATED_AT,
                champion_name,
                '1m',
                train_from,
                train_to,
                val_from,
                val_to,
                test_from,
                test_to,
                'completed',
                len(feature_cols),
                str(MODEL_PATH),
                str(MODEL_META_PATH),
                'Champion selected by validation MAE; scenarios mapped via Step 7 multipliers.',
                UPDATED_AT,
            ),
        )

        conn.executemany(
            """
            INSERT INTO maize_model_metrics
            (id, run_id, model_name, split, mae, rmse, mape, directional_accuracy, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            metrics_rows,
        )
        conn.executemany(
            """
            INSERT INTO maize_feature_importance
            (id, run_id, model_name, feature_name, importance, rank_no, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            imp_rows,
        )
        conn.executemany(
            """
            INSERT INTO maize_predictions_monthly
            (id, run_id, model_name, metric_month, split, current_value, actual_next_value, predicted_next_value, error, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            pred_rows,
        )
        conn.executemany(
            """
            INSERT INTO maize_forecast_output
            (id, run_id, forecast_month, scenario_key, forecast_price_index, low, high, confidence, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            forecast_rows,
        )
        conn.commit()

        counts = {
            'maize_model_runs': conn.execute('SELECT COUNT(*) FROM maize_model_runs').fetchone()[0],
            'maize_model_metrics': conn.execute('SELECT COUNT(*) FROM maize_model_metrics').fetchone()[0],
            'maize_feature_importance': conn.execute('SELECT COUNT(*) FROM maize_feature_importance').fetchone()[0],
            'maize_predictions_monthly': conn.execute('SELECT COUNT(*) FROM maize_predictions_monthly').fetchone()[0],
            'maize_forecast_output': conn.execute('SELECT COUNT(*) FROM maize_forecast_output').fetchone()[0],
        }

    return {
        'run_id': run_id,
        'champion_model': champion_name,
        'counts': counts,
        'artifacts': {
            'model_path': str(MODEL_PATH),
            'metadata_path': str(MODEL_META_PATH),
        },
    }


if __name__ == '__main__':
    print(json.dumps(build_db(), indent=2))
