import sqlite3
import os

DB_FILE = "counters.db"

class CounterStorage:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS counters (
            name TEXT PRIMARY KEY,
            setpoint REAL
        )
        """)
        conn.commit()
        conn.close()

    def load_setpoint(self, name):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT setpoint FROM counters WHERE name = ?", (name,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else 0  # Default 0

    def save_setpoint(self, name, setpoint):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
        INSERT INTO counters (name, setpoint)
        VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET setpoint=excluded.setpoint
        """, (name, setpoint))
        conn.commit()
        conn.close()
 



class DataStorage:
    def __init__(self, db_path = DB_FILE):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            esp TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            tmp REAL,
            hum REAL,
            prs REAL,
            et REAL,
            o3 REAL
        )
        """)
        conn.commit()
        conn.close()

    def save_reading(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
        INSERT INTO readings (esp, tmp, hum, prs, et, o3)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["esp"],
            data["TMP"],
            data["HUM"],
            data["PRS"],
            data["ET"],
            data["O3"]
        ))
        conn.commit()
        conn.close()
