# Kalshi chess ingest

Pull Kalshi **chess markets and public trades** from the last 7 days into newline-delimited JSON, then append them to BigQuery **`raw`**.

This is prediction-market data (series tagged Chess, plus Sports series whose title contains "chess"). It is not a Chess.com or Lichess game feed.

GCP project: `kalshi-analytics-512607` (project number `9542648690`). **Medallion datasets:** `raw`, `staging`, `marts` (layer-only naming). Ingest targets **`raw.kalshi_chess_markets`** and **`raw.kalshi_chess_trades`**.

Roadmap: [plan.md](plan.md) — **step 1 (ingest + Cloud Run) is complete**; dbt and Composer are later.

## Documentation

| File | Purpose |
| --- | --- |
| [plan.md](plan.md) | Roadmap and architecture diagram |
| [deploy/README.md](deploy/README.md) | Cloud Run deploy, IAM, Scheduler, legacy cleanup |
| [bq_best_practices.md](bq_best_practices.md) | BigQuery medallion + query notes for this repo |
| [api_pagination.md](api_pagination.md) | Kalshi cursor pagination (reference) |
| [api_history.md](api_history.md) | Kalshi live vs historical API (reference) |
| [AGENTS.md](AGENTS.md) / [CLAUDE.md](CLAUDE.md) | Agent and contributor conventions |

## Layout

| Path | Role |
| --- | --- |
| `extract_chess.py` | Chess extract. Writes `data/*.jsonl`. `--load` appends to `raw.kalshi_chess_*`. |
| `schema.sql` | Creates `raw`, `staging`, `marts` and `raw.kalshi_chess_*` tables. Run once. |
| `pyproject.toml` / `poetry.lock` | Poetry dependencies (`requests`, `google-cloud-bigquery`). |
| `Dockerfile` | Image for Cloud Run Job (`extract_chess.py --load`). |
| `deploy/cloud_run_ingest.sh` | Build **linux/amd64**, push, create/update job `chess-ingest`. |
| `deploy/README.md` | Cloud Run deploy, execute, schedule, troubleshooting. |
| `kalshi.py` | Smoke script for open `KXHIGHNY` markets. |
| `api_page_test.py` | Smoke script for one page of open markets. |
| `data/` | Generated JSONL. Gitignored. |

## Quick start (local)

Requires [Poetry](https://python-poetry.org/docs/#installation).

```bash
poetry install
poetry run python extract_chess.py          # JSONL only
poetry run python extract_chess.py --load   # append to raw.kalshi_chess_*
```

Poetry may create `.venv/` locally; it is gitignored and not used on Cloud Run.

## Quick start (GCP)

One-time DDL, then deploy and run the job — details in [deploy/README.md](deploy/README.md).

```bash
bq query --use_legacy_sql=false --project_id=kalshi-analytics-512607 < schema.sql
./deploy/cloud_run_ingest.sh
gcloud run jobs execute chess-ingest --region=us-central1 --wait
```

On **Apple Silicon**, the deploy script builds `docker build --platform linux/amd64` (required for Cloud Run).

Verify loads:

```bash
bq query --use_legacy_sql=false '
SELECT "markets" AS t, COUNT(*) AS n FROM `kalshi-analytics-512607.raw.kalshi_chess_markets`
UNION ALL
SELECT "trades", COUNT(*) FROM `kalshi-analytics-512607.raw.kalshi_chess_trades`;
'
```

## GCP CLI auth (local `--load`)

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project kalshi-analytics-512607
```

Use the Google account with access to this project. Local `--load` uses Application Default Credentials. Cloud Run uses service account **`chess-ingest@kalshi-analytics-512607.iam.gserviceaccount.com`** (BigQuery Data Editor + Job User).

## Behavior

- `--days` — lookback on market `created_time` (default 7). Aligns with a weekly scheduled job (overlapping window; dedupe in future dbt **staging**).
- Each run writes `data/chess_markets_<stamp>.jsonl` and `data/chess_trades_<stamp>.jsonl`, then `--load` appends via `NEWLINE_DELIMITED_JSON`.
- **`raw` is append-only:** same `ticker` / `trade_id` may appear on multiple runs; `_ingested_at` marks the ingest batch.

Legacy prototype data may exist in dataset `kalshi` or old `raw.markets` / `raw.trades` — see [deploy/README.md](deploy/README.md) to remove.

## Other scripts

```bash
poetry run python kalshi.py
poetry run python api_page_test.py
```
