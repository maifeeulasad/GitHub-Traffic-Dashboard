"""Domain models — plain, immutable value objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrafficPoint:
    """One repo/day/metric count (metric = 'views' or 'clones')."""

    repository: str
    day: str      # ISO date "YYYY-MM-DD"
    metric: str   # 'views' | 'clones'
    count: int
    uniques: int


@dataclass(frozen=True)
class Referrer:
    """A referring site snapshot for a repo on a collection day."""

    repository: str
    day: str
    source: str
    count: int
    uniques: int


@dataclass(frozen=True)
class PopularPath:
    """A popular content path snapshot for a repo on a collection day."""

    repository: str
    day: str
    path: str
    title: str
    count: int
    uniques: int
