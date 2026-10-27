# dbt project: `kalshi_dbt`

Transforms `raw.kalshi_chess_*` (loaded by `extract_chess.py`) into clean tables in BigQuery. Uses **dbt-core** with the BigQuery adapter, installed through Poetry (dev group) at the repo root.

## Run it

Run from this folder, and always through Poetry (a separate dbt Fusion binary may be earlier on your `PATH`):

```bash
cd dbt
poetry run dbt debug                 # check profile + BigQuery connection
poetry run dbt build                 # run models and tests
poetry run dbt build --select stg_kalshi_chess_markets
```

Auth is gcloud ADC (`gcloud auth application-default login`). The profile is [profiles.yml](profiles.yml) in this folder, so dbt picks it up when you run from here; it holds no secrets. It builds into dataset `staging` in project `kalshi-analytics-512607`, location `US`.

## Layout

| Path | Role |
| --- | --- |
| [models/staging/_sources.yml](models/staging/_sources.yml) | Declares `raw.kalshi_chess_markets` / `raw.kalshi_chess_trades` as sources (`loaded_at_field: _ingested_at`) |
| [models/staging/stg_kalshi_chess_markets.sql](models/staging/stg_kalshi_chess_markets.sql) | One row per `ticker`, latest `_ingested_at` wins |
| [models/staging/stg_kalshi_chess_trades.sql](models/staging/stg_kalshi_chess_trades.sql) | One row per `trade_id`, latest `_ingested_at` wins |
| [models/staging/_models.yml](models/staging/_models.yml) | Model docs and tests (`unique`, `not_null`) |

Staging models are views (set in [dbt_project.yml](dbt_project.yml)).

## Status

- Staging models for markets and trades build.
- Tests exist for markets only. **Next step: add `unique` and `not_null` tests for `trade_id` on `stg_kalshi_chess_trades` in `_models.yml`.**
- `marts` models are not written yet.
