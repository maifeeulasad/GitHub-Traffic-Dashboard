# GitHub-Traffic-Dashboard

A self-hosted **Grafana dashboard for GitHub repository Insights** — traffic (views,
unique visitors, clones, unique cloners), referring sites, and popular content — built
as a **lead-generation / audience-insight** tool: summarize all repos, drill into a
selected repo, rank traffic sources, and slice by interesting filters.

- **Author:** Maifee Ul Asad
- **License:** GPLv3
- **Workflow:** no issues, no branches, no PRs — progress is tracked in this checklist.

See [`CLAUDE.md`](CLAUDE.md) for the full design/instruction set.

## Quickstart

```bash
cp .env.example .env
# token + full repo list (owned first, then forks, newest push first):
{
  echo "GH_TOKEN=$(gh auth token)"
  echo "COLLECT_DAYS=14"
  echo "REPOS=$(gh repo list <owner> -L 2000 --json nameWithOwner,isFork,pushedAt --jq '
    (map(select(.isFork|not))|sort_by(.pushedAt)|reverse)
    + (map(select(.isFork))|sort_by(.pushedAt)|reverse) | map(.nameWithOwner)|join(","))"
} >> .env
docker compose up -d --build
```

- Grafana: <http://localhost:3000> → dashboard **GitHub Traffic Insights**.
  Login is disabled (anonymous Admin) for local use.
- Both containers run **non-root** (uid 472) and share a SQLite named volume.
- The collector runs one 14-day pass immediately, then once every 24h. It also
  syncs cheap repo metadata (fork/visibility/archived) each pass.
- Force a fresh full pull: `docker compose exec collector python -m ghtraffic.cli --backfill`
- Refresh only repo metadata: `docker compose exec collector python -m ghtraffic.cli --sync-repos`

> Rootless Docker note: if `docker` can't find the daemon, point it at the
> rootless socket: `export DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock`.

## Dashboard

- **Overview** — total/unique views & clones (respect the filters).
- **Trends** — aggregated views & clones over time (legend tables with totals).
- **Detailed per-repository views** — collapsed, opt-in row: one line per repo,
  pure local-DB query (no API cost).
- **Lead sources & content** — referring sites, popular paths, per-repo summary.
- **Momentum** — week-over-week top-growing repos (color-graded delta).
- **Filters** (top): `visibility` (public/private), `type` (source/fork),
  `archived`, and a chained `repository` picker.
- **Alerts** — per-repo week-over-week **growth** (>30) and **drop** (<-20).
  Wire up SMTP or a webhook contact point in Grafana to actually deliver.

## Stack

`gh` CLI (auth today, PAT/App provisioned for later) → Python OOP collector →
SQLite (single file, idempotent daily upserts) → Grafana (`frser-sqlite-datasource`,
provisioned dashboards + alerts). Two containers only, via `docker compose`.
Client retries on rate-limit (403/429) and transient DNS/network errors.

## Roadmap / Task tracking

### Foundations
- [x] Add persistent instruction set (`CLAUDE.md`)
- [x] Rewrite `README.md` with goals + checklist
- [x] `.gitignore` (`.env`, data volumes, Python caches)
- [x] `.env.example` documenting `GH_TOKEN`, `REPOS`, DB creds

### Data model (SQLite)
- [x] `traffic_daily(repo, day, metric, count, uniques)` upsert key
- [x] `referrers(repo, day, source, count, uniques)` upsert key
- [x] `popular_paths(repo, day, path, count, uniques)` upsert key
- [x] `repos(repo, is_fork, visibility, is_archived, updated_at)` dimension table
- [x] Bootstrap `schema.sql`

### Collector (Python, OOP)
- [x] `AuthProvider` interface + `CliAuthProvider` (`gh auth token`)
- [x] `EnvTokenProvider` provision (reads `GH_TOKEN`)
- [x] `GitHubClient` wrapping traffic/referrers/paths endpoints
- [x] `RepoMeta` sync via `list_owned_repos` / `--sync-repos`
- [x] Domain models: `TrafficPoint`, `Referrer`, `PopularPath`, `RepoMeta`
- [x] DAO / repository layer with idempotent upserts + `busy_timeout`
- [x] Rate-limit + DNS/network retry with backoff
- [x] `collect --once` one-shot entrypoint
- [x] Daily scheduler (last 1–2 days pull) + backfill mode

### Infra
- [x] `docker compose`: grafana + collector (non-root, shared named volume)
- [x] Grafana provisioning: `frser-sqlite-datasource` as code
- [x] Grafana dashboard JSON: overview + per-repo + sources + filters
- [x] Template variables: `$repository` + visibility/type/archived filters
- [x] Anonymous Grafana (password disabled) for local use

### Features
- [x] Multi-repo config (list of repos to track)
- [x] Week-over-week deltas / top-growing repos panel
- [x] Detailed per-repository views graph (collapsed, opt-in)
- [x] Growth / drop alerts (per repo, week-over-week)
- [x] Docs: quickstart in README

### Backlog / ideas
- [ ] Contact point (SMTP/webhook) so alerts actually deliver
- [ ] PAT / GitHub App auth provider (currently CLI token)
- [ ] Clones-based momentum + referrer-trend panels
