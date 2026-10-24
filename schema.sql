-- BigQuery DDL for chess ingestion (step 1).
-- Replace YOUR_PROJECT, then run this in the BigQuery console before `extract_chess.py --load`.
-- The loader uses a NEWLINE_DELIMITED_JSON load job (HTTP), WRITE_APPEND.
-- Fixed-point API values are JSON strings; the schema casts them to NUMERIC.
-- Each run appends a snapshot. A later dbt model should keep the latest row per ticker
-- and one row per trade_id.

CREATE SCHEMA IF NOT EXISTS `YOUR_PROJECT.kalshi` OPTIONS (location = 'US');

CREATE TABLE IF NOT EXISTS `YOUR_PROJECT.kalshi.markets` (
  ticker                    STRING NOT NULL,
  series_ticker             STRING,
  category                  STRING,
  event_ticker              STRING,
  market_type               STRING,
  title                     STRING,
  yes_sub_title             STRING,
  no_sub_title              STRING,
  status                    STRING,
  result                    STRING,
  expiration_value          STRING,
  created_time              TIMESTAMP,
  updated_time              TIMESTAMP,
  open_time                 TIMESTAMP,
  close_time                TIMESTAMP,
  expected_expiration_time  TIMESTAMP,
  latest_expiration_time    TIMESTAMP,
  settlement_ts             TIMESTAMP,
  last_price_dollars        NUMERIC,
  yes_bid_dollars           NUMERIC,
  yes_ask_dollars           NUMERIC,
  no_bid_dollars            NUMERIC,
  no_ask_dollars            NUMERIC,
  volume_fp                 NUMERIC,
  volume_24h_fp             NUMERIC,
  open_interest_fp          NUMERIC,
  settlement_value_dollars  NUMERIC,
  floor_strike              FLOAT64,
  custom_strike             STRING,   -- JSON object, e.g. {"Entity":"Hikaru Nakamura"}
  _source                   STRING,   -- live | historical
  _ingested_at              TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_time)
CLUSTER BY series_ticker, event_ticker;

CREATE TABLE IF NOT EXISTS `YOUR_PROJECT.kalshi.trades` (
  trade_id              STRING NOT NULL,
  ticker                STRING NOT NULL,
  series_ticker         STRING,
  event_ticker          STRING,
  count_fp              NUMERIC,
  yes_price_dollars     NUMERIC,
  no_price_dollars      NUMERIC,
  taker_outcome_side    STRING,
  taker_book_side       STRING,
  taker_side            STRING,
  created_time          TIMESTAMP,
  is_block_trade        BOOL,
  _source               STRING,   -- live | historical
  _ingested_at          TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_time)
CLUSTER BY ticker;
