# Repository Guidelines

## Project Structure & Module Organization

Kalshi chess ingestion: `extract_chess.py` pulls markets and trades (last `--days`, default 7) to JSONL under `data/`, then optionally appends to BigQuery project `kalshi-analytics-512607` (number `9542648690`), datasets **`raw`**, **`staging`**, **`marts`**; ingest tables `raw.kalshi_chess_markets`, `raw.kalshi_chess_trades`. See `bq_best_practices.md`.

Step 1 (see [plan.md](plan.md)): raw DDL (`schema.sql`), Poetry ([pyproject.toml](pyproject.toml)), Docker ([Dockerfile](Dockerfile)), Cloud Run Job ([deploy/cloud_run_ingest.sh](deploy/cloud_run_ingest.sh)). dbt and Composer are later steps.

`api_pagination.md` and `api_history.md` document cursors and historical cutoffs. `kalshi.py` and `api_page_test.py` are live smoke scripts. Do not commit credentials or large files in `data/`.

## Build, Test, and Development Commands

Poetry is the preferred local environment:

- `poetry install` — install dependencies.
- `poetry run python extract_chess.py` — write `data/chess_markets_*.jsonl` and `data/chess_trades_*.jsonl`. No GCP calls.
- `bq query --use_legacy_sql=false --project_id=kalshi-analytics-512607 < schema.sql` — create `raw` dataset and tables once.
- `poetry run python extract_chess.py --load` — append JSONL to `raw.kalshi_chess_*`.
- `docker build -t chess-ingest:local .` — build ingest image.
- `./deploy/cloud_run_ingest.sh` — push image and create/update Cloud Run Job `chess-ingest`.
- `gcloud run jobs execute chess-ingest --region=us-central1 --wait` — run ingest in GCP.

Live API calls need network access.

## Coding Style & Naming Conventions

Python 3, four-space indent, `snake_case`, uppercase module constants. Set a timeout and call `raise_for_status()` on every request. Retry HTTP 429 in `extract_chess.py`; do not treat other errors as empty pages. Keep fixed-point API values as strings in JSONL. BigQuery casts them to `NUMERIC` via `schema.sql`. Follow cursor pagination in `api_pagination.md`. Route old markets and trades with `GET /historical/cutoff` per `api_history.md`.

## Testing Guidelines

No pytest suite. `api_page_test.py` is a live smoke script. After pagination or historical changes, run a short `--days` smoke before `--load`. Loads use `WRITE_APPEND` and `CREATE_NEVER`.

## Commit & Pull Request Guidelines

Short imperative subject, e.g. `Add raw dataset and Cloud Run ingest job`. PRs should note API behavior, manual checks, and sample JSONL when useful.

## Security & Configuration Tips

Public Kalshi endpoints need no API key. Local `--load` uses Application Default Credentials. Cloud Run uses the job service account (BigQuery Data Editor + Job User). Keep tokens out of git. Each `--load` appends a snapshot; ticker and trade id are not unique in `raw`.
