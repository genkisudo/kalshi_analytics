# Kalshi analytics — roadmap

## Step 1 — Containerized ingest to BigQuery `raw` (current)

Land Kalshi chess API data in BigQuery. dbt and Airflow are **step 2+**.

| Substep | What | Status |
| --- | --- | --- |
| **1a. Raw dataset** | Datasets `raw` / `staging` / `marts`; ingest → `raw.kalshi_chess_markets`, `raw.kalshi_chess_trades` ([schema.sql](schema.sql), [bq_best_practices.md](bq_best_practices.md)) | Run DDL once; staging/marts empty until dbt |
| **1b. Poetry** | Dependencies in [pyproject.toml](pyproject.toml) | Ready — `poetry install` |
| **1c. Docker** | [Dockerfile](Dockerfile) runs `extract_chess.py --load` | Ready — `docker build` |
| **1d. Cloud Run Job** | [deploy/cloud_run_ingest.sh](deploy/cloud_run_ingest.sh) → Artifact Registry + job `chess-ingest` | Ready — run deploy script, then `gcloud run jobs execute` |

**Done earlier (prototype):** local `extract_chess.py --load` into legacy dataset `kalshi` (704 markets / 258 trades). New loads should target **`raw`** after DDL.

## Step 2 — dbt (later)

`staging` / `marts` in BigQuery; dbt in a second Cloud Run Job image.

## Step 3 — Airflow on Composer (later)

DAG: ingest job → dbt job.

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

    IngestJob["<b>Cloud Run Job</b><br/>Python ingestion<br/>(Poetry, Docker)"]:::compute
    DbtJob["<b>Cloud Run Job</b><br/>dbt core CLI (Poetry, Docker)<br/>Compiles SQL only, moves no data"]:::compute

    Registry["<b>Artifact Registry</b><br/>(Docker images)"]:::registry

    subgraph BigQuery ["BigQuery (executes the SQL, does the processing)"]
        Raw["raw<br/>(landed API data)"]:::bq
        Staging["staging<br/>(dbt: clean, typed)"]:::bq
        Marts["marts<br/>(dbt: analytics-ready)"]:::bq
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
