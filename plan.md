# Kalshi analytics — roadmap

## Step 1 — Containerized ingest to BigQuery `raw` (complete)

Land Kalshi chess API data in BigQuery. Production path: **Cloud Run Job** `chess-ingest` in `us-central1` → **`raw.kalshi_chess_markets`** / **`raw.kalshi_chess_trades`**. dbt and Composer are **step 2+**.

| Substep | What | Status |
| --- | --- | --- |
| **1a. Raw dataset** | Datasets `raw` / `staging` / `marts` via [schema.sql](schema.sql); ingest tables `raw.kalshi_chess_*` | Done (DDL applied) |
| **1b. Poetry** | [pyproject.toml](pyproject.toml) (`package-mode = false`) | Done |
| **1c. Docker** | [Dockerfile](Dockerfile); build **`linux/amd64`** on Apple Silicon | Done |
| **1d. Cloud Run Job** | [deploy/cloud_run_ingest.sh](deploy/cloud_run_ingest.sh) → Artifact Registry `kalshi/chess-ingest` | Done (job executes successfully) |

**Optional next (still step 1 ops):** [weekly Cloud Scheduler](deploy/README.md) · drop legacy `kalshi` dataset if unused · commit/push deploy script fixes.

**Legacy:** early loads may exist in dataset `kalshi` or `raw.markets` / `raw.trades`; current ingest uses **`raw.kalshi_chess_*`** only.

## Step 2 — dbt (later)

Models in **`staging`** (dedupe, types) and **`marts`** (analytics). Second Cloud Run Job image. Table DDL: [schema.sql](schema.sql).

## Step 3 — Airflow on Composer (later)

DAG: ingest job → dbt job (can replace Scheduler from step 1).

---

## Target architecture (full stack)

![Kalshi Market Data Pipeline (pet project)](docs/kalshi-market-data-pipeline.png)

**Legend:** solid lines — data flow; dashed blue — orchestration (`CloudRunExecuteJobOperator`); dashed yellow — container image pull from Artifact Registry.

**Today (step 1):** ingest Cloud Run Job → `raw.kalshi_chess_*`. Composer, dbt job, and `staging` / `marts` models are step 2+.
