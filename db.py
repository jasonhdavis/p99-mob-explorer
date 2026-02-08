import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS pages (
  title TEXT PRIMARY KEY,
  pageid INTEGER,
  revision_id INTEGER,
  revision_ts TEXT,
  wikitext TEXT,
  fetched_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS template_kv (
  title TEXT,
  template_name TEXT,
  param_name TEXT,
  param_value TEXT,
  fetched_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_template_kv_title ON template_kv(title);
CREATE INDEX IF NOT EXISTS idx_template_kv_template ON template_kv(template_name);
CREATE INDEX IF NOT EXISTS idx_template_kv_param ON template_kv(param_name);

CREATE TABLE IF NOT EXISTS npc_core (
  title TEXT PRIMARY KEY,
  level_min INTEGER,
  level_max INTEGER,
  hp INTEGER,
  ac INTEGER,
  atk INTEGER,
  zone TEXT,
  race TEXT,
  class TEXT,
  npc_id INTEGER,
  parsed_from_template TEXT,
  parse_version TEXT,
  parsed_at TEXT DEFAULT (datetime('now'))
);
"""

def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
