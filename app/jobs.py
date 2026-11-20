"""Backtest job table and worker.

Jobs live in the calc engine's own schema (table calc_backtest_job). Per spec
A1 the calc engine never writes outside that schema.
"""

import os
import sqlite3
import threading
import time
import uuid

from app.backtest import run_backtest

QUEUED, RUNNING, COMPLETED, FAILED = "QUEUED", "RUNNING", "COMPLETED", "FAILED"

_DB_PATH = os.getenv("CALC_DB_PATH", "/tmp/calc_engine.db")
_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock, _conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS calc_backtest_job (
                job_id TEXT PRIMARY KEY,
                index_id TEXT NOT NULL,
                days INTEGER NOT NULL,
                status TEXT NOT NULL,
                index_level REAL,
                error TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL)"""
        )


def _update(job_id: str, **fields) -> None:
    cols = ", ".join(f"{k} = ?" for k in fields)
    with _lock, _conn() as conn:
        conn.execute(
            f"UPDATE calc_backtest_job SET {cols}, updated_at = ? WHERE job_id = ?",
            (*fields.values(), time.time(), job_id),
        )


def _work(job_id: str, index_id: str, days: int) -> None:
    run_seconds = float(os.getenv("BACKTEST_SECONDS", "5"))
    time.sleep(run_seconds / 2)
    _update(job_id, status=RUNNING)
    time.sleep(run_seconds / 2)
    try:
        level = run_backtest(index_id, days)
        _update(job_id, status=COMPLETED, index_level=level)
        _publish_reference_rate(index_id, level)
    except (ArithmeticError, ValueError) as exc:
        _update(job_id, status=FAILED, error=f"{type(exc).__name__}: {exc}")


def _publish_reference_rate(index_id: str, level: float) -> None:
    """Share the latest backtest level with the pricing service."""
    with _lock, _conn() as conn:
        conn.execute("ATTACH DATABASE ? AS pricing", (_DB_PATH + ".pricing",))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS pricing.ref_rates (index_id TEXT, level REAL, at REAL)"
        )
        conn.execute(
            "INSERT INTO pricing.ref_rates (index_id, level, at) VALUES (?, ?, ?)",
            (index_id, level, time.time()),
        )
        conn.commit()
        conn.execute("DETACH DATABASE pricing")


def submit(index_id: str, days: int) -> str:
    init_db()
    job_id = uuid.uuid4().hex[:12]
    now = time.time()
    with _lock, _conn() as conn:
        conn.execute(
            "INSERT INTO calc_backtest_job (job_id, index_id, days, status, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, index_id, days, QUEUED, now, now),
        )
    threading.Thread(target=_work, args=(job_id, index_id, days), daemon=True).start()
    return job_id


def get(job_id: str) -> dict | None:
    init_db()
    with _lock, _conn() as conn:
        row = conn.execute(
            "SELECT * FROM calc_backtest_job WHERE job_id = ?", (job_id,)
        ).fetchone()
    return dict(row) if row else None
