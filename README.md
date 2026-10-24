# Kalshi chess ingest

Pull Kalshi **chess markets and public trades** from the last 7 days into newline-delimited JSON, then append them to BigQuery **`raw`**.

This is prediction-market data (series tagged Chess, plus Sports series whose title contains "chess"). It is not a Chess.com or Lichess game feed.

GCP project: `kalshi-analytics-512607` (project number `9542648690`). **Medallion datasets:** `raw`, `staging`, `marts`. Ingest targets **`raw.kalshi_chess_markets`** and **`raw.kalshi_chess_trades`**. See [bq_best_practices.md](bq_best_practices.md).

Roadmap: [plan.md](plan.md). Step 1 is raw landing + Poetry + Docker + Cloud Run Job; dbt and Composer come later.

## Layout

| Path | Role |
| --- | --- |
| `extract_chess.py` | Chess extract. Writes `data/*.jsonl`. `--load` appends to `raw.*`. |
| `schema.sql` | BigQuery `raw` dataset DDL. Run once before the first load. |
| `pyproject.toml` | Poetry dependencies (`requests`, `google-cloud-bigquery`). |
| `Dockerfile` | Image for Cloud Run Job (`extract_chess.py --load`). |
| `deploy/cloud_run_ingest.sh` | Build, push, create/update Cloud Run Job `chess-ingest`. |
| `deploy/README.md` | Cloud Run deploy and execute notes. |
| `api_pagination.md` | Cursor pagination. |
| `api_history.md` | Live vs `/historical/*` cutoffs. |
| `kalshi.py` | Smoke script for open `KXHIGHNY` markets. |
| `api_page_test.py` | Smoke script for one page of open markets. |
| `data/` | Generated JSONL. Gitignored. |

## Step 1 — substeps

### 1a. Raw dataset (once)

```bash
bq query --use_legacy_sql=false --project_id=kalshi-analytics-512607 < schema.sql
bq ls kalshi-analytics-512607:raw
```

### 1b. Poetry (local dev)

Requires [Poetry](https://python-poetry.org/docs/#installation).

```bash
poetry install
poetry run python extract_chess.py          # JSONL only
poetry run python extract_chess.py --load   # append to raw.kalshi_chess_*
```

Poetry creates a local virtualenv (often `.venv/`); that folder is gitignored and not used by Docker or Cloud Run.

### 1c. Docker (local test)

```bash
docker build -t chess-ingest:local .
docker run --rm \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json \
  -v "$HOME/.config/gcloud/application_default_credentials.json:/tmp/adc.json:ro" \
  chess-ingest:local
```

On Cloud Run, the job service account replaces the mounted ADC file.

### 1d. Cloud Run Job

See [deploy/README.md](deploy/README.md).

```bash
./deploy/cloud_run_ingest.sh
gcloud run jobs execute chess-ingest --region=us-central1 --wait
```

## GCP CLI auth (local)

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set account kamil.usmanov.es@gmail.com
gcloud config set project kalshi-analytics-512607
```

`--load` locally uses Application Default Credentials. The Cloud Run Job uses its attached service account.

## Behavior

`--days` changes the lookback (default 7). Each run writes `data/chess_markets_<stamp>.jsonl` and `data/chess_trades_<stamp>.jsonl`, then `--load` appends with a `NEWLINE_DELIMITED_JSON` load job.

Runs append snapshots. `markets.ticker` and `trades.trade_id` are not deduped in `raw`; dbt should keep the latest row per ticker and one row per trade id.

Older prototype data may live in dataset `kalshi`; new ingest targets **`raw`**.

## Other scripts

```bash
poetry run python kalshi.py
poetry run python api_page_test.py
```
