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

Models in **`staging`** (dedupe, types) and **`marts`** (analytics). Second Cloud Run Job image. See [bq_best_practices.md](bq_best_practices.md).

## Step 3 — Airflow on Composer (later)

DAG: ingest job → dbt job (can replace Scheduler from step 1).

---

## Target architecture (full stack)

```mermaid
graph TD
    classDef default fill:#fff,stroke:#333,stroke-width:1px;
    classDef api fill:#f3f4f6,stroke:#4b5563,stroke-width:1px;
    classDef airflow fill:#dbeafe,stroke:#3b82f6,stroke-width:1px;
    classDef compute fill:#d1fae5,stroke:#10b981,stroke-width:1px;
    classDef registry fill:#fef3c7,stroke:#f59e0b,stroke-width:1px;
    classDef bq fill:#f3e8ff,stroke:#8b5cf6,stroke-width:1px;
    classDef noteBox fill:#fee2e2,stroke:#ef4444,stroke-width:1px;

    API["<b>Kalshi REST API</b><br/>Market data endpoints<br/>(markets, events, trades)<br/>HTTPS / JSON"]:::api

    Airflow["<b>Airflow on Cloud Composer (managed)</b><br/>Orchestration: schedule, order, retries, dependencies<br/>DAG: ingest -> dbt run -> dbt test"]:::airflow

    IngestJob["<b>Cloud Run Job</b><br/>chess-ingest<br/>(Poetry, Docker)"]:::compute
    DbtJob["<b>Cloud Run Job</b><br/>dbt core CLI (Poetry, Docker)<br/>Compiles SQL only, moves no data"]:::compute

    Registry["<b>Artifact Registry</b><br/>kalshi/chess-ingest"]:::registry

    subgraph BigQuery ["BigQuery (executes the SQL, does the processing)"]
        Raw["raw.kalshi_chess_*"]:::bq
        Staging["staging<br/>(dbt)"]:::bq
        Marts["marts<br/>(dbt)"]:::bq
    end

    Note["<b>Self-hosted on managed services</b><br/><b>You own:</b> dbt project, Docker image, DAGs, deployment<br/><b>Google owns:</b> servers under Cloud Run, Composer, BigQuery"]:::noteBox

    API --> IngestJob
    IngestJob -->|load| Raw
    Raw --> Staging
    Staging --> Marts
    DbtJob -->|compiled SQL pushed down| BigQuery

    Airflow -.->|CloudRunExecuteJobOperator (ingest)| IngestJob
    Airflow -.->|CloudRunExecuteJobOperator (dbt), after ingest succeeds| DbtJob

    Registry -.->|image| DbtJob
    Registry -.->|image| IngestJob
```
