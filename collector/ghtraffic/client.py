"""Thin GitHub REST client for the traffic/insights endpoints.

Uses only the standard library (urllib) so the collector has no pip deps.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .auth import AuthProvider

API_ROOT = "https://api.github.com"
USER_AGENT = "github-traffic-dashboard/0.1"


class GitHubApiError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"GitHub API {status}: {message}")
        self.status = status


class GitHubClient:
    """Reads the repo traffic surface. One instance is reusable across repos."""

    def __init__(self, auth: AuthProvider, api_root: str = API_ROOT) -> None:
        self._auth = auth
        self._api_root = api_root.rstrip("/")

    def _get(self, path: str) -> Any:
        req = urllib.request.Request(
            f"{self._api_root}/{path.lstrip('/')}",
            headers={
                "Authorization": f"Bearer {self._auth.token()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise GitHubApiError(exc.code, body) from exc

    # --- traffic endpoints (require push access on the repo) ---

    def views(self, repository: str) -> Any:
        """Daily views for the last 14 days."""
        return self._get(f"repos/{repository}/traffic/views")

    def clones(self, repository: str) -> Any:
        """Daily clones for the last 14 days."""
        return self._get(f"repos/{repository}/traffic/clones")

    def referrers(self, repository: str) -> Any:
        """Top referring sites (current snapshot)."""
        return self._get(f"repos/{repository}/traffic/popular/referrers")

    def paths(self, repository: str) -> Any:
        """Top popular content paths (current snapshot)."""
        return self._get(f"repos/{repository}/traffic/popular/paths")
