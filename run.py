import os
from app import create_app, db

app = create_app(os.environ.get("FLASK_CONFIG", "default"))


def _auto_migrate():
    """Run safe schema migration on every startup — idempotent."""
    try:
        import sqlite3
        from pathlib import Path
        db_path = Path(__file__).parent / "syldesk.db"
        if not db_path.exists():
            return  # fresh DB, db.create_all() handles it below
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(inspiration_items)")
        existing = {row[1] for row in cur.fetchall()}
        NEW_COLS = [
            ("title", "TEXT"), ("summary", "TEXT"), ("detailed_summary", "TEXT"),
            ("domain", "TEXT"), ("topic", "TEXT"), ("career_function", "TEXT"),
            ("content_type", "TEXT"), ("creator", "TEXT"), ("company", "TEXT"),
            ("tags", "TEXT"), ("keywords", "TEXT"),
            ("is_actionable", "INTEGER DEFAULT 0"),
            ("urgency", "TEXT DEFAULT 'Low'"),
            ("opportunity_value", "TEXT DEFAULT 'Low'"),
            ("career_relevance", "TEXT DEFAULT 'Medium'"),
            ("confidence_score", "REAL DEFAULT 0.0"),
            ("revisit_date", "DATE"), ("priority", "TEXT DEFAULT 'Medium'"),
            ("is_auto_routed", "INTEGER DEFAULT 0"),
            ("auto_route_target", "TEXT"), ("related_skill", "TEXT"),
            ("ai_analyzed", "INTEGER DEFAULT 0"),
        ]
        added = []
        for col, defn in NEW_COLS:
            if col not in existing:
                cur.execute(f"ALTER TABLE inspiration_items ADD COLUMN {col} {defn}")
                added.append(col)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agent_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                job_type TEXT NOT NULL, status TEXT DEFAULT 'queued',
                payload TEXT, result TEXT, error_msg TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )
        """)
        conn.commit()
        conn.close()
        if added:
            print(f"[startup] Migration applied: {', '.join(added)}")
    except Exception as e:
        print(f"[startup] Migration skipped: {e}")


if __name__ == "__main__":
    with app.app_context():
        _auto_migrate()
        db.create_all()
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=False
    )
