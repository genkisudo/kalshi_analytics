# CLAUDE.md

Guidance for agents working in this repository.

## Overview

Chess ingestion calls the Kalshi public REST API with `requests`. Dependencies: **Poetry** (`pyproject.toml`, `package-mode = false`). Production: **Cloud Run Job** `chess-ingest` in `us-central1` runs `extract_chess.py --load` from a **linux/amd64** Docker image ([deploy/cloud_run_ingest.sh](deploy/cloud_run_ingest.sh)).

```bash
poetry install
poetry run python extract_chess.py          # last 7 days -> data/chess_*.jsonl
poetry run python extract_chess.py --load   # append to raw.kalshi_chess_*
```

GCP project `kalshi-analytics-512607` (number `9542648690`). Datasets **`raw`**, **`staging`**, **`marts`**. Ingest: `raw.kalshi_chess_markets`, `raw.kalshi_chess_trades`. DDL: [schema.sql](schema.sql). [bq_best_practices.md](bq_best_practices.md). [plan.md](plan.md) — step 1 complete; dbt/Composer later.

Local `--load`: `google-cloud-bigquery` + ADC. Cloud Run: service account `chess-ingest@kalshi-analytics-512607.iam.gserviceaccount.com`.

Smoke scripts: `kalshi.py`, `api_page_test.py`.

## Reference docs

- [api_pagination.md](api_pagination.md) — cursors; `extract_chess.py` uses `PAGE_LIMIT=1000`.
- [api_history.md](api_history.md) — `/historical/cutoff` and dual endpoints.
- [deploy/README.md](deploy/README.md) — deploy, execute, Scheduler, IAM, amd64, troubleshooting.

## API conventions

- Base URL: `https://external-api.kalshi.com/trade-api/v2`.
- Fixed-point fields as strings in JSONL; BQ `NUMERIC` on load.
- Chess series: Sports + tag `Chess`, plus title contains `chess`.
- Window: market `created_time` over `--days` (default 7); trades same window; live/historical split at `trades_created_ts`.
- Timeout, `raise_for_status()`, retry 429 only.
- Loads: `NEWLINE_DELIMITED_JSON`, `WRITE_APPEND`, `CREATE_NEVER`.
