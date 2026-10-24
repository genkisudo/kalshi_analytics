# Repository Guidelines

## Project Structure & Module Organization

This repository is a small, standalone Python sandbox for exploring the Kalshi public REST API. Python scripts live in the repository root: `kalshi.py` demonstrates series, event, and orderbook requests; `api_page_test.py` fetches one page of markets; and `extract_markets.py` selects series, paginates recent markets, and writes JSONL. `schema.sql` contains the planned BigQuery table definition. `api_pagination.md` and `api_history.md` document API behavior. Generated extracts belong in `data/`; do not commit credentials or unnecessary large data files.

## Build, Test, and Development Commands

There is no package build system, dependency manifest, or local server. Python 3 and `requests` are required. Run scripts directly from the repository root:

- `python3 kalshi.py` — query open KXHIGHNY markets and display event/orderbook data.
- `python3 api_page_test.py` — make a live smoke request for up to 10 open markets.
- `python3 extract_markets.py` — fetch recent markets for configured series and create a timestamped JSONL file in `data/`.

These commands make live API calls; they need network access and can fail when the API is unavailable.

## Coding Style & Naming Conventions

Use Python 3, four spaces for indentation, descriptive `snake_case` functions and variables, and uppercase names for module-level constants. Keep scripts readable and focused. API calls should use the shared base URL pattern, set a request timeout, and call `raise_for_status()` before decoding responses. Preserve fixed-point API values as strings unless a downstream schema explicitly requires conversion.

## Testing Guidelines

There is no pytest suite or configured coverage target. `api_page_test.py` is a live smoke script, not an isolated unit test; it prints results and asserts the requested page is within its limit. When changing pagination or historical lookups, consult `api_pagination.md` and `api_history.md` and manually verify against the relevant endpoint.

## Commit & Pull Request Guidelines

Git metadata is not present in this checkout, so repository-specific commit conventions cannot be verified. Use a short imperative commit subject (for example, `Add historical market pagination`). Pull requests should explain the API behavior changed, list manual checks performed, and include representative output or sample data when it helps reviewers.

## Security & Configuration Tips

The API examples use public endpoints and currently require no credentials. Keep tokens and personal configuration out of source control. Before running `extract_markets.py`, review its category/tag filters and remember that it creates data files under `data/`.
