# Cloud Run Job — chess ingest

Container runs `extract_chess.py --load` (Kalshi API → JSONL in `/app/data` → append **`raw.kalshi_chess_markets`** / **`raw.kalshi_chess_trades`**).

Job name: **`chess-ingest`**. Region: **`us-central1`**. Image: **`us-central1-docker.pkg.dev/kalshi-analytics-512607/kalshi/chess-ingest:latest`**.

## One-time BigQuery

Creates datasets `raw`, `staging`, `marts` and raw chess tables:

```bash
bq query --use_legacy_sql=false --project_id=kalshi-analytics-512607 < schema.sql
bq ls kalshi-analytics-512607:raw
```

## Deploy or update the job

From repo root. **Docker Desktop must be running.**

```bash
chmod +x deploy/cloud_run_ingest.sh
./deploy/cloud_run_ingest.sh
```

The script:

1. Enables Run, Artifact Registry, BigQuery APIs.
2. **`docker build --platform linux/amd64`** and **`docker push`** (required on Apple Silicon — arm-only images fail on Cloud Run with an amd64 manifest error).
3. Ensures service account **`chess-ingest@kalshi-analytics-512607.iam.gserviceaccount.com`** exists; waits for propagation; grants **BigQuery Data Editor** and **Job User** (idempotent).
4. Creates or updates Cloud Run Job **`chess-ingest`**.

It does **not** execute the job or configure a schedule.

Override defaults: `REGION=us-east1 ./deploy/cloud_run_ingest.sh`.

## Execute manually

```bash
gcloud run jobs execute chess-ingest --region=us-central1 --wait
```

Logs: [Cloud Run → Jobs → chess-ingest → Executions](https://console.cloud.google.com/run/jobs?project=kalshi-analytics-512607).

Verify BigQuery:

```bash
bq query --use_legacy_sql=false '
SELECT COUNT(*) FROM `kalshi-analytics-512607.raw.kalshi_chess_markets`;
'
```

## Weekly schedule (optional)

No built-in cron. Example: Monday 06:00 UTC via Cloud Scheduler — see commands below. Re-run `./deploy/cloud_run_ingest.sh` only when **code or Dockerfile** changes.

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

## IAM troubleshooting

**Roles needed on the job service account (project level):**

- `roles/bigquery.dataEditor`
- `roles/bigquery.jobUser`

Check:

```bash
gcloud projects get-iam-policy kalshi-analytics-512607 \
  --flatten="bindings[].members" \
  --filter="bindings.members:chess-ingest@kalshi-analytics-512607.iam.gserviceaccount.com" \
  --format="table(bindings.role)"
```

**Console:** [IAM](https://console.cloud.google.com/iam-admin/iam?project=kalshi-analytics-512607) → filter `chess-ingest` → **Edit principal** (pencil) → add missing roles. If **Grant access** says *principal already exists*, edit the existing row instead.

**CLI `Service account does not exist` right after create:** wait ~1 minute; re-run `./deploy/cloud_run_ingest.sh` (image may already be pushed).

**Cloud Run `must support amd64/linux`:** rebuild with `--platform linux/amd64` (the deploy script does this).

## Remove legacy BigQuery data (optional)

Early loads may be in dataset **`kalshi`** or **`raw.markets`** / **`raw.trades`**.

```bash
bq rm -r -f -d kalshi-analytics-512607:kalshi
bq rm -f -t kalshi-analytics-512607:raw.markets
bq rm -f -t kalshi-analytics-512607:raw.trades
```

## Manual job create (if deploy stopped before job create)

```bash
PROJECT_ID=kalshi-analytics-512607
SA=chess-ingest@${PROJECT_ID}.iam.gserviceaccount.com
IMAGE=us-central1-docker.pkg.dev/${PROJECT_ID}/kalshi/chess-ingest:latest

gcloud run jobs create chess-ingest --region=us-central1 \
  --image="${IMAGE}" --service-account="${SA}" \
  --task-timeout=3600 --max-retries=1 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
```

Use `gcloud run jobs update` if the job already exists.
