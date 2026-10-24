# Cloud Run Job — chess ingest

Container runs `extract_chess.py --load` (Kalshi API → JSONL → append `raw.kalshi_chess_markets` / `raw.kalshi_chess_trades`).

## Remove legacy BigQuery data (optional)

Prototype loads may exist in dataset `kalshi` or old `raw.markets` / `raw.trades`. **Deleting a dataset removes all tables inside it.**

List what you have:

```bash
bq ls --project_id=kalshi-analytics-512607
bq ls kalshi-analytics-512607:kalshi
bq ls kalshi-analytics-512607:raw
```

Drop entire legacy dataset (irreversible):

```bash
bq rm -r -f -d kalshi-analytics-512607:kalshi
```

Drop only old raw tables (keep `raw.kalshi_chess_*`):

```bash
bq rm -f -t kalshi-analytics-512607:raw.markets
bq rm -f -t kalshi-analytics-512607:raw.trades
```

Use the [BigQuery console](https://console.cloud.google.com/bigquery?project=kalshi-analytics-512607) if you prefer UI: select dataset/table → Delete.

## One-time BigQuery raw layer

```bash
bq query --use_legacy_sql=false --project_id=kalshi-analytics-512607 < schema.sql
```

## Deploy or update the job

From the repo root (Docker running locally):

```bash
chmod +x deploy/cloud_run_ingest.sh
./deploy/cloud_run_ingest.sh
```

Defaults: project `kalshi-analytics-512607`, region `us-central1`, job name `chess-ingest`. Override with env vars, e.g. `REGION=us-east1 ./deploy/cloud_run_ingest.sh`.

## What `cloud_run_ingest.sh` does

1. Enables APIs, ensures an Artifact Registry repo exists, **`docker build`** + **`docker push`** of your ingest image.
2. Creates **`chess-ingest`** service account (first run) with BigQuery load permissions.
3. **Creates or updates** the Cloud Run Job `chess-ingest` to run that image (`extract_chess.py --load`). It does **not** run the job or set a schedule.

## Execute manually (no schedule)

```bash
gcloud run jobs execute chess-ingest --region=us-central1 --wait
```

## Weekly schedule (Cloud Scheduler)

The job has **no built-in cron**; use Scheduler to call the Run Jobs API weekly (UTC Monday 06:00 example):

```bash
gcloud services enable cloudscheduler.googleapis.com

gcloud run jobs add-iam-policy-binding chess-ingest \
  --region=us-central1 \
  --member="serviceAccount:chess-ingest@kalshi-analytics-512607.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

gcloud scheduler jobs create http chess-ingest-weekly \
  --location=us-central1 \
  --schedule="0 6 * * 1" \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/kalshi-analytics-512607/jobs/chess-ingest:run" \
  --http-method=POST \
  --oauth-service-account-email="chess-ingest@kalshi-analytics-512607.iam.gserviceaccount.com"
```

Re-deploy the image with `./deploy/cloud_run_ingest.sh` only when Python/Docker code changes—not on every scheduled run.

Logs: Cloud Console → Cloud Run → Jobs → chess-ingest → Executions.

## IAM

The script creates service account `chess-ingest@…` with BigQuery Data Editor and Job User. The job identity is used automatically inside the container (no `application-default login` in Cloud Run).
