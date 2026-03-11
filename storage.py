import sqlite3
import os
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

DB_FILE = "counters.db"
LOG_DIR = "serial_logs"

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
    def __init__(self, db_path=DB_FILE, log_dir=LOG_DIR):
        self.db_path = db_path
        self.log_dir = log_dir
        self._lock = threading.Lock()
        os.makedirs(self.log_dir, exist_ok=True)
        self._ensure_tables()

    @staticmethod
    def _now_cot():
        return datetime.now(ZoneInfo("America/Bogota"))

    def _ensure_column(self, conn, table_name, column_name, definition):
        c = conn.cursor()
        c.execute(f"PRAGMA table_info({table_name})")
        existing_columns = {row[1] for row in c.fetchall()}
        if column_name not in existing_columns:
            c.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

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
        c.execute("""
        CREATE TABLE IF NOT EXISTS serial_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_cot TEXT NOT NULL,
            raw_line TEXT NOT NULL
        )
        """)
        self._ensure_column(conn, "readings", "timestamp_cot", "TEXT")
        self._ensure_column(conn, "readings", "raw_frame", "TEXT")
        conn.commit()
        conn.close()

    def _append_raw_log_file(self, timestamp_cot, raw_line):
        date_str = timestamp_cot.strftime("%Y-%m-%d")
        log_path = os.path.join(self.log_dir, f"serial_raw_{date_str}.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{timestamp_cot.strftime('%Y-%m-%d %H:%M:%S')} | {raw_line}\n")

    def _append_readings_log_file(self, timestamp_cot, data):
        date_str = timestamp_cot.strftime("%Y-%m-%d")
        log_path = os.path.join(self.log_dir, f"serial_readings_{date_str}.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                (
                    f"{timestamp_cot.strftime('%Y-%m-%d %H:%M:%S')} | "
                    f"ESP={data.get('esp')} | "
                    f"TMP={data.get('TMP')} | HUM={data.get('HUM')} | "
                    f"PRS={data.get('PRS')} | ET={data.get('ET')} | O3={data.get('O3')}\n"
                )
            )

    def save_raw_serial_line(self, raw_line):
        if not raw_line:
            return

        timestamp_cot = self._now_cot()
        timestamp_text = timestamp_cot.strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO serial_raw (timestamp_cot, raw_line)
                VALUES (?, ?)
                """,
                (timestamp_text, raw_line),
            )
            conn.commit()
            conn.close()
            self._append_raw_log_file(timestamp_cot, raw_line)

    def save_reading(self, data):
        timestamp_cot = self._now_cot()
        timestamp_text = timestamp_cot.strftime("%Y-%m-%d %H:%M:%S")
        raw_frame = data.get("_raw_frame")
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO readings (esp, timestamp, timestamp_cot, tmp, hum, prs, et, o3, raw_frame)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.get("esp"),
                    timestamp_text,
                    timestamp_text,
                    data.get("TMP"),
                    data.get("HUM"),
                    data.get("PRS"),
                    data.get("ET"),
                    data.get("O3"),
                    raw_frame,
                ),
            )
            conn.commit()
            conn.close()
            self._append_readings_log_file(timestamp_cot, data)
