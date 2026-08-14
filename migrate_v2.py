"""
migrate_v2.py — Syldesk v1 → v2 schema migration
===================================================
Adds new columns to inspiration_items and creates agent_jobs table.
Safe to run multiple times (checks column existence before adding).

Usage:
    python migrate_v2.py
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "syldesk.db"


NEW_INSPIRATION_COLS = [
    ("title",             "TEXT"),
    ("summary",           "TEXT"),
    ("detailed_summary",  "TEXT"),
    ("domain",            "TEXT"),
    ("topic",             "TEXT"),
    ("career_function",   "TEXT"),
    ("content_type",      "TEXT"),
    ("creator",           "TEXT"),
    ("company",           "TEXT"),
    ("tags",              "TEXT"),
    ("keywords",          "TEXT"),
    ("is_actionable",     "INTEGER DEFAULT 0"),
    ("urgency",           "TEXT DEFAULT 'Low'"),
    ("opportunity_value", "TEXT DEFAULT 'Low'"),
    ("career_relevance",  "TEXT DEFAULT 'Medium'"),
    ("confidence_score",  "REAL DEFAULT 0.0"),
    ("revisit_date",      "DATE"),
    ("priority",          "TEXT DEFAULT 'Medium'"),
    ("is_auto_routed",    "INTEGER DEFAULT 0"),
    ("auto_route_target", "TEXT"),
    ("related_skill",     "TEXT"),
    ("ai_analyzed",       "INTEGER DEFAULT 0"),
]


def migrate():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Run the app first to create it.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── 1. Add new columns to inspiration_items ──────────────────────────
    cur.execute("PRAGMA table_info(inspiration_items)")
    existing = {row[1] for row in cur.fetchall()}

    added = []
    for col_name, col_def in NEW_INSPIRATION_COLS:
        if col_name not in existing:
            sql = f"ALTER TABLE inspiration_items ADD COLUMN {col_name} {col_def}"
            cur.execute(sql)
            added.append(col_name)

    if added:
        print(f"Added columns to inspiration_items: {', '.join(added)}")
    else:
        print("inspiration_items — all columns already present, nothing to add.")

    # ── 2. Create agent_jobs table ────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_jobs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL REFERENCES users(id),
            job_type     TEXT NOT NULL,
            status       TEXT DEFAULT 'queued',
            payload      TEXT,
            result       TEXT,
            error_msg    TEXT,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        )
    """)
    print("agent_jobs table — ensured.")

    conn.commit()
    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    migrate()
