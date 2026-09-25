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
- **Interesting filters** — dashboard variables/filters for: repo(s), date range,
  metric (views vs clones vs uniques), referrer/source, and "unique vs total". Keep the
  schema tall/normalized so new filters are just `WHERE` clauses, not new tables.

Persist enough dimension detail (repo, day, metric, source/path, unique-vs-total) that
any of the above is a query, never a re-fetch.

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
│  collector   │──────────► │  GitHubClient │──────────────►│  PostgreSQL   │
│ (scheduler)  │            │ + AuthProvider│               │ (time series) │
└──────────────┘            └──────────────┘               └──────┬───────┘
                                                                   │ query
                                                            ┌──────▼───────┐
                                                            │   Grafana     │
                                                            │  dashboards   │
                                                            └──────────────┘
```

- **Storage = PostgreSQL** (Grafana's Postgres datasource), not Prometheus: our data is
  daily historical counts that need backfill + idempotent upserts, which suits SQL far
  better than a scrape-based TSDB. Schema keyed by `(repository, day, metric)`.
- **Collector** is a small Python (OOP) service: `AuthProvider` → `GitHubClient` →
  domain models (`TrafficPoint`, `Referrer`, `PopularPath`) → `Repository`/DAO layer →
  Postgres. Scheduling starts as a simple cron/loop; keep it swappable.
- **Grafana** is provisioned as code (datasource + dashboard JSON under
  `grafana/provisioning/`), so the whole stack is reproducible from `docker compose up`.

## Docker / local dev

- Everything runs via **`docker compose`** here: `postgres`, `grafana`, and the
  `collector`. Prefer testing in-repo with compose over host installs.
- Pass auth as `GH_TOKEN="$(gh auth token)"` in the compose env (never commit it; use a
  git-ignored `.env`). Document the one-liner in the README.
- Keep the collector runnable one-shot (`collect --once`) for manual testing and on a
  daily schedule for production.

## Working style in this repo

- Before finishing a change, tick the matching `README.md` box.
- Keep commits atomic and co-authored (see rules above).
- Don't add issue/PR/branch workflows — the README checklist is the single source of
  truth for progress.
