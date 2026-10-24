# BigQuery best practices (this project)

Medallion layout: datasets **`raw`**, **`staging`**, **`marts`** (layer-only). Table names carry the source domain, e.g. `raw.kalshi_chess_markets`, `staging.kalshi_chess_markets`, `marts.kalshi_chess_market_daily` (examples for dbt).

General query-performance notes below, mapped to how we use BigQuery here.

## Query performance

| Practice | How we use it |
| --- | --- |
| **Filter on partitioned columns** | `raw.kalshi_chess_*` tables are `PARTITION BY DATE(created_time)`. Ingest and analytics queries should include a `created_time` (or partition date) predicate. dbt models should partition on the same or a derived date where possible. |
| **Denormalizing data** | `raw` keeps API shape (markets + trades separate). **staging/marts** may denormalize (e.g. trade + market attributes) when it cuts join cost for frequent queries. |
| **Nested or repeated columns** | Not used in `raw` (flat JSONL load). Optional in marts for arrays (e.g. multiple strikes) if it avoids wide sparse tables. |
| **External data sources** | We do **not** query Kalshi from BigQuery external tables; ingest lands files via load jobs into `raw`. External tables are for other sources only. |
| **Reduce data before JOIN** | dbt: filter/partition prune in CTEs before joining markets ↔ trades; avoid `SELECT *` on full `raw` history. |
| **WITH clauses** | Treat CTEs as documentation, not reusable plans—BigQuery may re-evaluate. Prefer fewer, wider CTEs over deep chains on huge tables. |
| **Avoid oversharding** | Keep partition granularity at **day** on `created_time` unless row volume forces hour (unlikely for chess). |
| **Avoid JavaScript UDFs** | Use SQL (`SAFE_CAST`, `JSON_VALUE` on `custom_strike`) in dbt instead of JS UDFs. |
| **Approximate aggregation (HLL++)** | Use in **marts** for distinct traders/volume dashboards when exact counts are not required. |
| **Order last** | In heavy ad hoc SQL, apply `ORDER BY` only in the final SELECT (or omit for exports). |
| **Optimize join patterns** | When joining trades to markets, **markets first by row count** after filters, or use a pre-aggregated staging table as the large side per Google’s guidance. |

## Ingest-specific (step 1)

- **Clustering**: `raw.kalshi_chess_markets` clusters on `series_ticker`, `event_ticker`; trades on `ticker`—align filters with cluster keys when possible.
- **Append-only raw**: Each run adds rows; dedupe belongs in **staging** (`QUALIFY ROW_NUMBER() …`) not in the loader.
- **Location**: All datasets use `US` (see `schema.sql`)—keep Cloud Run job region compatible (e.g. `us-central1`).

## References

- [BigQuery optimization](https://cloud.google.com/bigquery/docs/best-practices-performance-overview)
- Project DDL: [schema.sql](schema.sql)
- Roadmap: [plan.md](plan.md)
