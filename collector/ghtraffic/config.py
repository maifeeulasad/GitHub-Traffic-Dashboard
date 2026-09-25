"""Runtime configuration, loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    repositories: list[str] = field(default_factory=list)
    db_path: str = "/data/traffic.db"
    collect_days: int = 2
    repo_delay: float = 0.0

    @classmethod
    def from_env(cls) -> "Config":
        repos_raw = os.environ.get("REPOS", "").strip()
        repositories = [r.strip() for r in repos_raw.split(",") if r.strip()]
        return cls(
            repositories=repositories,
            db_path=os.environ.get("DB_PATH", "/data/traffic.db"),
            collect_days=int(os.environ.get("COLLECT_DAYS", "2")),
            repo_delay=float(os.environ.get("REPO_DELAY", "0")),
        )
