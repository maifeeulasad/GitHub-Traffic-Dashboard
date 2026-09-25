"""Orchestrates: fetch via GitHubClient -> map to models -> persist via Storage."""

from __future__ import annotations

import datetime as dt
import logging

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
    ) -> None:
        self._client = client
        self._storage = storage
        self._collect_days = collect_days

    def collect(self, repository: str) -> None:
        today = dt.date.today().isoformat()
        cutoff = dt.date.today() - dt.timedelta(days=self._collect_days)

        # --- daily time series: keep only the recent tail (we own history) ---
        points: list[TrafficPoint] = []
        points += self._map_series(repository, "views", self._client.views(repository), cutoff)
        points += self._map_series(repository, "clones", self._client.clones(repository), cutoff)
        n = self._storage.upsert_traffic(points)
        log.info("%s: upserted %d traffic points (>= %s)", repository, n, cutoff)

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
        log.info("%s: upserted %d referrers", repository, self._storage.upsert_referrers(refs))

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
        log.info("%s: upserted %d popular paths", repository, self._storage.upsert_paths(paths))

    def collect_all(self, repositories: list[str]) -> None:
        for repo in repositories:
            try:
                self.collect(repo)
            except Exception:  # noqa: BLE001 - one repo failing must not sink the rest
                log.exception("failed to collect %s", repo)

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
