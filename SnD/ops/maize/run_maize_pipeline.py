from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[3]
OPS_DIR = Path(__file__).resolve().parent
OPS_DB = OPS_DIR / "maize_ops.db"

SUPPLY_BUILD = ROOT / "SnD" / "supply" / "maize" / "build_maize_supply_store.py"
DEMAND_BUILD = ROOT / "SnD" / "demand" / "maize" / "build_maize_demand_store.py"
BALANCE_BUILD = ROOT / "SnD" / "balance" / "maize" / "build_maize_balance_sheet.py"
DRIVER_BUILD = ROOT / "SnD" / "price_drivers" / "maize" / "build_maize_price_drivers.py"
DATA_PLAN_BUILD = ROOT / "SnD" / "data_plan" / "maize" / "build_maize_data_collection_plan.py"
SCENARIO_BUILD = ROOT / "SnD" / "scenarios" / "maize" / "build_maize_scenarios.py"
OUTPUT_BUILD = ROOT / "SnD" / "output" / "maize" / "build_maize_output_structure.py"
MODEL_BUILD = ROOT / "SnD" / "model_integration" / "maize" / "build_maize_model_integration.py"

SUPPLY_DB = ROOT / "SnD" / "supply" / "maize" / "maize_supply_factors.db"
DEMAND_DB = ROOT / "SnD" / "demand" / "maize" / "maize_demand_monthly.db"
BALANCE_DB = ROOT / "SnD" / "balance" / "maize" / "maize_balance_sheet.db"
DRIVER_DB = ROOT / "SnD" / "price_drivers" / "maize" / "maize_price_drivers.db"
SCENARIO_DB = ROOT / "SnD" / "scenarios" / "maize" / "maize_scenarios.db"
OUTPUT_DB = ROOT / "SnD" / "output" / "maize" / "maize_output_structure.db"
MODEL_DB = ROOT / "SnD" / "model_integration" / "maize" / "maize_model_integration.db"


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def connect_ops() -> sqlite3.Connection:
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(OPS_DB)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS maize_job_runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            status TEXT NOT NULL,
            triggered_by TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS maize_job_steps (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            step_name TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER NOT NULL,
            start_time TEXT,
            end_time TEXT,
            error TEXT,
            last_output TEXT,
            UNIQUE(run_id, step_name)
        );

        CREATE TABLE IF NOT EXISTS maize_data_quality_checks (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            check_name TEXT NOT NULL,
            check_scope TEXT NOT NULL,
            result TEXT NOT NULL,
            threshold_value TEXT,
            observed_value TEXT,
            severity TEXT NOT NULL,
            checked_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maize_model_registry (
            model_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            status TEXT NOT NULL,
            val_mae REAL,
            val_rmse REAL,
            artifact_path TEXT,
            metadata_path TEXT,
            promoted_at TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS maize_publish_log (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            publish_time TEXT NOT NULL,
            forecast_month TEXT NOT NULL,
            scenario_count INTEGER NOT NULL,
            published_by TEXT NOT NULL,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS maize_alert_log (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            delivery_status TEXT NOT NULL
        );
        """
    )
    conn.commit()


def log_alert(conn: sqlite3.Connection, run_id: str, alert_type: str, severity: str, message: str) -> None:
    conn.execute(
        """
        INSERT INTO maize_alert_log (id, run_id, alert_type, severity, message, sent_at, delivery_status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (str(uuid.uuid4()), run_id, alert_type, severity, message, now_iso(), "logged"),
    )
    conn.commit()


def run_python_script(script: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    msg = output if output else err
    if proc.returncode != 0:
        return False, msg
    return True, msg


def no_op_ingest() -> tuple[bool, str]:
    return True, "Ingestion placeholder completed. External connectors can be plugged in here."


def run_dq_checks(conn: sqlite3.Connection, run_id: str) -> bool:
    checks: list[tuple[str, str, str, str, str, str, str]] = []
    passed = True

    def add_check(name: str, scope: str, ok: bool, threshold: str, observed: str, severity: str) -> None:
        nonlocal passed
        result = "pass" if ok else "fail"
        if not ok and severity == "critical":
            passed = False
        checks.append((name, scope, result, threshold, observed, severity, now_iso()))

    # Table count checks.
    table_checks = [
        (SUPPLY_DB, "maize_factor_monthly_values", "supply"),
        (DEMAND_DB, "maize_factor_monthly_values", "demand"),
        (BALANCE_DB, "maize_balance_monthly", "balance"),
        (DRIVER_DB, "maize_driver_impact_score", "drivers"),
        (SCENARIO_DB, "maize_scenario_price_range", "scenarios"),
        (OUTPUT_DB, "maize_output_scenario_summary", "output"),
        (MODEL_DB, "maize_forecast_output", "model"),
    ]
    for db_path, table, scope in table_checks:
        with sqlite3.connect(db_path) as c:
            count = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        add_check(
            f"row_count_{table}",
            scope,
            count > 0,
            "> 0 rows",
            str(count),
            "critical",
        )

    # Date coverage check for balance.
    with sqlite3.connect(BALANCE_DB) as c:
        row = c.execute("SELECT MIN(metric_month), MAX(metric_month) FROM maize_balance_monthly").fetchone()
    min_m, max_m = row
    add_check(
        "balance_month_range",
        "balance",
        min_m == "2016-04-01" and max_m == "2026-03-01",
        "2016-04-01..2026-03-01",
        f"{min_m}..{max_m}",
        "critical",
    )

    # Scenario monotonicity check on latest crop year.
    with sqlite3.connect(SCENARIO_DB) as c:
        latest_cy = c.execute("SELECT MAX(crop_year) FROM maize_scenario_price_range").fetchone()[0]
        rows = c.execute(
            "SELECT scenario_key, price_mid FROM maize_scenario_price_range WHERE crop_year=?",
            (latest_cy,),
        ).fetchall()
    mids = {r[0]: float(r[1]) for r in rows}
    mono_ok = (
        "bull_tight_supply" in mids
        and "base_normal" in mids
        and "bear_surplus" in mids
        and mids["bull_tight_supply"] > mids["base_normal"] > mids["bear_surplus"]
    )
    add_check(
        "scenario_ordering",
        "scenarios",
        mono_ok,
        "bull > base > bear",
        str(mids),
        "critical",
    )

    # Forecast scenario count check.
    with sqlite3.connect(MODEL_DB) as c:
        fmonth = c.execute("SELECT MAX(forecast_month) FROM maize_forecast_output").fetchone()[0]
        scount = c.execute(
            "SELECT COUNT(*) FROM maize_forecast_output WHERE forecast_month=?",
            (fmonth,),
        ).fetchone()[0]
    add_check(
        "forecast_scenario_count",
        "model",
        scount == 3,
        "3 scenarios",
        str(scount),
        "critical",
    )

    # Persist checks.
    conn.executemany(
        """
        INSERT INTO maize_data_quality_checks
        (id, run_id, check_name, check_scope, result, threshold_value, observed_value, severity, checked_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                str(uuid.uuid4()),
                run_id,
                c[0],
                c[1],
                c[2],
                c[3],
                c[4],
                c[5],
                c[6],
            )
            for c in checks
        ],
    )
    conn.commit()
    return passed


def publish_latest(conn: sqlite3.Connection, run_id: str, triggered_by: str) -> tuple[bool, str]:
    with sqlite3.connect(MODEL_DB) as c:
        row = c.execute(
            "SELECT forecast_month, COUNT(*) FROM maize_forecast_output GROUP BY forecast_month ORDER BY forecast_month DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return False, "No forecast rows found to publish."
    forecast_month, scenario_count = row[0], int(row[1])
    conn.execute(
        """
        INSERT INTO maize_publish_log (id, run_id, publish_time, forecast_month, scenario_count, published_by, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            run_id,
            now_iso(),
            forecast_month,
            scenario_count,
            triggered_by,
            "Auto-published after DQ pass.",
        ),
    )
    conn.commit()
    return True, f"Published forecast_month={forecast_month}, scenario_count={scenario_count}"


def update_model_registry(conn: sqlite3.Connection, run_id: str) -> None:
    with sqlite3.connect(MODEL_DB) as c:
        c.row_factory = sqlite3.Row
        run = c.execute(
            "SELECT run_id, artifact_path, metadata_path FROM maize_model_runs ORDER BY run_date DESC LIMIT 1"
        ).fetchone()
        metric = c.execute(
            "SELECT mae, rmse FROM maize_model_metrics WHERE split='val' ORDER BY rowid LIMIT 1"
        ).fetchone()
    if run is None:
        return

    # Archive previous active model.
    conn.execute("UPDATE maize_model_registry SET status='archived' WHERE status='active'")
    conn.execute(
        """
        INSERT OR REPLACE INTO maize_model_registry
        (model_id, run_id, status, val_mae, val_rmse, artifact_path, metadata_path, promoted_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(run["run_id"]),
            run_id,
            "active",
            float(metric["mae"]) if metric is not None else None,
            float(metric["rmse"]) if metric is not None else None,
            str(run["artifact_path"]),
            str(run["metadata_path"]),
            now_iso(),
            "Promoted automatically after successful pipeline run.",
        ),
    )
    conn.commit()


@dataclass
class Step:
    name: str
    fn: Callable[[], tuple[bool, str]]


def upsert_step(
    conn: sqlite3.Connection,
    run_id: str,
    step_name: str,
    status: str,
    attempts: int,
    start_time: str | None,
    end_time: str | None,
    error: str | None,
    output: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO maize_job_steps (id, run_id, step_name, status, attempts, start_time, end_time, error, last_output)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id, step_name) DO UPDATE SET
            status=excluded.status,
            attempts=excluded.attempts,
            start_time=excluded.start_time,
            end_time=excluded.end_time,
            error=excluded.error,
            last_output=excluded.last_output
        """,
        (str(uuid.uuid4()), run_id, step_name, status, attempts, start_time, end_time, error, output),
    )
    conn.commit()


def should_skip_completed(conn: sqlite3.Connection, run_id: str, step_name: str) -> bool:
    row = conn.execute(
        "SELECT status FROM maize_job_steps WHERE run_id=? AND step_name=?",
        (run_id, step_name),
    ).fetchone()
    return row is not None and row["status"] == "completed"


def execute_pipeline(run_id: str, triggered_by: str, max_retries: int, resume: bool) -> int:
    conn = connect_ops()
    ensure_schema(conn)

    steps = [
        Step("ingest_sources", no_op_ingest),
        Step("build_supply", lambda: run_python_script(SUPPLY_BUILD)),
        Step("build_demand", lambda: run_python_script(DEMAND_BUILD)),
        Step("build_balance", lambda: run_python_script(BALANCE_BUILD)),
        Step("build_drivers", lambda: run_python_script(DRIVER_BUILD)),
        Step("build_data_plan", lambda: run_python_script(DATA_PLAN_BUILD)),
        Step("build_scenarios", lambda: run_python_script(SCENARIO_BUILD)),
        Step("build_output", lambda: run_python_script(OUTPUT_BUILD)),
        Step("build_model", lambda: run_python_script(MODEL_BUILD)),
    ]

    try:
        for step in steps:
            if resume and should_skip_completed(conn, run_id, step.name):
                continue

            start_t = now_iso()
            upsert_step(conn, run_id, step.name, "running", 0, start_t, None, None, None)

            success = False
            last_msg = ""
            for attempt in range(1, max_retries + 1):
                ok, msg = step.fn()
                last_msg = msg
                if ok:
                    success = True
                    upsert_step(conn, run_id, step.name, "completed", attempt, start_t, now_iso(), None, msg)
                    break
                wait_s = 2 ** (attempt - 1)
                upsert_step(
                    conn,
                    run_id,
                    step.name,
                    "retrying" if attempt < max_retries else "failed",
                    attempt,
                    start_t,
                    now_iso(),
                    msg[:2000],
                    msg[:2000],
                )
                if attempt < max_retries:
                    time.sleep(wait_s)

            if not success:
                conn.execute(
                    "UPDATE maize_job_runs SET ended_at=?, status=?, notes=? WHERE run_id=?",
                    (now_iso(), "failed", f"Step failed: {step.name}", run_id),
                )
                conn.commit()
                log_alert(conn, run_id, "pipeline_failure", "critical", f"Step {step.name} failed after retries. {last_msg[:500]}")
                return 1

        # DQ gate
        dq_ok = run_dq_checks(conn, run_id)
        if not dq_ok:
            conn.execute(
                "UPDATE maize_job_runs SET ended_at=?, status=?, notes=? WHERE run_id=?",
                (now_iso(), "failed_dq", "Critical data quality checks failed.", run_id),
            )
            conn.commit()
            log_alert(conn, run_id, "dq_failure", "critical", "Critical DQ checks failed. Publish blocked.")
            return 2

        # Publish + registry.
        ok, msg = publish_latest(conn, run_id, triggered_by)
        if not ok:
            conn.execute(
                "UPDATE maize_job_runs SET ended_at=?, status=?, notes=? WHERE run_id=?",
                (now_iso(), "failed_publish", msg, run_id),
            )
            conn.commit()
            log_alert(conn, run_id, "publish_failure", "critical", msg)
            return 3

        update_model_registry(conn, run_id)
        conn.execute(
            "UPDATE maize_job_runs SET ended_at=?, status=?, notes=? WHERE run_id=?",
            (now_iso(), "completed", msg, run_id),
        )
        conn.commit()
        return 0
    finally:
        conn.close()


def init_or_resume_run(resume_run_id: str | None, triggered_by: str) -> str:
    conn = connect_ops()
    ensure_schema(conn)
    if resume_run_id:
        row = conn.execute("SELECT run_id, status FROM maize_job_runs WHERE run_id=?", (resume_run_id,)).fetchone()
        if row is None:
            conn.close()
            raise ValueError(f"Run id not found: {resume_run_id}")
        conn.close()
        return str(resume_run_id)

    run_id = f"maize-ops-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    conn.execute(
        "INSERT INTO maize_job_runs (run_id, started_at, ended_at, status, triggered_by, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, now_iso(), None, "running", triggered_by, "Pipeline started"),
    )
    conn.commit()
    conn.close()
    return run_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Maize operational pipeline with retry and checkpoint support.")
    parser.add_argument("--resume-run-id", default=None, help="Resume an existing run id from the last failed/pending step.")
    parser.add_argument("--max-retries", type=int, default=3, help="Retries per step (default: 3).")
    parser.add_argument("--triggered-by", default="manual", help="Actor/source for this run.")
    args = parser.parse_args()

    run_id = init_or_resume_run(args.resume_run_id, args.triggered_by)
    code = execute_pipeline(run_id, args.triggered_by, max_retries=max(1, args.max_retries), resume=bool(args.resume_run_id))
    print(f"run_id={run_id} exit_code={code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
