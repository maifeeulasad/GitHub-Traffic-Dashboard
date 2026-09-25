"""Authentication strategies.

Auth is behind an interface so we can move from the gh CLI to a PAT or a
GitHub App without touching any call site. Only CLI + env-token are wired up
today; the App provider is a documented stub.
"""

from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod


class AuthError(RuntimeError):
    """Raised when no usable token can be obtained."""


class AuthProvider(ABC):
    """Supplies a GitHub API token."""

    @abstractmethod
    def token(self) -> str:
        """Return a bearer token, or raise AuthError."""


class EnvTokenProvider(AuthProvider):
    """Reads a token from an environment variable (provision for real PATs)."""

    def __init__(self, var: str = "GH_TOKEN") -> None:
        self._var = var

    def token(self) -> str:
        value = os.environ.get(self._var, "").strip()
        if not value:
            raise AuthError(f"environment variable {self._var} is empty")
        return value


class CliAuthProvider(AuthProvider):
    """Shells out to `gh auth token` (the CLI-now default)."""

    def __init__(self, gh_binary: str = "gh") -> None:
        self._gh = gh_binary

    def token(self) -> str:
        try:
            out = subprocess.run(
                [self._gh, "auth", "token"],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as exc:
            raise AuthError(f"{self._gh} not found on PATH") from exc
        except subprocess.CalledProcessError as exc:
            raise AuthError(f"`gh auth token` failed: {exc.stderr.strip()}") from exc
        value = out.stdout.strip()
        if not value:
            raise AuthError("`gh auth token` returned empty output")
        return value


class GitHubAppProvider(AuthProvider):
    """Future: mint an installation access token from a GitHub App.

    Stubbed intentionally — implement JWT signing + installation token exchange
    when we need unattended, higher-rate-limit auth.
    """

    def token(self) -> str:  # pragma: no cover - not implemented yet
        raise NotImplementedError("GitHub App auth is not implemented yet")


class ChainAuthProvider(AuthProvider):
    """Tries providers in order, returning the first token that works."""

    def __init__(self, *providers: AuthProvider) -> None:
        if not providers:
            raise ValueError("ChainAuthProvider needs at least one provider")
        self._providers = providers

    def token(self) -> str:
        errors = []
        for provider in self._providers:
            try:
                return provider.token()
            except AuthError as exc:
                errors.append(f"{type(provider).__name__}: {exc}")
        raise AuthError("no auth provider yielded a token: " + "; ".join(errors))


def default_provider() -> AuthProvider:
    """Env token first (works in containers), then fall back to the gh CLI."""
    return ChainAuthProvider(EnvTokenProvider(), CliAuthProvider())
