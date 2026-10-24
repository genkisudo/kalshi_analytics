# Kalshi API — Pagination Guide

Reference for [extract_chess.py](extract_chess.py): `paginate()` keeps filters fixed, follows `cursor` until empty, uses `limit=1000` (`PAGE_LIMIT`).

Source: https://docs.kalshi.com/getting_started/pagination

## Overview

The Kalshi API uses cursor-based pagination to retrieve large datasets without returning everything in a single response.

Pagination is commonly used with endpoints such as `/markets`, `/events`, and `/series`.

Each response contains:

- **Data array:** Records returned for the current page.
- **Cursor:** A token used to request the next page.
- **Limit:** Maximum records returned per page (default: 100).

## How Cursor-Based Pagination Works

1. Send an initial API request without a cursor.
2. Process the records returned in the response.
3. Read the `cursor` field.
4. If the cursor contains a value, send another request using it.
5. Repeat until the cursor is `null` or empty.

Example:

```text
GET /markets?limit=100

GET /markets?limit=100&cursor=NEXT_CURSOR

GET /markets?limit=100&cursor=ANOTHER_CURSOR
```

When no next-page cursor is returned, pagination is complete.

## Pagination Parameters

| Parameter | Description |
|---|---|
| `cursor` | Token returned by the previous response that identifies the next page. |
| `limit` | Maximum records per page. Typically 1–100; default is 100. |

## Python Example

Retrieve every market belonging to a specific series.

```python
import requests

BASE_URL = "https://external-api.kalshi.com/trade-api/v2/markets"

def get_all_markets(series_ticker):
    markets = []
    cursor = None

    while True:
        params = {
            "series_ticker": series_ticker,
            "limit": 100,
        }

        if cursor:
            params["cursor"] = cursor

        response = requests.get(
            BASE_URL,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        page = data.get("markets", [])

        markets.extend(page)

        print(
            f"Fetched {len(page)} markets; "
            f"total: {len(markets)}"
        )

        cursor = data.get("cursor")

        if not cursor:
            break

    return markets


markets = get_all_markets("KXHIGHNY")

print(f"Total markets: {len(markets)}")
```

## JavaScript Example

```javascript
async function getAllMarkets(seriesTicker) {
  const markets = [];
  let cursor = null;

  const baseUrl =
    "https://external-api.kalshi.com/trade-api/v2/markets";

  while (true) {
    const url = new URL(baseUrl);

    url.searchParams.set("series_ticker", seriesTicker);
    url.searchParams.set("limit", "100");

    if (cursor) {
      url.searchParams.set("cursor", cursor);
    }

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    markets.push(...(data.markets ?? []));

    console.log(`Total markets fetched: ${markets.length}`);

    cursor = data.cursor;

    if (!cursor) {
      break;
    }
  }

  return markets;
}

getAllMarkets("KXHIGHNY")
  .then(markets => {
    console.log(`Total markets: ${markets.length}`);
  })
  .catch(console.error);
```

## Supported Endpoints

The following Kalshi API endpoints support cursor-based pagination:

| Endpoint | Purpose |
|---|---|
| `/markets` | Retrieve markets |
| `/events` | Retrieve events |
| `/series` | Retrieve series |
| `/markets/trades` | Retrieve trades |
| `/portfolio/history` | Retrieve portfolio history |
| `/portfolio/fills` | Retrieve fills |
| `/portfolio/orders` | Retrieve orders |

## Common Usage Patterns

### 1. Fetch Only Recent Items

If you only require a small number of records, specify a limit rather than retrieving every page.

```python
url = (
    "https://external-api.kalshi.com"
    "/trade-api/v2/markets?limit=10&status=open"
)
```

### 2. Apply Filters During Pagination

Filters can be combined with cursor pagination.

```python
params = {
    "series_ticker": "KXHIGHNY",
    "status": "open",
    "limit": 100,
}

if cursor:
    params["cursor"] = cursor
```

Keep the same filters throughout a pagination sequence.

### 3. Identify Newly Added Records

For incremental collection:

1. Save the first record's ID or timestamp after a successful fetch.
2. On the next run, begin fetching the latest records.
3. Continue through pages until the previously saved record appears.
4. Treat records preceding that record as newly observed.

This pattern assumes the endpoint provides a suitable, consistent ordering.

## Best Practices

### Rate Limits

Multiple page requests may consume API rate-limit capacity.

For large collections, implement request throttling and retry handling where appropriate.

### Page Size

Use `limit=100` when collecting large datasets, unless a smaller limit is more suitable.

### Local Caching

Persist downloaded records to avoid unnecessary repeat requests.

### Changing Data

Records can be added or modified while pagination is in progress.

If data consistency matters, implement deduplication and periodic refreshes.

### Error Handling

Production implementations should:

- Check HTTP response status codes.
- Handle network timeouts.
- Retry temporary failures with backoff.
- Persist progress when processing many pages.
- Avoid silently treating failed requests as the end of pagination.

## Quick Reference

**Base URL**

```text
https://external-api.kalshi.com/trade-api/v2
```

**First request**

```http
GET /markets?limit=100
```

**Next page**

```http
GET /markets?limit=100&cursor=NEXT_CURSOR
```

**Completion condition**

Stop requesting additional pages when the returned cursor is null or empty.

## References

- [Understanding Pagination](https://docs.kalshi.com/getting_started/pagination)
- [Kalshi API Documentation](https://docs.kalshi.com/)
