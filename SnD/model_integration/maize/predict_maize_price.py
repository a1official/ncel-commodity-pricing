from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB = ROOT / 'SnD' / 'model_integration' / 'maize' / 'maize_model_integration.db'


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    run = conn.execute('SELECT run_id, model_name, run_date FROM maize_model_runs ORDER BY run_date DESC LIMIT 1').fetchone()
    if run is None:
        print('No model run found.')
        return

    print({'run_id': run['run_id'], 'model_name': run['model_name'], 'run_date': run['run_date']})
    rows = conn.execute(
        """
        SELECT forecast_month, scenario_key, forecast_price_index, low, high, confidence
        FROM maize_forecast_output
        WHERE run_id=?
        ORDER BY scenario_key
        """,
        (run['run_id'],),
    ).fetchall()
    for row in rows:
        print(dict(row))
    conn.close()


if __name__ == '__main__':
    main()
