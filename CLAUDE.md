# CLAUDE.md — GitHub Traffic Dashboard

Persistent instruction set for this repository. Read this before doing any work here.

## What we are building

A self-hosted **Grafana dashboard for GitHub repository Insights** (Traffic: views,
unique visitors, clones, unique cloners, referring sites, popular content; plus
contributor/commit stats where useful).

- **Reference for UX only:** the "GitHub Actions Insights" Grafana board (gauges for
  success/overhead, stacked area for usage over time, right-hand legend tables with
  totals, grouped sections). We copy that *look and layout quality*, not its metrics.
- **Our data** is the GitHub Traffic/Insights API surface (see snap 1: Clones, Unique
  cloners, Total views, Unique visitors, Referring sites, Popular content).

## Product intent — lead generation & analytics

This is not just a pretty traffic chart; it is a **lead-generation / audience-insight
tool**. Design panels and the data model so the owner can answer:

- **Summary across all repos** — org/user-wide rollup: total views, uniques, clones,
  top-growing repos, week-over-week deltas.
- **Drill into a selected repo** — Grafana template variable `$repository` to switch a
  single repo into every panel.
- **Traffic sources** — which referring sites (reddit, HN, google, npm, personal blog,
  etc.) drive unique visitors; treat referrers as *lead channels* and rank/trend them.
- **Popular content** — which paths pull attention (candidate landing surfaces).
- **Interesting filters** — dashboard variables for: repo(s), date range, and
  repo attributes (**visibility** public/private, **type** source/fork, **archived**).
  These chain into the `$repository` picker via the `repos` dimension table. Keep the
  schema tall/normalized so new filters are just `WHERE` clauses, not new tables.
- **Detailed per-repo view** — a collapsed, opt-in graph with one line per repo. It is
  a pure local-SQLite query, so it has **no API cost** and can show everything at once;
  the aggregated Trends panels stay the default, this is the drill-down.
- **Alerts** — per-repo week-over-week **growth** and **drop** rules (provisioned).

Persist enough dimension detail (repo, day, metric, source/path, unique-vs-total, and
repo attributes) that any of the above is a query, never a re-fetch. Never re-download
traffic just to add a filter — repo attributes come from the cheap repo-list API.

## Non-negotiable project rules (from the owner)

- **Author:** Maifee Ul Asad. **License:** GPLv3 (already in `LICENSE`).
- **No GitHub issues, no branches, no PRs/MRs.** Track all work in `README.md` using
  `- [ ]` / `- [x]` checklists. Update the checklist as part of the same change.
- **Mini commits:** commit as small as sensibly possible, one logical change each.
- **Co-author every commit** with:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- **OOP + sound system design wherever it fits.** Prefer small classes with clear
  responsibilities, dependency injection, and interfaces over ad-hoc scripts.
- **Research first** when unsure — look at how others wire GitHub → Grafana before
  inventing something.

## Data collection contract

- **Cadence:** fetch **once per day**, pulling the **last 1–2 days** only (the API
  returns up to 14 days; we only need the recent tail because we persist history
  ourselves). Full 14-day pulls are fine for backfill/first run.
- **Idempotent upserts:** every metric is keyed by `(repository, date, metric)` and
  upserted, so re-running a day never double-counts. Daily overlap of 1–2 days is a
  feature (late-arriving counts get corrected), not a bug.
- **We own history.** GitHub only keeps 14 days; our datastore keeps everything.

## Auth: CLI now, token later (keep provisions)

- **Now:** authenticate via the **`gh` CLI** (already logged in as `maifeeulasad`).
  Read data with `gh api ...`. No PAT is configured or committed.
- **Important gotcha:** on this host the gh token is stored in the OS **keyring**, not
  in `~/.config/gh/hosts.yml`. So mounting `~/.config/gh` into a container does **not**
  carry auth. The reliable bridge is to export a token at runtime:
  `GH_TOKEN="$(gh auth token)"` and pass it into the container as an env var. The
  container has its own `gh` (or plain `curl`) and uses that token.
- **Design for a swap:** put auth behind an interface so we can move from CLI to a PAT
  or GitHub App without touching call sites.

  ```
  AuthProvider (interface)          -> token() -> str
    ├─ CliAuthProvider   (default)  -> shells `gh auth token`
    ├─ EnvTokenProvider  (provision)-> reads GH_TOKEN / PAT from env
    └─ GitHubAppProvider (future)   -> installation token
  ```

  Only `CliAuthProvider`/`EnvTokenProvider` are needed initially; the others are stubs
  with clear TODOs. Never hardcode or commit a token; env + `.gitignore` only.

## Relevant GitHub API endpoints (via `gh api`)

```
gh api repos/{owner}/{repo}/traffic/views              # total + unique views, 14d
gh api repos/{owner}/{repo}/traffic/clones             # total + unique clones, 14d
gh api repos/{owner}/{repo}/traffic/popular/referrers  # referring sites
gh api repos/{owner}/{repo}/traffic/popular/paths       # popular content
gh api repos/{owner}/{repo}/stats/contributors         # contributor stats
```

Traffic endpoints require **push access** to the repo (owner token satisfies this).

## Target architecture

```
┌──────────────┐   daily    ┌──────────────┐   SQL upsert   ┌──────────────┐
│  collector   │──────────► │  GitHubClient │──────────────►│   SQLite      │
│ (scheduler)  │            │ + AuthProvider│               │ data/traffic.db│
└──────────────┘            └──────────────┘               └──────┬───────┘
                                                                   │ query (plugin)
                                                            ┌──────▼───────┐
                                                            │   Grafana     │
                                                            │  dashboards   │
                                                            └──────────────┘
```

- **Storage = SQLite** (a single file, read in Grafana via the
  `frser-sqlite-datasource` plugin), not Postgres/Prometheus: our data is small, daily,
  historical counts that need backfill + idempotent upserts. SQLite gives us SQL and
  zero DB-server overhead — no extra container, just a mounted `data/traffic.db`. Schema
  keyed by `(repository, day, metric)`. If volume ever outgrows it, the DAO layer is the
  only thing that changes (swap to Postgres).
- **Collector** is a small Python (OOP) service: `AuthProvider` → `GitHubClient` →
  domain models (`TrafficPoint`, `Referrer`, `PopularPath`, `RepoMeta`) → `Storage`/DAO
  layer → SQLite. Scheduling starts as a simple loop; keep it swappable. The client
  retries on rate-limit (403/429) and transient DNS/network errors; `Storage` sets
  `busy_timeout` so a one-off `--sync-repos` can run alongside the collector.
- **Repo metadata** (`repos` table: is_fork, visibility, is_archived) is synced from the
  repo-list API (`GET /user/repos`) — a handful of cheap calls, never the traffic
  endpoints. It powers the visibility/type/archived filters.
- **Alerts** live in `grafana/provisioning/alerting/` as code: per-repo WoW change via
  `time series → reduce → threshold` (frser labels series by `repository`).
- **Grafana** is provisioned as code (SQLite datasource + dashboard JSON under
  `grafana/provisioning/`), so the whole stack is reproducible from `docker compose up`.
  Only two containers: `grafana` and `collector`, sharing the `data/` volume.

## Docker / local dev

- Everything runs via **`docker compose`** here: `grafana` and the `collector`, sharing
  a SQLite **named volume** (`dbdata`). Prefer testing in-repo with compose.
- **Never run containers as root.** Both run as uid 472 so, under rootless Docker, they
  share the volume at one uid and the SQLite WAL works without root. Use the active
  `docker context` (Docker Desktop socket); don't hardcode a socket path.
- Pass auth as `GH_TOKEN="$(gh auth token)"` in the compose env (never commit it; use a
  git-ignored `.env`). Document the one-liner in the README.
- Grafana login is **disabled** (anonymous Admin, no login form) for local use; re-enable
  auth before exposing it beyond localhost.
- Large repo sets (~1160): the client retries on rate-limit (403/429) and transient
  DNS/network errors with backoff; `REPO_DELAY` adds politeness between repos. Order
  repos owned-first then forks, newest push first.
- Keep the collector runnable one-shot (`collect --once` / `--backfill`) for manual
  testing and on a daily schedule for production.

## Working style in this repo

- Before finishing a change, tick the matching `README.md` box.
- Keep commits atomic and co-authored (see rules above).
- Don't add issue/PR/branch workflows — the README checklist is the single source of
  truth for progress.
