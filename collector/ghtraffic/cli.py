"""Command-line entrypoint.

  python -m ghtraffic.cli --once            # single pass, then exit
  python -m ghtraffic.cli --backfill        # pull full 14-day window once
  python -m ghtraffic.cli --daemon          # loop, once every --interval hours
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from .auth import AuthError, default_provider
from .client import GitHubClient
from .collector import Collector
from .config import Config
from .storage import Storage

log = logging.getLogger("ghtraffic")


def _run_once(cfg: Config, collect_days: int) -> None:
    with Storage(cfg.db_path) as storage:
        storage.init_schema()
        client = GitHubClient(default_provider())
        Collector(
            client, storage, collect_days=collect_days, repo_delay=cfg.repo_delay
        ).collect_all(cfg.repositories)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ghtraffic")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="run a single pass and exit")
    mode.add_argument("--backfill", action="store_true", help="pull full 14-day window once")
    mode.add_argument("--daemon", action="store_true", help="loop forever")
    parser.add_argument("--interval", type=float, default=24.0, help="daemon interval, hours")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    cfg = Config.from_env()
    if not cfg.repositories:
        log.error("no repositories configured (set REPOS=owner/repo,owner/repo)")
        return 2

    try:
        if args.backfill:
            _run_once(cfg, collect_days=14)
        elif args.daemon:
            while True:
                _run_once(cfg, collect_days=cfg.collect_days)
                log.info("sleeping %.1fh until next collection", args.interval)
                time.sleep(args.interval * 3600)
        else:  # default: --once
            _run_once(cfg, collect_days=cfg.collect_days)
    except AuthError as exc:
        log.error("auth failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
