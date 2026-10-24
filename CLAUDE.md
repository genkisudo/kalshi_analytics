# CLAUDE.md

Guidance for agents working in this repository.

## Overview

Chess ingestion calls the Kalshi public REST API with `requests`. Dependencies are managed with **Poetry** (`pyproject.toml`). Production ingest runs as a **Cloud Run Job** (Docker image runs `extract_chess.py --load`).

```bash
poetry install
poetry run python extract_chess.py          # last 7 days -> data/chess_*.jsonl
poetry run python extract_chess.py --load   # append to raw.kalshi_chess_markets / raw.kalshi_chess_trades
```

GCP project `kalshi-analytics-512607` (number `9542648690`). Medallion datasets **`raw`**, **`staging`**, **`marts`**. Ingest: `raw.kalshi_chess_*`. See `bq_best_practices.md`. DDL: `schema.sql`. Create tables before the first `--load`. Local `--load` needs `google-cloud-bigquery` and ADC; Cloud Run uses the job service account.

Roadmap: [plan.md](plan.md) — step 1 is raw + Poetry + Docker + Cloud Run; dbt and Composer later.

`kalshi.py` and `api_page_test.py` are live smoke scripts.

## Reference docs

- `api_pagination.md` — cursor pagination. Keep filters constant. Loop until `cursor` is empty.
- `api_history.md` — live vs historical tiers. Cutoffs from `GET /historical/cutoff`.
- `deploy/README.md` — Cloud Run Job deploy and execute.

## API conventions

- Base URL: `https://external-api.kalshi.com/trade-api/v2`.
- Fixed-point fields stay strings in JSONL; BigQuery loads cast to `NUMERIC`.
- Chess series: Sports + tag `Chess`, plus Sports series whose title contains `chess`.
- Market window: `created_time` over `--days` (default 7). Trades split across live/historical at `trades_created_ts`.
- Timeout and `raise_for_status()` on every request. Retry 429 only.
- Loads: `NEWLINE_DELIMITED_JSON`, `WRITE_APPEND`, `CREATE_NEVER`.
