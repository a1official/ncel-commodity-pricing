from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
from psycopg2.extensions import connection as PgConnection


ROOT = Path(__file__).resolve().parents[3]
MIGRATION_DIR = Path(__file__).resolve().parent
CHECKPOINT_FILE = MIGRATION_DIR / "wheat_rds_migration_checkpoint.json"

SOURCE_DATABASES = {
    "wheat_demand": ROOT / "SnD" / "demand" / "wheat" / "wheat_demand_monthly.db",
    "wheat_supply": ROOT / "SnD" / "supply" / "wheat" / "wheat_supply_factors.db",
    "wheat_price_drivers": ROOT / "SnD" / "price_drivers" / "wheat" / "wheat_price_drivers.db",
    "wheat_scenarios": ROOT / "SnD" / "scenarios" / "wheat" / "wheat_scenarios.db",
    "wheat_output": ROOT / "SnD" / "output" / "wheat" / "wheat_output_structure.db",
    "wheat_model_integration": ROOT / "SnD" / "model_integration" / "wheat" / "wheat_model_integration.db",
}

MIGRATION_SCHEMA = "migration_meta"
RUN_NAME = "wheat_snd_sqlite_to_postgres"


@dataclass
class TableSpec:
    sqlite_path: Path
    schema_name: str
    table_name: str
    columns: list[dict[str, Any]]
    primary_keys: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate Wheat SnD SQLite data to PostgreSQL with retry and resume.")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--database", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--sslmode", default="prefer")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--max-retries", type=int, default=6)
    parser.add_argument("--retry-delay", type=float, default=2.0)
    parser.add_argument("--checkpoint-file", default=str(CHECKPOINT_FILE))
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--skip-validate", action="store_true")
    return parser.parse_args()


def load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"run_name": RUN_NAME, "tables": {}, "updated_at": None}
    return json.loads(path.read_text(encoding="utf-8"))


def save_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def connect_postgres(args: argparse.Namespace) -> PgConnection:
    return psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.database,
        user=args.user,
        password=args.password,
        sslmode=args.sslmode,
        connect_timeout=15,
    )


def with_retry(fn, *, max_retries: int, retry_delay: float, label: str):
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            attempt += 1
            if attempt > max_retries:
                raise RuntimeError(f"{label} failed after {max_retries} retries") from exc
            sleep_for = retry_delay * (2 ** (attempt - 1))
            print(f"[retry] {label} failed on attempt {attempt}: {exc}. Sleeping {sleep_for:.1f}s", file=sys.stderr)
            time.sleep(sleep_for)


def sqlite_tables(sqlite_path: Path) -> list[str]:
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    names = [row[0] for row in cur.fetchall()]
    conn.close()
    return names


def sqlite_table_spec(schema_name: str, sqlite_path: Path, table_name: str) -> TableSpec:
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cols = cur.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    conn.close()
    columns = []
    primary_keys = []
    for row in cols:
        col = {
            "cid": row["cid"],
            "name": row["name"],
            "type": row["type"] or "TEXT",
            "notnull": bool(row["notnull"]),
            "default": row["dflt_value"],
            "pk_order": row["pk"],
        }
        columns.append(col)
        if row["pk"]:
            primary_keys.append((row["pk"], row["name"]))
    primary_keys = [name for _, name in sorted(primary_keys)]
    return TableSpec(
        sqlite_path=sqlite_path,
        schema_name=schema_name,
        table_name=table_name,
        columns=columns,
        primary_keys=primary_keys,
    )


def pg_type(sqlite_type: str) -> str:
    t = sqlite_type.upper()
    if "INT" in t:
        return "BIGINT"
    if any(token in t for token in ("REAL", "FLOA", "DOUB")):
        return "DOUBLE PRECISION"
    if "BLOB" in t:
        return "BYTEA"
    return "TEXT"


def ensure_meta_schema(pg: PgConnection) -> None:
    cur = pg.cursor()
    cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(MIGRATION_SCHEMA)))
    cur.execute(
        sql.SQL(
            """
            CREATE TABLE IF NOT EXISTS {}.migration_runs (
                run_name TEXT PRIMARY KEY,
                started_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                checkpoint_json TEXT
            )
            """
        ).format(sql.Identifier(MIGRATION_SCHEMA))
    )
    cur.execute(
        sql.SQL(
            """
            CREATE TABLE IF NOT EXISTS {}.table_progress (
                run_name TEXT NOT NULL,
                schema_name TEXT NOT NULL,
                table_name TEXT NOT NULL,
                source_rows BIGINT,
                target_rows BIGINT,
                status TEXT,
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (run_name, schema_name, table_name)
            )
            """
        ).format(sql.Identifier(MIGRATION_SCHEMA))
    )
    pg.commit()
    cur.close()


def ensure_target_table(pg: PgConnection, spec: TableSpec) -> None:
    cur = pg.cursor()
    cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(spec.schema_name)))
    col_defs: list[sql.Composable] = []
    for col in spec.columns:
        pieces: list[sql.Composable] = [
            sql.Identifier(col["name"]),
            sql.SQL(pg_type(col["type"])),
        ]
        if col["notnull"]:
            pieces.append(sql.SQL("NOT NULL"))
        col_defs.append(sql.SQL(" ").join(pieces))
    if spec.primary_keys:
        pk_def = sql.SQL("PRIMARY KEY ({})").format(
            sql.SQL(", ").join(sql.Identifier(name) for name in spec.primary_keys)
        )
        col_defs.append(pk_def)
    cur.execute(
        sql.SQL("CREATE TABLE IF NOT EXISTS {}.{} ({})").format(
            sql.Identifier(spec.schema_name),
            sql.Identifier(spec.table_name),
            sql.SQL(", ").join(col_defs),
        )
    )
    pg.commit()
    cur.close()


def source_row_count(spec: TableSpec) -> int:
    conn = sqlite3.connect(spec.sqlite_path)
    cur = conn.cursor()
    cur.execute(f'SELECT COUNT(*) FROM "{spec.table_name}"')
    count = int(cur.fetchone()[0])
    conn.close()
    return count


def target_row_count(pg: PgConnection, spec: TableSpec) -> int:
    cur = pg.cursor()
    cur.execute(
        sql.SQL("SELECT COUNT(*) FROM {}.{}").format(sql.Identifier(spec.schema_name), sql.Identifier(spec.table_name))
    )
    count = int(cur.fetchone()[0])
    cur.close()
    return count


def ordered_select_sql(spec: TableSpec) -> str:
    quoted = f'"{spec.table_name}"'
    if spec.primary_keys:
        order_by = ", ".join(f'"{col}"' for col in spec.primary_keys)
        return f"SELECT * FROM {quoted} ORDER BY {order_by} LIMIT ? OFFSET ?"
    return f"SELECT rowid, * FROM {quoted} ORDER BY rowid LIMIT ? OFFSET ?"


def fetch_batch(spec: TableSpec, batch_size: int, offset: int) -> tuple[list[str], list[tuple[Any, ...]]]:
    conn = sqlite3.connect(spec.sqlite_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    query = ordered_select_sql(spec)
    cur.execute(query, (batch_size, offset))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return [], []
    first_keys = list(rows[0].keys())
    if first_keys[0] == "rowid":
        first_keys = first_keys[1:]
        values = [tuple(row[key] for key in first_keys) for row in rows]
        return first_keys, values
    values = [tuple(row[key] for key in first_keys) for row in rows]
    return first_keys, values


def write_batch(pg: PgConnection, spec: TableSpec, columns: list[str], values: list[tuple[Any, ...]]) -> None:
    cur = pg.cursor()
    insert_sql = sql.SQL("INSERT INTO {}.{} ({}) VALUES %s").format(
        sql.Identifier(spec.schema_name),
        sql.Identifier(spec.table_name),
        sql.SQL(", ").join(sql.Identifier(col) for col in columns),
    )
    if spec.primary_keys:
        insert_sql += sql.SQL(" ON CONFLICT ({}) DO NOTHING").format(
            sql.SQL(", ").join(sql.Identifier(col) for col in spec.primary_keys)
        )
    execute_values(cur, insert_sql.as_string(pg), values, page_size=len(values))
    pg.commit()
    cur.close()


def update_meta_progress(pg: PgConnection, spec: TableSpec, source_rows_total: int, target_rows_total: int, status: str, checkpoint: dict[str, Any]) -> None:
    cur = pg.cursor()
    cur.execute(
        sql.SQL(
            """
            INSERT INTO {}.migration_runs (run_name, checkpoint_json, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (run_name) DO UPDATE
            SET checkpoint_json = EXCLUDED.checkpoint_json,
                updated_at = NOW()
            """
        ).format(sql.Identifier(MIGRATION_SCHEMA)),
        (RUN_NAME, json.dumps(checkpoint)),
    )
    cur.execute(
        sql.SQL(
            """
            INSERT INTO {}.table_progress (run_name, schema_name, table_name, source_rows, target_rows, status, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (run_name, schema_name, table_name) DO UPDATE
            SET source_rows = EXCLUDED.source_rows,
                target_rows = EXCLUDED.target_rows,
                status = EXCLUDED.status,
                updated_at = NOW()
            """
        ).format(sql.Identifier(MIGRATION_SCHEMA)),
        (RUN_NAME, spec.schema_name, spec.table_name, source_rows_total, target_rows_total, status),
    )
    pg.commit()
    cur.close()


def migrate_table(pg_args: argparse.Namespace, spec: TableSpec, checkpoint: dict[str, Any], checkpoint_path: Path) -> None:
    source_total = source_row_count(spec)

    def _run() -> None:
        pg = connect_postgres(pg_args)
        ensure_meta_schema(pg)
        ensure_target_table(pg, spec)
        current_target_rows = target_row_count(pg, spec)
        progress_key = f"{spec.schema_name}.{spec.table_name}"
        table_state = checkpoint["tables"].get(progress_key, {})
        offset = max(int(table_state.get("target_rows", 0)), current_target_rows)
        status = "in_progress"
        checkpoint["tables"][progress_key] = {
            "schema_name": spec.schema_name,
            "table_name": spec.table_name,
            "source_rows": source_total,
            "target_rows": offset,
            "status": status,
        }
        save_checkpoint(checkpoint_path, checkpoint)
        update_meta_progress(pg, spec, source_total, offset, status, checkpoint)

        while offset < source_total:
            columns, values = fetch_batch(spec, pg_args.batch_size, offset)
            if not values:
                break
            write_batch(pg, spec, columns, values)
            offset = target_row_count(pg, spec)
            checkpoint["tables"][progress_key] = {
                "schema_name": spec.schema_name,
                "table_name": spec.table_name,
                "source_rows": source_total,
                "target_rows": offset,
                "status": "in_progress",
            }
            save_checkpoint(checkpoint_path, checkpoint)
            update_meta_progress(pg, spec, source_total, offset, "in_progress", checkpoint)

        checkpoint["tables"][progress_key]["status"] = "completed"
        checkpoint["tables"][progress_key]["target_rows"] = offset
        save_checkpoint(checkpoint_path, checkpoint)
        update_meta_progress(pg, spec, source_total, offset, "completed", checkpoint)
        pg.close()

    with_retry(
        _run,
        max_retries=pg_args.max_retries,
        retry_delay=pg_args.retry_delay,
        label=f"migrate {spec.schema_name}.{spec.table_name}",
    )


def validate_table(pg_args: argparse.Namespace, spec: TableSpec) -> tuple[int, int]:
    source_total = source_row_count(spec)
    pg = connect_postgres(pg_args)
    target_total = target_row_count(pg, spec)
    pg.close()
    return source_total, target_total


def plan() -> list[TableSpec]:
    specs: list[TableSpec] = []
    for schema_name, sqlite_path in SOURCE_DATABASES.items():
        for table_name in sqlite_tables(sqlite_path):
            specs.append(sqlite_table_spec(schema_name, sqlite_path, table_name))
    return specs


def main() -> int:
    args = parse_args()
    checkpoint_path = Path(args.checkpoint_file)
    checkpoint = load_checkpoint(checkpoint_path)
    specs = plan()

    if args.print_plan:
        print("Migration plan:")
        for spec in specs:
            print(f"- {spec.sqlite_path.name} -> {spec.schema_name}.{spec.table_name}")
        print(f"Checkpoint file: {checkpoint_path}")
        return 0

    for spec in specs:
        print(f"[start] {spec.schema_name}.{spec.table_name}")
        migrate_table(args, spec, checkpoint, checkpoint_path)
        print(f"[done] {spec.schema_name}.{spec.table_name}")

    if not args.skip_validate:
        print("\nValidation summary:")
        for spec in specs:
            source_total, target_total = validate_table(args, spec)
            status = "ok" if source_total == target_total else "mismatch"
            print(f"- {spec.schema_name}.{spec.table_name}: source={source_total} target={target_total} status={status}")

    print("\nMigration completed.")
    print(f"Checkpoint file: {checkpoint_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
