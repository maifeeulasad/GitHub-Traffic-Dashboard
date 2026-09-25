# Slim, stdlib-only collector image. `gh` CLI is optional inside the container:
# preferred auth is GH_TOKEN passed as an env var (from `gh auth token` on the
# host), which needs no gh binary here.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
# no-op today (stdlib only) but honoured for future deps
RUN pip install --no-cache-dir -r requirements.txt

COPY schema.sql ./schema.sql
COPY ghtraffic ./ghtraffic

# default: run forever, collecting once a day
ENTRYPOINT ["python", "-m", "ghtraffic.cli"]
CMD ["--daemon", "--interval", "24"]
