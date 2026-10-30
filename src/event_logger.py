import sqlite3
from datetime import datetime


class EventLogger:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS print_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    printer TEXT NOT NULL,
                    filename TEXT,
                    status TEXT NOT NULL,
                    filament_name TEXT,
                    filament_grams REAL,
                    duration_seconds INTEGER,
                    started_at TEXT,
                    ended_at TEXT,
                    error_reason TEXT
                )
                """
            )
            conn.commit()

    def log_start(self, printer: str, filename: str, started_at: datetime | None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO print_events (
                    printer, filename, status, started_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    printer,
                    filename,
                    "printing",
                    started_at.isoformat() if started_at else None,
                )
            )
            conn.commit()
            return cursor.lastrowid

    def log_end(
        self,
        event_id: int | None,
        printer: str,
        filename: str,
        status: str,
        filament_name: str,
        filament_grams: float | None,
        duration_seconds: int,
        ended_at: datetime | None,
        error_reason: str | None = None,
    ):
        with sqlite3.connect(self.db_path) as conn:
            if event_id:
                conn.execute(
                    """
                    UPDATE print_events
                    SET status = ?,
                        filament_name = ?,
                        filament_grams = ?,
                        duration_seconds = ?,
                        ended_at = ?,
                        error_reason = ?
                    WHERE id = ?
                    """,
                    (
                        status,
                        filament_name,
                        filament_grams,
                        duration_seconds,
                        ended_at.isoformat() if ended_at else None,
                        error_reason,
                        event_id,
                    )
                )
            else:
                conn.execute(
                    """
                    INSERT INTO print_events (
                        printer,
                        filename,
                        status,
                        filament_name,
                        filament_grams,
                        duration_seconds,
                        ended_at,
                        error_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        printer,
                        filename,
                        status,
                        filament_name,
                        filament_grams,
                        duration_seconds,
                        ended_at.isoformat() if ended_at else None,
                        error_reason,
                    )
                )
            conn.commit()
