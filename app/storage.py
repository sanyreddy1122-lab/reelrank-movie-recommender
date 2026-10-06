"""Durable local feedback storage; SQLite can be swapped for a managed DB later."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "feedback.sqlite3"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def initialize() -> None:
    with connect() as db:
        schema = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='feedback'").fetchone()
        if schema and "unwatchlist" not in schema[0]:
            # Rebuild the small event table to extend its action constraint while preserving history.
            db.execute("DROP INDEX IF EXISTS idx_feedback_user_movie")
            db.execute("ALTER TABLE feedback RENAME TO feedback_legacy")
            db.execute("""CREATE TABLE feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                movie_id INTEGER NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('like','dislike','watchlist','unlike','unwatchlist')),
                created_at TEXT NOT NULL
            )""")
            db.execute("INSERT INTO feedback(id,user_id,movie_id,action,created_at) SELECT id,user_id,movie_id,action,created_at FROM feedback_legacy")
            db.execute("DROP TABLE feedback_legacy")
        db.execute("""CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            movie_id INTEGER NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('like','dislike','watchlist','unlike','unwatchlist')),
            created_at TEXT NOT NULL
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user_movie ON feedback(user_id, movie_id, id)")


def record_feedback(user_id: str, movie_id: int, action: str) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO feedback(user_id,movie_id,action,created_at) VALUES(?,?,?,?)",
            (user_id, movie_id, action, datetime.now(timezone.utc).isoformat()),
        )


def preferences(user_id: str) -> dict:
    with connect() as db:
        rows = db.execute("""
            SELECT f.movie_id, f.action, f.created_at
            FROM feedback f
            JOIN (SELECT movie_id, MAX(id) AS latest_id FROM feedback WHERE user_id=? GROUP BY movie_id) latest
              ON f.id=latest.latest_id
            WHERE f.user_id=? ORDER BY f.id DESC
        """, (user_id, user_id)).fetchall()
    latest = [dict(row) for row in rows]
    return {
        "user_id": user_id,
        "liked": [row["movie_id"] for row in latest if row["action"] == "like"],
        "disliked": [row["movie_id"] for row in latest if row["action"] == "dislike"],
        "watchlist": [row["movie_id"] for row in latest if row["action"] == "watchlist"],
        "recent_feedback": latest[:20],
    }


def feedback_summary() -> dict:
    with connect() as db:
        total = db.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        users = db.execute("SELECT COUNT(DISTINCT user_id) FROM feedback").fetchone()[0]
        actions = {row["action"]: row["count"] for row in db.execute(
            "SELECT action, COUNT(*) AS count FROM feedback GROUP BY action"
        )}
    return {"total_events": total, "users": users, "actions": actions}
