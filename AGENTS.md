# Repository Guidelines

## Project Structure & Module Organization

Kalshi chess ingestion: `extract_chess.py` pulls markets and trades (last `--days`, default 7) to JSONL under `data/`, then optionally appends to BigQuery project `kalshi-analytics-512607` (number `9542648690`).

**Medallion datasets:** `raw`, `staging`, `marts`. **Ingest tables:** `raw.kalshi_chess_markets`, `raw.kalshi_chess_trades`. See [bq_best_practices.md](bq_best_practices.md).

**Step 1 is complete:** Poetry, Docker, Cloud Run Job `chess-ingest` (`us-central1`). dbt and Composer are later — [plan.md](plan.md).

Reference: [api_pagination.md](api_pagination.md), [api_history.md](api_history.md). Smoke scripts: `kalshi.py`, `api_page_test.py`. Do not commit `data/` or credentials.

## Build, Test, and Development Commands

- `poetry install` — dependencies from `pyproject.toml` / `poetry.lock`.
- `poetry run python extract_chess.py` — JSONL only (no GCP).
- `bq query --use_legacy_sql=false --project_id=kalshi-analytics-512607 < schema.sql` — datasets + raw tables (once).
- `poetry run python extract_chess.py --load` — append to `raw.kalshi_chess_*` (ADC).
- `docker build --platform linux/amd64 -t chess-ingest:local .` — local image (match Cloud Run arch).
- `./deploy/cloud_run_ingest.sh` — build amd64, push to Artifact Registry, update job.
- `gcloud run jobs execute chess-ingest --region=us-central1 --wait` — production ingest.

Deploy and IAM: [deploy/README.md](deploy/README.md). Live API calls need network.

## Coding Style & Naming Conventions

Python 3, four-space indent, `snake_case`, uppercase module constants. Timeout + `raise_for_status()` on every request. Retry HTTP 429 in `extract_chess.py` only. Fixed-point API values stay strings in JSONL; BigQuery casts via `schema.sql`. Pagination: [api_pagination.md](api_pagination.md). Historical routing: [api_history.md](api_history.md).

## Testing Guidelines

No pytest. `api_page_test.py` is a live smoke script. After API changes, `poetry run python extract_chess.py --days 1` before `--load`. Loads: `WRITE_APPEND`, `CREATE_NEVER`.

## Commit & Pull Request Guidelines

Short imperative subject. PRs: API behavior, manual check (local or Cloud Run execution), sample JSONL when helpful.

## Security & Configuration Tips

No Kalshi API key. Local `--load` uses ADC. Cloud Run uses `chess-ingest@…` service account. No `.env` required. Append-only `raw`; dedupe in future dbt `staging`.
