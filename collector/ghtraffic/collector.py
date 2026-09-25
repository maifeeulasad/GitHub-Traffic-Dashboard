"""Orchestrates: fetch via GitHubClient -> map to models -> persist via Storage."""

from __future__ import annotations

import datetime as dt
import logging
import time

from .client import GitHubClient
from .models import PopularPath, Referrer, TrafficPoint
from .storage import Storage

log = logging.getLogger("ghtraffic.collector")


class Collector:
    """Pulls the traffic surface for a set of repos and upserts it."""

    def __init__(
        self,
        client: GitHubClient,
        storage: Storage,
        collect_days: int = 2,
        repo_delay: float = 0.0,
    ) -> None:
        self._client = client
        self._storage = storage
        self._collect_days = collect_days
        self._repo_delay = repo_delay

    def collect(self, repository: str) -> None:
        today = dt.date.today().isoformat()
        cutoff = dt.date.today() - dt.timedelta(days=self._collect_days)

        # --- daily time series: keep only the recent tail (we own history) ---
        points: list[TrafficPoint] = []
        points += self._map_series(repository, "views", self._client.views(repository), cutoff)
        points += self._map_series(repository, "clones", self._client.clones(repository), cutoff)
        n = self._storage.upsert_traffic(points)
        log.debug("%s: upserted %d traffic points (>= %s)", repository, n, cutoff)

        # --- snapshots: referrers + popular paths, stamped with collection day ---
        refs = [
            Referrer(
                repository=repository,
                day=today,
                source=r.get("referrer", ""),
                count=int(r.get("count", 0)),
                uniques=int(r.get("uniques", 0)),
            )
            for r in (self._client.referrers(repository) or [])
        ]
        log.debug("%s: upserted %d referrers", repository, self._storage.upsert_referrers(refs))

        paths = [
            PopularPath(
                repository=repository,
                day=today,
                path=p.get("path", ""),
                title=p.get("title", ""),
                count=int(p.get("count", 0)),
                uniques=int(p.get("uniques", 0)),
            )
            for p in (self._client.paths(repository) or [])
        ]
        log.debug("%s: upserted %d popular paths", repository, self._storage.upsert_paths(paths))

    def collect_all(self, repositories: list[str]) -> None:
        total = len(repositories)
        ok = skipped = 0
        for i, repo in enumerate(repositories, 1):
            try:
                self.collect(repo)
                ok += 1
            except Exception as exc:  # noqa: BLE001 - one repo must not sink the rest
                skipped += 1
                # 403 usually means no push access (traffic API needs it) — expected
                # across a large repo set, so keep it quiet unless it's something else.
                log.warning("[%d/%d] skipped %s: %s", i, total, repo, exc)
            if i % 50 == 0 or i == total:
                log.info("progress: %d/%d repos (%d ok, %d skipped)", i, total, ok, skipped)
            if self._repo_delay and i < total:
                time.sleep(self._repo_delay)
        log.info("collection done: %d ok, %d skipped, of %d repos", ok, skipped, total)

    @staticmethod
    def _map_series(
        repository: str, metric: str, payload: dict, cutoff: dt.date
    ) -> list[TrafficPoint]:
        out: list[TrafficPoint] = []
        for entry in payload.get(metric, []):
            ts = entry.get("timestamp", "")
            day = ts[:10]  # "YYYY-MM-DD" from "YYYY-MM-DDT00:00:00Z"
            if not day:
                continue
            if dt.date.fromisoformat(day) < cutoff:
                continue
            out.append(
                TrafficPoint(
                    repository=repository,
                    day=day,
                    metric=metric,
                    count=int(entry.get("count", 0)),
                    uniques=int(entry.get("uniques", 0)),
                )
            )
        return out
