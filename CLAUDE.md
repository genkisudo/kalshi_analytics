# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Small, unstructured sandbox for exploring the Kalshi public REST API with plain `requests`. There is no package, build system, linter, or test framework (no `requirements.txt` either — only `requests` is needed). Each `.py` file is a standalone script run directly:

```
python3 kalshi.py          # series -> open markets -> event details -> orderbook for KXHIGHNY
python3 api_page_test.py   # fetches one page of 10 open markets (limit=10) and prints them
```

The "tests" are live-API smoke scripts, not pytest tests; there is no single-test command.

## Reference docs (local copies of Kalshi docs)

- `api_pagination.md` — cursor pagination (`cursor`/`limit`, loop until cursor is empty, keep filters constant across pages).
- `api_history.md` — live vs. historical storage tiers. Old markets, trades, orders and fills move behind per-type cutoffs from `GET /historical/cutoff`, and must then be fetched from `/historical/*` endpoints. Cutoffs differ per data type; events and series are unaffected.

Consult these before writing code that pages through or looks back at old data.

## API conventions to keep consistent

- Base URL: `https://external-api.kalshi.com/trade-api/v2` (used throughout the scripts and docs; Kalshi's documented host `api.elections.kalshi.com` also works).
- Responses use fixed-point string fields: `yes_bid_dollars`, `volume_fp`, and orderbook under `orderbook_fp.yes_dollars` / `no_dollars` as `[price, count]` pairs. An orderbook side can be empty.
- `/markets` ordering is not documented as guaranteed; the unfiltered feed is dominated by `KXMVECROSSCATEGORY-*` multi-leg combo markets with very long titles. Filter by `series_ticker` (e.g. `KXHIGHNY`) for ordinary markets.
- Scripts use `raise_for_status()` plus a timeout on every request; keep that rather than treating failed requests as empty results.
