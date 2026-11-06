"""SQLite persistence for InvoiceIQ runs and human-review audit trail."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "invoiceiq.db"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            filename TEXT,
            invoice_number TEXT,
            vendor_name TEXT,
            po_number TEXT,
            total_amount REAL,
            currency TEXT,
            status TEXT NOT NULL,
            reasons_json TEXT NOT NULL,
            checks_json TEXT NOT NULL,
            document_hash TEXT NOT NULL,
            stages_json TEXT NOT NULL DEFAULT '[]',
            duration_ms REAL,
            review_status TEXT NOT NULL DEFAULT 'NOT REVIEWED',
            reviewer TEXT,
            review_note TEXT,
            reviewed_at TEXT
        )""")
        # Safe, idempotent migration for databases created by earlier versions.
        existing = {row[1] for row in conn.execute("PRAGMA table_info(runs)")}
        additions = {
            "stages_json": "TEXT NOT NULL DEFAULT '[]'",
            "duration_ms": "REAL",
            "review_status": "TEXT NOT NULL DEFAULT 'NOT REVIEWED'",
            "reviewer": "TEXT",
            "review_note": "TEXT",
            "reviewed_at": "TEXT",
        }
        for name, definition in additions.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE runs ADD COLUMN {name} {definition}")


def prior_hashes():
    with connect() as conn:
        return {row[0] for row in conn.execute("SELECT document_hash FROM runs")}


def save_run(result: dict, filename: str = "pasted_invoice.txt") -> int:
    f = result["fields"]
    with connect() as conn:
        cur = conn.execute("""INSERT INTO runs
        (created_at, filename, invoice_number, vendor_name, po_number, total_amount,
         currency, status, reasons_json, checks_json, document_hash, stages_json, duration_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            datetime.now(timezone.utc).isoformat(timespec="seconds"), filename,
            f.get("invoice_number"), f.get("vendor_name"), f.get("po_number"),
            f.get("total_amount"), f.get("currency", "USD"), result["status"],
            json.dumps(result["reasons"]), json.dumps(result["checks"]),
            result["document_hash"], json.dumps(result.get("stages", [])),
            result.get("duration_ms")
        ))
        return int(cur.lastrowid)


def record_review(run_id: int, reviewer: str, decision: str, note: str):
    if decision not in {"HUMAN APPROVED", "HUMAN REJECTED"}:
        raise ValueError("Unsupported human review decision.")
    with connect() as conn:
        conn.execute("""UPDATE runs SET review_status=?, reviewer=?, review_note=?, reviewed_at=?
                        WHERE id=?""", (
            decision, reviewer.strip(), note.strip(),
            datetime.now(timezone.utc).isoformat(timespec="seconds"), run_id
        ))


def get_runs(limit: int = 500):
    with connect() as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_run(run_id: int):
    with connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    return dict(row) if row else None
