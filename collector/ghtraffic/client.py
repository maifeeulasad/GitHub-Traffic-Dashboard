"""Thin GitHub REST client for the traffic/insights endpoints.

Uses only the standard library (urllib) so the collector has no pip deps.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from .auth import AuthProvider

API_ROOT = "https://api.github.com"
USER_AGENT = "github-traffic-dashboard/0.1"

log = logging.getLogger("ghtraffic.client")


class GitHubApiError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"GitHub API {status}: {message}")
        self.status = status


class GitHubClient:
    """Reads the repo traffic surface. One instance is reusable across repos."""

    def __init__(
        self, auth: AuthProvider, api_root: str = API_ROOT, max_retries: int = 4
    ) -> None:
        self._auth = auth
        self._api_root = api_root.rstrip("/")
        self._max_retries = max_retries

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
        for attempt in range(self._max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                # 403/429 with rate-limit signals are transient: back off + retry.
                wait = self._retry_after(exc)
                if wait is not None and attempt < self._max_retries:
                    log.warning("rate-limited on %s; sleeping %ds", path, wait)
                    time.sleep(wait)
                    continue
                body = exc.read().decode("utf-8", "replace")
                raise GitHubApiError(exc.code, body) from exc
            except (urllib.error.URLError, OSError) as exc:
                # DNS hiccups / transient network errors (common under rootless
                # Docker networking): exponential backoff and retry.
                if attempt < self._max_retries:
                    wait = 2 ** attempt
                    log.warning("network error on %s (%s); retry in %ds", path, exc, wait)
                    time.sleep(wait)
                    continue
                raise GitHubApiError(0, f"network error: {exc}") from exc
        raise GitHubApiError(0, "exhausted retries")  # unreachable

    @staticmethod
    def _retry_after(exc: urllib.error.HTTPError) -> int | None:
        """Seconds to wait for a retryable rate-limit response, else None."""
        if exc.code not in (403, 429):
            return None
        headers = exc.headers
        retry_after = headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            return min(int(retry_after), 300)
        if headers.get("X-RateLimit-Remaining") == "0":
            reset = headers.get("X-RateLimit-Reset")
            if reset and reset.isdigit():
                return max(1, min(int(reset) - int(time.time()) + 1, 300))
        return None

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
