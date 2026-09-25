"""SQLite persistence — the DAO layer.

This is the single swap point if we ever outgrow SQLite: change this file, not
the collector or client. All writes are idempotent upserts on the natural key.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .models import PopularPath, Referrer, RepoMeta, TrafficPoint

_SCHEMA = Path(__file__).resolve().parent.parent / "schema.sql"


class Storage:
    """Owns the SQLite connection and the upsert operations."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, timeout=60)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        # wait (don't error) when another writer holds the lock — lets a one-off
        # metadata sync run alongside the collector safely.
        self._conn.execute("PRAGMA busy_timeout=30000;")

    def init_schema(self) -> None:
        self._conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
        self._conn.commit()

    def upsert_traffic(self, points: Iterable[TrafficPoint]) -> int:
        rows = [(p.repository, p.day, p.metric, p.count, p.uniques) for p in points]
        self._conn.executemany(
            """
            INSERT INTO traffic_daily (repository, day, metric, count, uniques)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(repository, day, metric)
            DO UPDATE SET count=excluded.count, uniques=excluded.uniques
            """,
            rows,
        )
        self._conn.commit()
        return len(rows)

    def upsert_referrers(self, referrers: Iterable[Referrer]) -> int:
        rows = [(r.repository, r.day, r.source, r.count, r.uniques) for r in referrers]
        self._conn.executemany(
            """
            INSERT INTO referrers (repository, day, source, count, uniques)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(repository, day, source)
            DO UPDATE SET count=excluded.count, uniques=excluded.uniques
            """,
            rows,
        )
        self._conn.commit()
        return len(rows)

    def upsert_paths(self, paths: Iterable[PopularPath]) -> int:
        rows = [
            (p.repository, p.day, p.path, p.title, p.count, p.uniques) for p in paths
        ]
        self._conn.executemany(
            """
            INSERT INTO popular_paths (repository, day, path, title, count, uniques)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(repository, day, path)
            DO UPDATE SET title=excluded.title, count=excluded.count,
                         uniques=excluded.uniques
            """,
            rows,
        )
        self._conn.commit()
        return len(rows)

    def upsert_repos(self, repos: Iterable[RepoMeta]) -> int:
        rows = [
            (r.repository, int(r.is_fork), r.visibility, int(r.is_archived), r.updated_at)
            for r in repos
        ]
        self._conn.executemany(
            """
            INSERT INTO repos (repository, is_fork, visibility, is_archived, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(repository)
            DO UPDATE SET is_fork=excluded.is_fork, visibility=excluded.visibility,
                         is_archived=excluded.is_archived, updated_at=excluded.updated_at
            """,
            rows,
        )
        self._conn.commit()
        return len(rows)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
