import requests

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"


def get_markets(limit=10, status="open"):
    """Fetch a single page of markets (no cursor loop needed for a small limit)."""
    response = requests.get(
        f"{BASE_URL}/markets",
        params={"limit": limit, "status": status},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("markets", []), data.get("cursor")


markets, next_cursor = get_markets(limit=10)

print(f"Fetched {len(markets)} markets")
for market in markets:
    print(f"- {market['ticker']}: {market['title'][:80]}")
    print(f"  Event: {market['event_ticker']} | Created: {market.get('created_time')}")
    print(f"  Yes Bid: ${market.get('yes_bid_dollars')} | Volume: {market.get('volume_fp')}")
    print()

print(f"Next page cursor: {next_cursor or '(none)'}")

assert len(markets) <= 10, "limit=10 should return at most 10 markets"
