# Slim, stdlib-only collector image. `gh` CLI is optional inside the container:
# preferred auth is GH_TOKEN passed as an env var (from `gh auth token` on the
# host), which needs no gh binary here.
FROM python:3.12-slim

# Run as uid 472 to match the official Grafana image's user, so both containers
# share the SQLite named volume at the same uid (WAL works, no root needed).
RUN groupadd -g 472 app && useradd -u 472 -g 472 -m app

WORKDIR /app
COPY requirements.txt ./
# no-op today (stdlib only) but honoured for future deps
RUN pip install --no-cache-dir -r requirements.txt

COPY schema.sql ./schema.sql
COPY ghtraffic ./ghtraffic

# /data owned by 472 so a fresh named volume inherits that ownership
RUN mkdir -p /data && chown -R 472:472 /data /app
USER 472

# default: run forever, collecting once a day
ENTRYPOINT ["python", "-m", "ghtraffic.cli"]
CMD ["--daemon", "--interval", "24"]
