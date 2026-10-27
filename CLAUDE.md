# CLAUDE.md

Guidance for agents working in this repository.

## Overview

Chess ingestion calls the Kalshi public REST API with `requests`. Dependencies: **Poetry** (`pyproject.toml`, `package-mode = false`). Production: **Cloud Run Job** `chess-ingest` in `us-central1` runs `extract_chess.py --load` from a **linux/amd64** Docker image ([deploy/cloud_run_ingest.sh](deploy/cloud_run_ingest.sh)).

```bash
poetry install
poetry run python extract_chess.py          # last 7 days -> data/chess_*.jsonl
poetry run python extract_chess.py --load   # append to raw.kalshi_chess_*
```

GCP project `kalshi-analytics-512607` (number `9542648690`). Datasets **`raw`**, **`staging`**, **`marts`**. Ingest: `raw.kalshi_chess_markets`, `raw.kalshi_chess_trades`. DDL: [schema.sql](schema.sql). [plan.md](plan.md) — step 1 complete; step 2 (dbt) in progress; Composer later.

dbt: project in [dbt/](dbt/README.md) (**dbt-core** + BigQuery adapter, Poetry dev group). Always run `cd dbt && poetry run dbt ...` — a separate dbt Fusion binary may be on `PATH`. Profile `kalshi_dbt` is [dbt/profiles.yml](dbt/profiles.yml) (ADC, dataset `staging`, location `US`, no secrets). Staging models: `stg_kalshi_chess_markets` (dedupe on `ticker`), `stg_kalshi_chess_trades` (on `trade_id`), latest `_ingested_at` wins; `marts` not built yet. `raw` stays append-only.

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

## Data engineering mentor

- You are a data eng mentor, guide me step by step. The goal is me to learn, i like to learn by doing. Explain every step in 2-3 lines. ask Qs if needed                                                     
