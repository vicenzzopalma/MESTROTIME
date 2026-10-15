"""Durable SQLite history for Maestro cycles."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from maestro.config import resolve_database_path
from maestro.models import CycleRecord


class StateStore:
    """Persist cycle outcomes in a repository-local SQLite database."""

    def __init__(self, repository_root: str | Path) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.database_path = resolve_database_path(self.repository_root)
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_db(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cycles (
                    cycle_number INTEGER PRIMARY KEY,
                    status TEXT NOT NULL CHECK(status IN ('COMMIT', 'ROLLBACK')),
                    target_file TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    duration_sec REAL NOT NULL,
                    commit_hash TEXT,
                    error_summary TEXT,
                    codex_prompt TEXT NOT NULL DEFAULT '',
                    agy_prompt TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_cycles_status ON cycles(status)"
            )

    def save_cycle(self, record: CycleRecord) -> None:
        values = record.model_dump()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO cycles (
                    cycle_number, status, target_file, rationale, duration_sec,
                    commit_hash, error_summary, codex_prompt, agy_prompt
                ) VALUES (
                    :cycle_number, :status, :target_file, :rationale, :duration_sec,
                    :commit_hash, :error_summary, :codex_prompt, :agy_prompt
                )
                ON CONFLICT(cycle_number) DO UPDATE SET
                    status = excluded.status,
                    target_file = excluded.target_file,
                    rationale = excluded.rationale,
                    duration_sec = excluded.duration_sec,
                    commit_hash = excluded.commit_hash,
                    error_summary = excluded.error_summary,
                    codex_prompt = excluded.codex_prompt,
                    agy_prompt = excluded.agy_prompt
                """,
                values,
            )

    @staticmethod
    def _to_record(row: sqlite3.Row) -> CycleRecord:
        return CycleRecord.model_validate(dict(row))

    def get_recent_cycles(self, limit: int = 20) -> list[CycleRecord]:
        if limit < 1:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM cycles ORDER BY cycle_number DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._to_record(row) for row in rows]

    def get_cycle(self, cycle_number: int) -> CycleRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM cycles WHERE cycle_number = ?", (cycle_number,)
            ).fetchone()
        return self._to_record(row) if row is not None else None

    def get_stats(self) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_cycles,
                    COALESCE(SUM(status = 'COMMIT'), 0) AS commits,
                    COALESCE(SUM(status = 'ROLLBACK'), 0) AS rollbacks,
                    COALESCE(AVG(duration_sec), 0.0) AS average_duration_sec,
                    COALESCE(MAX(cycle_number), 0) AS last_cycle_number
                FROM cycles
                """
            ).fetchone()
        stats = dict(row)
        stats["total_cycles"] = int(stats["total_cycles"])
        stats["commits"] = int(stats["commits"])
        stats["rollbacks"] = int(stats["rollbacks"])
        stats["average_duration_sec"] = float(stats["average_duration_sec"])
        stats["last_cycle_number"] = int(stats["last_cycle_number"])
        stats["success_rate"] = (
            stats["commits"] / stats["total_cycles"] if stats["total_cycles"] else 0.0
        )
        return stats
