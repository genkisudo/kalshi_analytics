"""Kalshi chess markets and public trades -> JSONL -> BigQuery load job.

Default run writes local JSONL only. Pass --load to append those files to BigQuery
with a NEWLINE_DELIMITED_JSON load job (the HTTP batch load, not streaming inserts).
Create the tables from schema.sql first. ``--load`` needs ``google-cloud-bigquery``
and Application Default Credentials. This script does not call GCP unless --load is set.

Window: markets whose created_time is inside the last --days (default 7). Public
trades are then read for those markets over the same window. Settled markets older
than /historical/cutoff ``market_settled_ts`` are read from /historical/markets, and
trades older than ``trades_created_ts`` from /historical/trades. A 7-day window that
starts after the cutoff uses the live endpoints only.

Series: Sports series tagged Chess, plus Sports series whose title contains "chess"
(a few chess series are untagged).
"""
import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"
OUT_DIR = Path("data")
DATASET = "raw"
TABLE_MARKETS = "kalshi_chess_markets"
TABLE_TRADES = "kalshi_chess_trades"
PAGE_LIMIT = 1000
DEFAULT_DAYS = 7

MARKET_FIELDS = [
    "ticker", "event_ticker", "market_type", "title", "yes_sub_title", "no_sub_title",
    "status", "result", "expiration_value", "created_time", "updated_time", "open_time",
    "close_time", "expected_expiration_time", "latest_expiration_time", "settlement_ts",
    "last_price_dollars", "yes_bid_dollars", "yes_ask_dollars", "no_bid_dollars",
    "no_ask_dollars", "volume_fp", "volume_24h_fp", "open_interest_fp",
    "settlement_value_dollars", "floor_strike",
]
TRADE_FIELDS = [
    "trade_id", "ticker", "count_fp", "yes_price_dollars", "no_price_dollars",
    "taker_outcome_side", "taker_book_side", "taker_side", "created_time", "is_block_trade",
]


def get(path, **params):
    """Perform one GET request against the Kalshi trade API.

    Args:
        path: Path suffix appended to ``BASE_URL`` (e.g. ``/markets``).
        **params: Query parameters; keys with value ``None`` are omitted.

    Returns:
        Parsed JSON response body as a dict.

    Raises:
        requests.HTTPError: On non-429 HTTP errors after ``raise_for_status``.
        requests.HTTPError: On 429 if all retry attempts are exhausted.
    """
    clean = {key: value for key, value in params.items() if value is not None}
    response = None
    for attempt in range(5):
        response = requests.get(f"{BASE_URL}{path}", params=clean, timeout=30)
        if response.status_code != 429:
            response.raise_for_status()
            return response.json()
        time.sleep(2 ** attempt)
    response.raise_for_status()
    return {}


def paginate(path, record_key, **params):
    """Yield all records from a cursor-paginated Kalshi endpoint.

    See api_pagination.md: filters stay constant across pages; stop when the cursor
    is empty or repeats.

    Args:
        path: API path (e.g. ``/markets``).
        record_key: Key in each response page holding the record list (e.g. ``markets``).
        **params: Query filters; ``limit`` is set to ``PAGE_LIMIT``.

    Yields:
        Individual records from successive pages.
    """
    params = dict(params, limit=PAGE_LIMIT)
    seen_cursors = set()
    cursor = None
    while True:
        page = get(path, cursor=cursor, **params)
        yield from page.get(record_key) or []
        cursor = page.get("cursor") or ""
        if not cursor or cursor in seen_cursors:
            return
        seen_cursors.add(cursor)


def parse_ts(value):
    """Parse an ISO-8601 timestamp string into a timezone-aware datetime.

    Args:
        value: Timestamp string, or empty/None.

    Returns:
        Parsed datetime, or None if ``value`` is falsy.
    """
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def to_unix(value):
    """Convert a datetime or ISO string to Unix seconds (integer).

    Args:
        value: ``datetime`` instance or ISO-8601 string.

    Returns:
        Integer Unix timestamp.
    """
    parsed = parse_ts(value) if isinstance(value, str) else value
    return int(parsed.timestamp())


def in_window(iso_time, start, end):
    """Return whether ``iso_time`` lies strictly between ``start`` and ``end``.

    Args:
        iso_time: Market or trade time as an ISO string.
        start: Window start (aware datetime).
        end: Window end (aware datetime).

    Returns:
        True if ``start < parsed < end``; False if unparseable or outside.
    """
    parsed = parse_ts(iso_time)
    return parsed is not None and start < parsed < end


def list_chess_series():
    """Discover Kalshi series tickers that represent chess markets.

    Includes Sports series with the Chess tag and untagged Sports series whose
    title contains "chess" (case-insensitive).

    Returns:
        Dict mapping series ticker to the series object from the API.
    """
    selected = {}
    for series in get("/series", category="Sports", tags="Chess").get("series", []):
        selected[series["ticker"]] = series
    for series in get("/series", category="Sports").get("series", []):
        title = (series.get("title") or "").lower()
        ticker = series.get("ticker")
        if ticker and ticker not in selected and "chess" in title:
            selected[ticker] = series
    return selected


def has_volume(market):
    """Return whether the market has strictly positive ``volume_fp``.

    Args:
        market: Market dict from the Kalshi API.

    Returns:
        False if volume is missing or zero; True if positive. Unparseable values
        are treated as having volume so trades are not skipped silently.
    """
    raw = market.get("volume_fp")
    if raw in (None, ""):
        return False
    try:
        return Decimal(str(raw)) > 0
    except InvalidOperation:
        return True


def cutoff_unix():
    """Fetch live vs historical storage boundaries from Kalshi.

    Returns:
        Dict with keys ``markets`` and ``trades``, each an int Unix timestamp
        from ``market_settled_ts`` and ``trades_created_ts`` respectively.
    """
    payload = get("/historical/cutoff")
    return {
        "markets": to_unix(payload["market_settled_ts"]),
        "trades": to_unix(payload["trades_created_ts"]),
    }


def extract_markets(series_ticker, start, end, cutoffs):
    """Collect markets for one series whose created_time falls in the window.

    Uses live ``/markets`` with created-time filters. When the window extends
    before the market archival cutoff, also scans ``/historical/markets`` and
    filters by ``created_time`` client-side.

    Args:
        series_ticker: Kalshi series ticker.
        start: Window start (aware datetime).
        end: Window end (aware datetime).
        cutoffs: Dict from ``cutoff_unix()`` with ``markets`` and ``trades`` keys.

    Returns:
        Dict mapping market ticker to ``(source, market)`` where source is
        ``live`` or ``historical``.
    """
    markets = {}
    for market in paginate(
        "/markets",
        "markets",
        series_ticker=series_ticker,
        min_created_ts=to_unix(start),
        max_created_ts=to_unix(end),
    ):
        ticker = market.get("ticker")
        if ticker:
            markets[ticker] = ("live", market)

    if to_unix(start) < cutoffs["markets"]:
        for market in paginate("/historical/markets", "markets", series_ticker=series_ticker):
            ticker = market.get("ticker")
            if ticker and ticker not in markets and in_window(market.get("created_time"), start, end):
                markets[ticker] = ("historical", market)
    return markets


def iter_trades(market_ticker, start_unix, end_unix, cutoffs):
    """Yield public trades for one market, routing across live and historical APIs.

    Overlaps live and historical requests by one second at ``trades_created_ts``
    so a fill on the cutoff instant is not dropped. Caller dedupes by ``trade_id``.

    Args:
        market_ticker: Market ticker.
        start_unix: Trade window start (Unix seconds).
        end_unix: Trade window end (Unix seconds).
        cutoffs: Dict from ``cutoff_unix()``.

    Yields:
        Tuples of ``(source, trade)`` where source is ``live`` or ``historical``.
    """
    trade_cutoff = cutoffs["trades"]
    ranges = []
    if end_unix >= trade_cutoff:
        live_min = start_unix if start_unix >= trade_cutoff else trade_cutoff - 1
        ranges.append(("/markets/trades", "live", live_min, end_unix))
    if start_unix < trade_cutoff:
        hist_max = end_unix if end_unix <= trade_cutoff else trade_cutoff + 1
        ranges.append(("/historical/trades", "historical", start_unix, hist_max))
    for path, source, min_ts, max_ts in ranges:
        if min_ts >= max_ts:
            continue
        for trade in paginate(
            path,
            "trades",
            ticker=market_ticker,
            min_ts=min_ts,
            max_ts=max_ts,
        ):
            yield source, trade


def transform_market(market, series_ticker, category, source, ingested_at):
    """Build one BigQuery-ready market row from an API market object.

    Args:
        market: Raw market dict from Kalshi.
        series_ticker: Parent series ticker.
        category: Series category (e.g. Sports).
        source: ``live`` or ``historical``.
        ingested_at: ISO timestamp for this extract run.

    Returns:
        Flat dict aligned with ``MARKET_FIELDS`` plus metadata columns.
    """
    row = {field: market.get(field) for field in MARKET_FIELDS}
    strike = market.get("custom_strike")
    row["custom_strike"] = json.dumps(strike, separators=(",", ":")) if strike else None
    row["series_ticker"] = series_ticker
    row["category"] = category
    row["_source"] = source
    row["_ingested_at"] = ingested_at
    return row


def transform_trade(trade, series_ticker, event_ticker, source, ingested_at):
    """Build one BigQuery-ready trade row from an API trade object.

    Args:
        trade: Raw trade dict from Kalshi.
        series_ticker: Parent series ticker.
        event_ticker: Parent event ticker from the market.
        source: ``live`` or ``historical``.
        ingested_at: ISO timestamp for this extract run.

    Returns:
        Flat dict aligned with ``TRADE_FIELDS`` plus metadata columns.
    """
    row = {field: trade.get(field) for field in TRADE_FIELDS}
    row["series_ticker"] = series_ticker
    row["event_ticker"] = event_ticker
    row["_source"] = source
    row["_ingested_at"] = ingested_at
    return row


def write_jsonl(rows, path):
    """Write rows as newline-delimited JSON to ``path``.

    Args:
        rows: Iterable of JSON-serializable dicts.
        path: Output file path; parent directory is created if needed.
    """
    path.parent.mkdir(exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _schema(columns):
    """Build a list of BigQuery ``SchemaField`` instances from column tuples.

    Args:
        columns: Sequence of ``(name, field_type, mode)`` tuples.

    Returns:
        List of ``google.cloud.bigquery.SchemaField`` objects.
    """
    from google.cloud import bigquery

    fields = []
    for name, field_type, mode in columns:
        fields.append(bigquery.SchemaField(name, field_type, mode=mode))
    return fields


def market_schema():
    """Return the BigQuery schema for the markets load job.

    Returns:
        Schema field list matching ``schema.sql`` / market JSONL rows.
    """
    numeric = [
        "last_price_dollars", "yes_bid_dollars", "yes_ask_dollars", "no_bid_dollars",
        "no_ask_dollars", "volume_fp", "volume_24h_fp", "open_interest_fp",
        "settlement_value_dollars",
    ]
    timestamps = [
        "created_time", "updated_time", "open_time", "close_time",
        "expected_expiration_time", "latest_expiration_time", "settlement_ts",
    ]
    strings = [
        "series_ticker", "category", "event_ticker", "market_type", "title",
        "yes_sub_title", "no_sub_title", "status", "result", "expiration_value",
        "custom_strike", "_source",
    ]
    columns = [("ticker", "STRING", "REQUIRED")]
    columns += [(name, "STRING", "NULLABLE") for name in strings]
    columns += [(name, "TIMESTAMP", "NULLABLE") for name in timestamps]
    columns += [(name, "NUMERIC", "NULLABLE") for name in numeric]
    columns += [("floor_strike", "FLOAT64", "NULLABLE"), ("_ingested_at", "TIMESTAMP", "REQUIRED")]
    return _schema(columns)


def trade_schema():
    """Return the BigQuery schema for the trades load job.

    Returns:
        Schema field list matching ``schema.sql`` / trade JSONL rows.
    """
    columns = [
        ("trade_id", "STRING", "REQUIRED"),
        ("ticker", "STRING", "REQUIRED"),
        ("series_ticker", "STRING", "NULLABLE"),
        ("event_ticker", "STRING", "NULLABLE"),
        ("count_fp", "NUMERIC", "NULLABLE"),
        ("yes_price_dollars", "NUMERIC", "NULLABLE"),
        ("no_price_dollars", "NUMERIC", "NULLABLE"),
        ("taker_outcome_side", "STRING", "NULLABLE"),
        ("taker_book_side", "STRING", "NULLABLE"),
        ("taker_side", "STRING", "NULLABLE"),
        ("created_time", "TIMESTAMP", "NULLABLE"),
        ("is_block_trade", "BOOL", "NULLABLE"),
        ("_source", "STRING", "NULLABLE"),
        ("_ingested_at", "TIMESTAMP", "REQUIRED"),
    ]
    return _schema(columns)


def load_jsonl(path, table_id, schema, project):
    """Append one JSONL file to an existing BigQuery table via a load job.

    Args:
        path: Local newline-delimited JSON file.
        table_id: Fully qualified table id ``project.dataset.table``.
        schema: BigQuery schema field list.
        project: GCP project id for the BigQuery client.

    Raises:
        google.cloud.exceptions.GoogleCloudError: If the load job fails.
    """
    from google.cloud import bigquery

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        create_disposition=bigquery.CreateDisposition.CREATE_NEVER,
    )
    client = bigquery.Client(project=project)
    with path.open("rb") as handle:
        job = client.load_table_from_file(handle, table_id, job_config=job_config)
    job.result()
    print(f"loaded {job.output_rows} rows into {table_id}")


def load_to_bigquery(market_path, trade_path, project):
    """Load market and trade JSONL files produced by ``extract``.

    Args:
        market_path: Path to markets JSONL.
        trade_path: Path to trades JSONL; skipped if the file is empty.
        project: GCP project id.

    Raises:
        SystemExit: If ``project`` is empty.
    """
    if not project:
        raise SystemExit("Pass --project with your GCP project id before --load.")
    load_jsonl(market_path, f"{project}.{DATASET}.{TABLE_MARKETS}", market_schema(), project)
    if trade_path.stat().st_size == 0:
        print(f"no trades to load into {project}.{DATASET}.{TABLE_TRADES}")
        return
    load_jsonl(trade_path, f"{project}.{DATASET}.{TABLE_TRADES}", trade_schema(), project)


def extract(days):
    """Run the full Kalshi chess extract for the last ``days`` calendar days.

    Args:
        days: Lookback length; markets are filtered by ``created_time`` in
            ``(now - days, now)``. Trades use the same Unix window per market.

    Returns:
        Tuple ``(market_path, trade_path)`` of written JSONL files under ``OUT_DIR``.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    ingested_at = now.isoformat()
    cutoffs = cutoff_unix()
    series = list_chess_series()
    print(f"{len(series)} chess series | window {start.isoformat()} -> {now.isoformat()}", flush=True)

    market_rows = []
    trade_rows = []
    seen_trades = set()
    start_unix, end_unix = to_unix(start), to_unix(now)

    for index, (series_ticker, meta) in enumerate(series.items(), 1):
        found = extract_markets(series_ticker, start, now, cutoffs)
        series_trades = 0
        for source, market in found.values():
            market_rows.append(
                transform_market(market, series_ticker, meta.get("category"), source, ingested_at)
            )
            if not has_volume(market):
                continue
            for trade_source, trade in iter_trades(market["ticker"], start_unix, end_unix, cutoffs):
                trade_id = trade.get("trade_id")
                if not trade_id or trade_id in seen_trades:
                    continue
                seen_trades.add(trade_id)
                trade_rows.append(
                    transform_trade(
                        trade,
                        series_ticker,
                        market.get("event_ticker"),
                        trade_source,
                        ingested_at,
                    )
                )
                series_trades += 1
        if found:
            print(
                f"[{index}/{len(series)}] {series_ticker}: {len(found)} markets, "
                f"{series_trades} trades",
                flush=True,
            )

    stamp = f"{now:%Y%m%dT%H%M%SZ}"
    market_path = OUT_DIR / f"chess_markets_{stamp}.jsonl"
    trade_path = OUT_DIR / f"chess_trades_{stamp}.jsonl"
    write_jsonl(market_rows, market_path)
    write_jsonl(trade_rows, trade_path)
    print(f"wrote {len(market_rows)} markets -> {market_path}")
    print(f"wrote {len(trade_rows)} trades -> {trade_path}")
    return market_path, trade_path


def main():
    """Parse CLI arguments, run extract, and optionally load to BigQuery."""
    parser = argparse.ArgumentParser(description="Extract Kalshi chess markets and public trades.")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="Created-time lookback. Default 7.")
    parser.add_argument("--load", action="store_true", help="Append the JSONL files to BigQuery.")
    parser.add_argument(
        "--project",
        default="kalshi-analytics-512607",
        help="GCP project id for --load.",
    )
    args = parser.parse_args()
    if args.days < 1:
        raise SystemExit("--days must be >= 1")

    market_path, trade_path = extract(args.days)
    if args.load:
        load_to_bigquery(market_path, trade_path, args.project)


if __name__ == "__main__":
    main()
