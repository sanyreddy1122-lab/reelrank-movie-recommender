"""Durable local feedback storage; SQLite can be swapped for a managed DB later."""
import base64
import hashlib
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(os.environ.get("REELRANK_DATA_DIR", Path(__file__).resolve().parents[1] / "data")).expanduser()
DB_PATH = DATA_DIR / "feedback.sqlite3"
SESSION_SECRET_PATH = DATA_DIR / "session.key"
PASSWORD_ITERATIONS = 310_000


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
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")


def session_secret() -> bytes:
    """Get a stable local signing key; deployments can supply a shared env secret."""
    configured = os.environ.get("REELRANK_SECRET_KEY")
    if configured:
        return configured.encode("utf-8")
    SESSION_SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with SESSION_SECRET_PATH.open("xb") as secret_file:
            secret_file.write(secrets.token_bytes(32))
    except FileExistsError:
        pass
    return SESSION_SECRET_PATH.read_bytes()


def _password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)


def create_user(display_name: str, email: str, password: str) -> dict | None:
    user_id = str(uuid.uuid4())
    salt = secrets.token_bytes(16)
    digest = _password_hash(password, salt)
    encoded = f"pbkdf2_sha256${PASSWORD_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"
    with connect() as db:
        try:
            db.execute(
                "INSERT INTO users(id,email,display_name,password_hash,created_at) VALUES(?,?,?,?,?)",
                (user_id, email.strip().lower(), display_name.strip(), encoded, datetime.now(timezone.utc).isoformat()),
            )
        except sqlite3.IntegrityError:
            return None
    return get_user_by_id(user_id)


def ensure_demo_account(email: str, password: str) -> None:
    """Create or refresh the intentionally shared demo login for app demonstrations."""
    normalized_email = email.strip().lower()
    salt = secrets.token_bytes(16)
    digest = _password_hash(password, salt)
    encoded = f"pbkdf2_sha256${PASSWORD_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"
    with connect() as db:
        existing = db.execute("SELECT id FROM users WHERE email=? COLLATE NOCASE", (normalized_email,)).fetchone()
        if existing:
            db.execute(
                "UPDATE users SET display_name=?, password_hash=? WHERE id=?",
                ("ReelRank Demo", encoded, existing["id"]),
            )
        else:
            db.execute(
                "INSERT INTO users(id,email,display_name,password_hash,created_at) VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()), normalized_email, "ReelRank Demo", encoded, datetime.now(timezone.utc).isoformat()),
            )


def _public_user(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {"id": row["id"], "email": row["email"], "display_name": row["display_name"]}


def get_user_by_id(user_id: str) -> dict | None:
    with connect() as db:
        row = db.execute("SELECT id,email,display_name FROM users WHERE id=?", (user_id,)).fetchone()
    return _public_user(row)


def authenticate_user(email: str, password: str) -> dict | None:
    with connect() as db:
        row = db.execute("SELECT * FROM users WHERE email=? COLLATE NOCASE", (email.strip().lower(),)).fetchone()
    if row is None:
        return None
    try:
        algorithm, rounds, encoded_salt, encoded_digest = row["password_hash"].split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return None
        salt = base64.b64decode(encoded_salt)
        expected = base64.b64decode(encoded_digest)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(rounds))
    except (ValueError, TypeError):
        return None
    if not secrets.compare_digest(actual, expected):
        return None
    return _public_user(row)


def transfer_feedback(source_user_id: str, target_user_id: str) -> None:
    if source_user_id == target_user_id:
        return
    with connect() as db:
        db.execute("UPDATE feedback SET user_id=? WHERE user_id=?", (target_user_id, source_user_id))


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
