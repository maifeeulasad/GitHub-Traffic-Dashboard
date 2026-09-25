-- SQLite schema for GitHub Traffic Dashboard.
-- Tall/normalized so new filters are WHERE clauses, not new tables.
-- Every row is idempotent-upsertable by its natural key.

-- Daily traffic counts. metric in ('views','clones').
-- count = total, uniques = unique visitors/cloners for that repo/day/metric.
CREATE TABLE IF NOT EXISTS traffic_daily (
    repository TEXT    NOT NULL,           -- "owner/repo"
    day        TEXT    NOT NULL,           -- ISO date "YYYY-MM-DD"
    metric     TEXT    NOT NULL,           -- 'views' | 'clones'
    count      INTEGER NOT NULL DEFAULT 0,
    uniques    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (repository, day, metric)
);

-- Referring sites (lead channels). Snapshot per collection day.
CREATE TABLE IF NOT EXISTS referrers (
    repository TEXT    NOT NULL,
    day        TEXT    NOT NULL,           -- collection day
    source     TEXT    NOT NULL,           -- e.g. "reddit.com", "Google"
    count      INTEGER NOT NULL DEFAULT 0,
    uniques    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (repository, day, source)
);

-- Popular content paths. Snapshot per collection day.
CREATE TABLE IF NOT EXISTS popular_paths (
    repository TEXT    NOT NULL,
    day        TEXT    NOT NULL,           -- collection day
    path       TEXT    NOT NULL,           -- e.g. "/tree/main/adapter"
    title      TEXT,                       -- human label from the API
    count      INTEGER NOT NULL DEFAULT 0,
    uniques    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (repository, day, path)
);

-- Repository metadata (dimension table) for filtering: fork/source,
-- public/private, archived. Populated from the repo list, NOT the traffic API.
CREATE TABLE IF NOT EXISTS repos (
    repository  TEXT    NOT NULL PRIMARY KEY,  -- "owner/repo"
    is_fork     INTEGER NOT NULL DEFAULT 0,
    visibility  TEXT    NOT NULL DEFAULT 'public',  -- 'public' | 'private'
    is_archived INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT
);

CREATE INDEX IF NOT EXISTS idx_traffic_repo_day ON traffic_daily (repository, day);
CREATE INDEX IF NOT EXISTS idx_referrers_repo_day ON referrers (repository, day);
CREATE INDEX IF NOT EXISTS idx_paths_repo_day ON popular_paths (repository, day);
