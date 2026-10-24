# Kalshi chess ingest

Kalshi **chess** prediction markets (Sports + Chess tag / “chess” in title) → JSONL → BigQuery **`raw.kalshi_chess_markets`** / **`raw.kalshi_chess_trades`**. Project **`kalshi-analytics-512607`**. Datasets: **`raw`**, **`staging`**, **`marts`**. Roadmap: [plan.md](plan.md).

## Summary

We stood up an end-to-end chess ingest from Kalshi’s public API into BigQuery’s medallion raw layer (`raw.kalshi_chess_markets` / `raw.kalshi_chess_trades`), with empty staging and marts datasets ready for dbt later.

Ingestion is containerized (Poetry + Docker, linux/amd64) and runs as a Cloud Run Job (`chess-ingest` in us-central1), loading append-only snapshots with `_ingested_at` for lineage.

IAM uses a dedicated service account with BigQuery load permissions; no `.env` or API keys for Kalshi. Local runs use Poetry/ADC; production uses the job identity.

Operational model: manual or weekly scheduled runs over a 7-day window; raw is intentionally not deduped—staging/marts will own latest market per ticker and one row per trade.

Step 1 is complete and documented; dbt and Composer are the planned next phase for dedupe, analytics models, and orchestration.

## Docs

| File | Purpose |
| --- | --- |
| [plan.md](plan.md) | Roadmap, architecture |
| [deploy/README.md](deploy/README.md) | Cloud Run, IAM, Scheduler |
| [bq_best_practices.md](bq_best_practices.md) | BQ medallion + queries |
| [api_pagination.md](api_pagination.md) · [api_history.md](api_history.md) | Kalshi API reference |

## Layout

`extract_chess.py` · `schema.sql` · `pyproject.toml` / `poetry.lock` · `Dockerfile` · `deploy/cloud_run_ingest.sh` · `data/` (gitignored JSONL)

## Run locally

[Poetry](https://python-poetry.org/docs/#installation) required. Once: `gcloud auth application-default login` and `gcloud config set project kalshi-analytics-512607`.

```bash
poetry install
poetry run python extract_chess.py              # JSONL only
poetry run python extract_chess.py --load       # append to raw
```

Default lookback: **7 days** (`--days`). Append-only `raw`; dedupe in future dbt **staging**.

## Run on GCP

Details: [deploy/README.md](deploy/README.md). Deploy script builds **linux/amd64** (Apple Silicon).

```bash
bq query --use_legacy_sql=false --project_id=kalshi-analytics-512607 < schema.sql   # once
./deploy/cloud_run_ingest.sh
gcloud run jobs execute chess-ingest --region=us-central1 --wait
```

Check rows: `bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM \`kalshi-analytics-512607.raw.kalshi_chess_markets\`'`

Production identity: `chess-ingest@kalshi-analytics-512607.iam.gserviceaccount.com`.

## Smoke scripts

`poetry run python kalshi.py` · `poetry run python api_page_test.py`
