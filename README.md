# Kalshi chess analytics — data ingest

This repository pulls **chess-related prediction markets and public trades** from [Kalshi’s public REST API](https://kalshi.com) and lands them in **Google BigQuery** for analysis. No Kalshi API key is required—the endpoints used here are public.

**Status:** Step 1 is **done** (ingest to BigQuery `raw`). **dbt** models and **Airflow on Composer** are planned next. See [plan.md](plan.md).

## Architecture overview

Solid boxes are **live today**. Dashed boxes and arrows are **planned** (step 2+).

<p align="center">
  <img
    src="kalshi-market-data-pipeline.png"
    alt="Architecture: Kalshi API to extract_chess.py (local or Cloud Run Job) to JSONL and raw BigQuery; Scheduler, staging, and marts are planned"
    width="50%"
  />
</p>

| Layer | Role |
| --- | --- |
| **Kalshi API** | Source of chess markets and public trades ([live vs historical](api_history.md) routing inside the script). |
| **extract_chess.py** | Fetch, paginate, write JSONL; optionally append to BigQuery. |
| **Cloud Run Job** | Same script with `--load` in production; image from Artifact Registry via [deploy/cloud_run_ingest.sh](deploy/cloud_run_ingest.sh). |
| **raw** | Landing zone—API shape, `_ingested_at` lineage; overlaps OK until staging dedupes. |
| **staging / marts** | Not built yet—see [plan.md](plan.md). |

---

**Medallion layout (BigQuery datasets):**

- **`raw`** — API-shaped snapshots (this repo loads here).
- **`staging`** — reserved for deduplicated, cleaned tables (future **dbt**).
- **`marts`** — reserved for analytics-ready models (future **dbt**).

**Tables written by ingest:**

- `raw.kalshi_chess_markets`
- `raw.kalshi_chess_trades`

`raw` is intentionally **not deduplicated**. Weekly runs with a 7-day window will append overlapping rows; dedupe belongs in `staging` later.

---

## How it works (high level)

1. **Discover** chess series and markets (default: markets whose `created_time` is in the last **7 days**; override with `--days`).
2. **Fetch trades** for those markets over the same time window.
3. **Route live vs historical** using Kalshi’s `/historical/cutoff` (older settled markets and trades use historical endpoints). Details: [api_history.md](api_history.md).
4. **Paginate** all list endpoints (page size 1000). Details: [api_pagination.md](api_pagination.md).
5. **Write** newline-delimited JSON locally, or **append** to BigQuery with a batch load job when you pass `--load`.

Retries: HTTP **429** only (exponential backoff). Other errors fail fast after `raise_for_status()`.

---

## Quick start

Needs [Poetry](https://python-poetry.org/docs/#installation) (Python 3.11+). For `--load` or Cloud Run: [Google Cloud SDK](https://cloud.google.com/sdk), ADC (`gcloud auth application-default login`), and `gcloud config set project kalshi-analytics-512607`.

**1. BigQuery (once)** — datasets `raw` / `staging` / `marts` and `raw.kalshi_chess_*` tables:

```bash
bq query --use_legacy_sql=false --project_id=kalshi-analytics-512607 < schema.sql
```

**2. Extract locally** — last **7 days** (default) to gitignored `data/chess_*.jsonl`; use `--days N` to narrow. `--load` appends JSONL to `raw` (fixed-point fields stay strings in files, `NUMERIC` in BQ per [schema.sql](schema.sql)):

```bash
poetry install
poetry run python extract_chess.py           # API only, no GCP
poetry run python extract_chess.py --load    # extract + append to raw
```

**3. Production** — same script with `--load` on Cloud Run Job `chess-ingest` (`chess-ingest@kalshi-analytics-512607.iam.gserviceaccount.com`). Deploy, IAM, Scheduler, amd64 build: [deploy/README.md](deploy/README.md).

```bash
./deploy/cloud_run_ingest.sh
gcloud run jobs execute chess-ingest --region=us-central1 --wait
```

After a load, verify row counts in the BigQuery console or with `bq query` on `raw.kalshi_chess_markets`.

---

## Repository map

| Path | Role |
| --- | --- |
| [extract_chess.py](extract_chess.py) | Main ingest: API → JSONL → optional BQ load |
| [schema.sql](schema.sql) | BigQuery datasets and `raw.kalshi_chess_*` DDL |
| [pyproject.toml](pyproject.toml) / [poetry.lock](poetry.lock) | Dependencies (`requests`, `google-cloud-bigquery`) |
| [Dockerfile](Dockerfile) | Image for Cloud Run Job |
| [deploy/cloud_run_ingest.sh](deploy/cloud_run_ingest.sh) | Build amd64, push, create/update job |
| [kalshi.py](kalshi.py) | Small smoke script against the API |
| [api_page_test.py](api_page_test.py) | Pagination smoke script |
| `data/` | Local JSONL output (not committed) |

---

## Roadmap

| Step | Goal | Status |
| --- | --- | --- |
| **1** | Containerized ingest → `raw.kalshi_chess_*` | **Complete** |
| **2** | dbt: `staging` + `marts` (dedupe, analytics SQL) | Planned |
| **3** | Composer DAG: ingest → dbt | Planned |

Full target stack (Composer, second dbt job): [plan.md](plan.md).

---

## Further reading

| Document | Contents |
| --- | --- |
| [plan.md](plan.md) | Roadmap and target architecture |
| [deploy/README.md](deploy/README.md) | Cloud Run, Artifact Registry, Scheduler, IAM |
| [api_pagination.md](api_pagination.md) | Cursor pagination conventions |
| [api_history.md](api_history.md) | Live vs historical endpoints |
| [AGENTS.md](AGENTS.md) | Contributor / agent conventions for this repo |
