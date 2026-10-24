"""Step 1: markets created in the last 24h for a few chosen categories -> local JSONL -> dummy load.

Two-step extract: /series (filter by category/tag) -> /markets per series ticker.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"
OUT_DIR = Path("data")
WINDOW_SECONDS = 24 * 60 * 60

# (category, tags). tags=None keeps the whole category; otherwise a series needs at least one of them.
SERIES_FILTERS = [
    ("Climate and Weather", {  # 1. weather hedging
        "Daily temperature", "Hourly temperature", "Snow and rain",
        "Ski Resorts", "Hurricanes", "Heatwaves",
    }),
    ("Commodities", None),                # 2. commodities hub
    ("Economics", {"Oil and energy"}),    # 3. retail gas prices
]

# Columns that mirror schema.sql. Prices/counts stay strings here; BigQuery casts them (NUMERIC).
FIELDS = [
    "ticker", "event_ticker", "market_type", "title", "status",
    "created_time", "open_time", "close_time",
    "last_price_dollars", "volume_fp", "open_interest_fp", "floor_strike",
]


def get(path, **params):
    response = requests.get(f"{BASE_URL}{path}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def list_series():
    """Return {series_ticker: category} for every series matching SERIES_FILTERS."""
    selected = {}
    for category, tags in SERIES_FILTERS:
        for s in get("/series", category=category).get("series", []):
            if tags is None or tags & set(s.get("tags") or []):
                selected[s["ticker"]] = category
    return selected


def extract_series_markets(series_ticker, min_created_ts):
    """Page through /markets for one series until the cursor is empty (see api_pagination.md)."""
    markets, cursor = [], None
    while True:
        params = {"series_ticker": series_ticker, "min_created_ts": min_created_ts, "limit": 100}
        if cursor:
            params["cursor"] = cursor
        data = get("/markets", **params)
        markets.extend(data.get("markets", []))
        cursor = data.get("cursor")
        if not cursor:
            return markets


def transform(markets, series_ticker, category, ingested_at):
    """Keep only schema columns, add series info and ingestion metadata."""
    return [
        {
            **{f: m.get(f) for f in FIELDS},
            "series_ticker": series_ticker,
            "category": category,
            "_ingested_at": ingested_at,
        }
        for m in markets
    ]


def write_jsonl(rows, path):
    path.parent.mkdir(exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def load_to_bigquery(path, table_id="YOUR_PROJECT.kalshi.markets"):
    """DUMMY. Later: google-cloud-bigquery load_table_from_file with a JSON load job."""
    print(f"[dummy] would load {path} into {table_id}")


if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    min_created_ts = int(time.time()) - WINDOW_SECONDS

    series = list_series()
    print(f"{len(series)} series match the filters", flush=True)

    rows = []
    for i, (ticker, category) in enumerate(series.items(), 1):
        markets = extract_series_markets(ticker, min_created_ts)
        rows.extend(transform(markets, ticker, category, now.isoformat()))
        if markets:
            print(f"[{i}/{len(series)}] {ticker}: {len(markets)} markets | total {len(rows)}", flush=True)

    out_path = OUT_DIR / f"markets_{now:%Y%m%dT%H%M%SZ}.jsonl"
    write_jsonl(rows, out_path)
    print(f"wrote {len(rows)} rows -> {out_path}")

    load_to_bigquery(out_path)
