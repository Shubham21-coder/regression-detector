"""SQLite storage for evaluation runs and per-case results."""

import sqlite3
import json
import uuid
from datetime import datetime, timezone


def init_db(db_path: str = "storage/runs.db"):
    """Create tables if they don't exist."""
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            version_id TEXT,
            timestamp TEXT,
            scores_json TEXT,
            is_baseline INTEGER DEFAULT 0
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            run_id TEXT,
            case_id INTEGER,
            result_json TEXT
        )
    """)
    con.commit()
    con.close()


def save_run(run_id, version_id, scores, results, db_path="storage/runs.db"):
    """Save a complete evaluation run (scores + per-case results)."""
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT INTO runs VALUES (?,?,?,?,?)",
        (run_id, version_id, scores["run_timestamp"], json.dumps(scores), 0),
    )
    for r in results:
        con.execute(
            "INSERT INTO cases VALUES (?,?,?)",
            (run_id, r["id"], json.dumps(r)),
        )
    con.commit()
    con.close()


def get_baseline(db_path="storage/runs.db"):
    """Get baseline run scores and results. Returns (scores_dict, results_list) or (None, None)."""
    con = sqlite3.connect(db_path)
    row = con.execute(
        "SELECT run_id, scores_json FROM runs WHERE is_baseline=1 ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    if not row:
        # No baseline set — use most recent run
        row = con.execute(
            "SELECT run_id, scores_json FROM runs ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
    if not row:
        con.close()
        return None, None
    run_id, scores_json = row
    cases = con.execute(
        "SELECT result_json FROM cases WHERE run_id=?", (run_id,)
    ).fetchall()
    con.close()
    return json.loads(scores_json), [json.loads(c[0]) for c in cases]


def mark_as_baseline(run_id, db_path="storage/runs.db"):
    """Mark a specific run as the baseline (clears previous baseline)."""
    con = sqlite3.connect(db_path)
    con.execute("UPDATE runs SET is_baseline=0")
    con.execute("UPDATE runs SET is_baseline=1 WHERE run_id=?", (run_id,))
    con.commit()
    con.close()


def get_run_history(db_path="storage/runs.db", limit=10):
    """Get recent run history for reporting."""
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT run_id, version_id, timestamp, scores_json, is_baseline "
        "FROM runs ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    con.close()
    return [
        {
            "run_id": r[0],
            "version_id": r[1],
            "timestamp": r[2],
            "overall_accuracy": json.loads(r[3])["overall_accuracy"],
            "is_baseline": bool(r[4]),
        }
        for r in rows
    ]
