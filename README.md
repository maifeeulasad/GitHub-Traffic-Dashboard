# GitHub-Traffic-Dashboard

A self-hosted **Grafana dashboard for GitHub repository Insights** — traffic (views,
unique visitors, clones, unique cloners), referring sites, and popular content — built
as a **lead-generation / audience-insight** tool: summarize all repos, drill into a
selected repo, rank traffic sources, and slice by interesting filters.

- **Author:** Maifee Ul Asad
- **License:** GPLv3
- **Workflow:** no issues, no branches, no PRs — progress is tracked in this checklist.

See [`CLAUDE.md`](CLAUDE.md) for the full design/instruction set.

## Stack

`gh` CLI (auth today, PAT/App provisioned for later) → Python OOP collector →
SQLite (single file, idempotent daily upserts) → Grafana (`frser-sqlite-datasource`,
provisioned dashboards). Two containers only, via `docker compose`.

## Roadmap / Task tracking

### Foundations
- [x] Add persistent instruction set (`CLAUDE.md`)
- [x] Rewrite `README.md` with goals + checklist
- [ ] `.gitignore` (`.env`, data volumes, Python caches)
- [ ] `.env.example` documenting `GH_TOKEN`, `REPOS`, DB creds

### Data model (SQLite)
- [ ] `traffic_daily(repo, day, metric, count, uniques)` upsert key
- [ ] `referrers(repo, day, source, count, uniques)` upsert key
- [ ] `popular_paths(repo, day, path, count, uniques)` upsert key
- [ ] Bootstrap `schema.sql`

### Collector (Python, OOP)
- [ ] `AuthProvider` interface + `CliAuthProvider` (`gh auth token`)
- [ ] `EnvTokenProvider` provision (reads `GH_TOKEN`)
- [ ] `GitHubClient` wrapping traffic/referrers/paths endpoints
- [ ] Domain models: `TrafficPoint`, `Referrer`, `PopularPath`
- [ ] DAO / repository layer with idempotent upserts
- [ ] `collect --once` one-shot entrypoint
- [ ] Daily scheduler (last 1–2 days pull) + backfill mode

### Infra
- [ ] `docker compose`: grafana + collector (shared `data/` volume)
- [ ] Grafana provisioning: `frser-sqlite-datasource` as code
- [ ] Grafana dashboard JSON: overview + per-repo + sources + filters
- [ ] Template variables: `$repository`, date range, metric, source

### Polish
- [ ] Multi-repo config (list of repos to track)
- [ ] Week-over-week deltas / top-growing repos panel
- [ ] Docs: quickstart in README
