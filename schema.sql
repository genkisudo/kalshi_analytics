-- BigQuery medallion datasets: raw / staging / marts (layer-only naming).
-- Project kalshi-analytics-512607 (number 9542648690).
-- Run once:
--   bq query --use_legacy_sql=false --project_id=kalshi-analytics-512607 < schema.sql
-- Ingest (step 1) loads: raw.kalshi_chess_markets, raw.kalshi_chess_trades.
-- dbt (step 2) owns tables in staging and marts.
-- Legacy: dataset `kalshi` or raw.markets / raw.trades from early prototypes.

CREATE SCHEMA IF NOT EXISTS `kalshi-analytics-512607.raw` OPTIONS (location = 'US');
CREATE SCHEMA IF NOT EXISTS `kalshi-analytics-512607.staging` OPTIONS (location = 'US');
CREATE SCHEMA IF NOT EXISTS `kalshi-analytics-512607.marts` OPTIONS (location = 'US');

CREATE TABLE IF NOT EXISTS `kalshi-analytics-512607.raw.kalshi_chess_markets` (
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
  custom_strike             STRING,
  _source                   STRING,
  _ingested_at              TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_time)
CLUSTER BY series_ticker, event_ticker;

CREATE TABLE IF NOT EXISTS `kalshi-analytics-512607.raw.kalshi_chess_trades` (
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
  _source               STRING,
  _ingested_at          TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_time)
CLUSTER BY ticker;
