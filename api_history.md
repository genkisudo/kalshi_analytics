# Kalshi API — Historical Data Guide

Reference for [extract_chess.py](extract_chess.py): `cutoff_unix()`, `/historical/markets`, `/historical/trades`, and one-second overlap at `trades_created_ts`.

Source: https://docs.kalshi.com/getting_started/historical_data

## Overview

Kalshi separates exchange data into two storage tiers:

1. **Live API:** Current and recent exchange data.
2. **Historical API:** Older records that have been moved out of the live dataset.

This architecture keeps live API requests fast while preserving access to historical records.

Data types affected by this partitioning include:

- Markets
- Market candlesticks
- Trades
- Orders
- Market positions

**Important:** Historical events and series remain accessible through their original endpoints.

## How Historical Data Works

Kalshi exposes cutoff timestamps that determine which records belong to historical storage.

Retrieve these timestamps using:

```http
GET /historical/cutoff
```

Cutoffs are updated periodically and move forward over time.

Each data category has its own cutoff timestamp.

Do not assume all data types share the same historical window.

### Position Archival Exception

Positions use a buffered, whole-event archival process.

A settled position may remain available through the live API even after its last-update timestamp is older than the published cutoff.

It becomes available through the historical API only after the associated event completes its archival handoff.

For complete position history, query both the live and historical endpoints.

## Cutoff Timestamps

| Field | Partitioned By | Description |
|---|---|---|
| `market_settled_ts` | Market settlement time | Markets and candlesticks settled before this timestamp are available only through historical endpoints. |
| `trades_created_ts` | Trade execution time | Older trades and user fills are available only through historical endpoints. |
| `orders_updated_ts` | Order cancellation or execution time | Canceled or fully executed orders older than this timestamp are historical. |
| `market_positions_last_updated_ts` | Position last-update time | Backfill horizon for settled positions, not the exact time of archival. |

### Important Rules

**Markets**

Markets settled before `market_settled_ts` must be retrieved using the historical API.

**Trades and fills**

Trades older than `trades_created_ts` must be retrieved using:

- `GET /historical/trades` for market-wide trades.
- `GET /historical/fills` for user-specific fills.

**Orders**

Canceled or fully executed orders older than `orders_updated_ts` are available through the historical orders endpoint.

Resting orders remain available through the live portfolio orders endpoint regardless of cutoff.

**Positions**

Unsettled positions always remain available through the live positions endpoint.

Settled positions may exist in the live dataset until their entire event has completed archival.

Use the `settlement_status` parameter:

| Value | Behavior |
|---|---|
| `unsettled` | Return unsettled positions; default behavior |
| `settled` | Return settled positions still in live storage |
| `all` | Return both settled and unsettled live positions |

Archived positions must be requested separately.

## Historical API Endpoints

| Endpoint | Description |
|---|---|
| `GET /historical/cutoff` | Retrieve current cutoff timestamps |
| `GET /historical/markets` | List archived settled markets |
| `GET /historical/markets/{ticker}` | Retrieve a single historical market |
| `GET /historical/markets/{ticker}/candlesticks` | Retrieve historical market candlesticks |
| `GET /historical/trades` | Retrieve archived market-wide trades |
| `GET /historical/fills` | Retrieve archived user-specific fills |
| `GET /historical/orders` | Retrieve archived canceled or executed orders |
| `GET /historical/positions` | Retrieve archived settled positions |

## Impact on Live API Endpoints

Once records move into historical storage, they may no longer appear in the corresponding live API endpoints.

| Live Endpoint | Cutoff Field | Impact |
|---|---|---|
| `GET /markets` | `market_settled_ts` | Older settled markets are excluded |
| `GET /markets/{ticker}` | `market_settled_ts` | Older settled markets are unavailable |
| Market candlestick endpoints | `market_settled_ts` | Candlesticks for archived markets move to historical storage |
| `GET /events?with_nested_markets=true` | `market_settled_ts` | Archived markets are excluded from nested market results |
| `GET /markets/trades` | `trades_created_ts` | Older trades are excluded |
| `GET /portfolio/fills` | `trades_created_ts` | Older user fills are excluded |
| `GET /portfolio/orders` | `orders_updated_ts` | Older completed/canceled orders are excluded |
| `GET /portfolio/positions` | `market_positions_last_updated_ts` | Archived settled positions are excluded after their event handoff |

### Exceptions

- Active orders remain accessible through `/portfolio/orders`.
- Unsettled positions remain accessible through `/portfolio/positions`.
- Settled positions awaiting archival can remain accessible through `/portfolio/positions?settlement_status=settled`.
- Events and series remain accessible through their original endpoints.

## Migration Guide

Applications requiring complete exchange history should query both live and historical storage.

### Step 1 — Retrieve Cutoff Timestamps

```http
GET /historical/cutoff
```

Use the returned timestamps to understand the historical boundaries for each data category.

### Step 2 — Query the Appropriate Endpoints

For markets:

```http
GET /markets
GET /historical/markets
```

For trades:

```http
GET /markets/trades
GET /historical/trades
```

For user fills:

```http
GET /portfolio/fills
GET /historical/fills
```

For orders:

```http
GET /portfolio/orders
GET /historical/orders
```

For positions:

```http
GET /portfolio/positions?settlement_status=all&subaccount=0
GET /historical/positions?subaccount=0
```

**Important:** Both position endpoints default to subaccount 0.

Repeat requests for every subaccount whose positions you need.

### Step 3 — Combine and Deduplicate Results

When building complete historical datasets:

1. Retrieve all pages from the live endpoint.
2. Retrieve all pages from the historical endpoint.
3. Combine the returned records.
4. Deduplicate overlapping records.
5. Reconcile records near archival cutoffs if exact completeness is required.

For positions, deduplicate using:

```text
(subaccount, ticker)
```

### Why Query Live Positions First?

Position records move from live storage into historical storage.

Reading the live endpoint first reduces the risk of missing a position during an archival handoff.

However, the two API requests do not represent a single atomic snapshot.

An overlap may also persist if an archival job stops after making a historical copy visible but before removing the live copy.

For accurate reconciliation, repeat the comparison when necessary.

## Settlement Data Limitation

The following endpoint returns settled positions still present in live storage:

```http
GET /portfolio/settlements
```

Once positions are archived, their information becomes available through:

```http
GET /historical/positions
```

Historical positions provide:

- Position information
- Realized profit and loss
- Fee data

**Limitation:** There is currently no historical endpoint exposing exactly the same settlement-record fields as `GET /portfolio/settlements`.

Applications relying on those specific settlement records should account for this difference.

## Pagination

Historical API endpoints support the same cursor-based pagination mechanism as live endpoints.

Example:

```http
GET /historical/markets?limit=100
```

For subsequent pages:

```http
GET /historical/markets?limit=100&cursor=NEXT_CURSOR
```

Continue requesting pages until no next-page cursor is returned.

See:

https://docs.kalshi.com/getting_started/pagination

## Implementation Best Practices

### 1. Do Not Hardcode Cutoff Dates

Retrieve current cutoff timestamps dynamically.

Kalshi advances these timestamps over time.

### 2. Maintain Separate Live and Historical Queries

For full historical coverage, use both APIs rather than assuming the live API contains all records.

### 3. Implement Cursor Pagination

Historical datasets may contain large numbers of records.

Process results page by page.

### 4. Deduplicate Overlapping Positions

Position archival uses a buffered handoff.

Use the combination of subaccount and ticker as the reconciliation key.

### 5. Account for Data Movement During Requests

Records may move between live and historical storage while requests are running.

Repeated reconciliation may be needed for exact completeness.

### 6. Preserve Relevant Historical Records

If your application depends on settlement-record fields not available in historical endpoints, collect and persist them before they disappear from live storage.

## Quick Reference

**API Base URL**

```text
https://external-api.kalshi.com/trade-api/v2
```

**Get historical cutoffs**

```http
GET /historical/cutoff
```

**Get archived markets**

```http
GET /historical/markets
```

**Get archived market trades**

```http
GET /historical/trades
```

**Get archived user fills**

```http
GET /historical/fills
```

**Get archived orders**

```http
GET /historical/orders
```

**Get archived positions**

```http
GET /historical/positions
```

**Get settled positions still in live storage**

```http
GET /portfolio/positions?settlement_status=settled
```

**Get all live positions for a subaccount**

```http
GET /portfolio/positions?settlement_status=all&subaccount=0
```

## References

- [Kalshi Historical Data](https://docs.kalshi.com/getting_started/historical_data)
- [Kalshi Pagination](https://docs.kalshi.com/getting_started/pagination)
- [Kalshi API Documentation](https://docs.kalshi.com/)
