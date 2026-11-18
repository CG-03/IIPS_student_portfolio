"""SQLite helpers and schema. The database is created automatically on first run."""
import sqlite3
from contextlib import closing
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = DATA_DIR / "student_portfolio.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'admin')),
    must_change_password INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS student_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    enrollment_no TEXT NOT NULL UNIQUE,
    course TEXT DEFAULT 'MCA (5 Year Integrated)',
    semester INTEGER DEFAULT 1,
    cgpa REAL DEFAULT 0,
    phone TEXT DEFAULT '',
    location TEXT DEFAULT '',
    headline TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    github TEXT DEFAULT '',
    linkedin TEXT DEFAULT '',
    coursework TEXT DEFAULT '',
    is_public INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS academic_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    semester INTEGER NOT NULL,
    sgpa REAL NOT NULL,
    credits INTEGER DEFAULT 0,
    remarks TEXT DEFAULT '',
    UNIQUE (user_id, semester)
);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'Intermediate'
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    technologies TEXT NOT NULL,
    github_url TEXT DEFAULT '',
    demo_url TEXT DEFAULT '',
    thumbnail_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS certifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    issuer TEXT NOT NULL,
    completion_date TEXT,
    credential_id TEXT DEFAULT '',
    verify_url TEXT DEFAULT '',
    file_path TEXT
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    organization TEXT DEFAULT '',
    event_date TEXT,
    position TEXT DEFAULT '',
    description TEXT DEFAULT '',
    proof_path TEXT,
    status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Rejected')),
    admin_remark TEXT DEFAULT '',
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_skills_user ON skills(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_certs_user ON certifications(user_id);
CREATE INDEX IF NOT EXISTS idx_ach_user ON achievements(user_id);
"""

DEFAULT_SETTINGS = {
    "app_name": "IIPS Student Portfolio & Achievement Management System",
    "institution": "International Institute of Professional Studies (IIPS), DAVV, Indore",
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql, params=(), one=False):
    """Run a SELECT. Returns a list of dicts, or a single dict/None when one=True."""
    with closing(get_conn()) as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, params=()):
    """Run an INSERT/UPDATE/DELETE and return the last row id."""
    with closing(get_conn()) as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def get_setting(key, default=""):
    row = query("SELECT value FROM settings WHERE key = ?", (key,), one=True)
    return row["value"] if row else default


def init_db():
    """Create folders, tables and default settings (safe to call repeatedly)."""
    DATA_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    with closing(get_conn()) as conn:
        conn.executescript(SCHEMA)
        for k, v in DEFAULT_SETTINGS.items():
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        conn.commit()
