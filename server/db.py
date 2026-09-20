import sqlite3

DB_PATH = "c2.db"


def init_db(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS agents(
            id TEXT PRIMARY KEY,
            hostname TEXT,
            first_seen TEXT,
            last_seen TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tasks(
            id TEXT PRIMARY KEY,
            agent_id TEXT,
            cmd TEXT,
            status TEXT,
            stdout TEXT,
            stderr TEXT,
            exit_code INTEGER,
            created_at TEXT,
            completed_at TEXT
        )"""
    )
    conn.commit()
    return conn
