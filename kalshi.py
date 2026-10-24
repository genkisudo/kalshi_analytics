import requests

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"
SERIES_TICKER = "KXHIGHNY"


def get(path, **params):
    response = requests.get(f"{BASE_URL}{path}", params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def print_book_side(label, levels):
    print(f"\n{label}:")
    if not levels:
        print("  (no orders)")
    for price_dollars, count_fp in levels[:5]:  # Show top 5
        print(f"  Price: ${price_dollars}, Quantity: {count_fp}")


# Get all open markets for the series
markets = get("/markets", series_ticker=SERIES_TICKER, status="open")["markets"]
if not markets:
    raise SystemExit(f"No open markets found for {SERIES_TICKER}.")

print(f"\nActive markets in {SERIES_TICKER} series:")
for market in markets:
    print(f"- {market['ticker']}: {market['title']}")
    print(f"  Event: {market['event_ticker']}")
    print(f"  Yes Price: ${market['yes_bid_dollars']} | Volume: {market['volume_fp']}")
    print()

# Details for the first market's event
event = get(f"/events/{markets[0]['event_ticker']}")["event"]
print("Event Details:")
print(f"Title: {event['title']}")
print(f"Category: {event['category']}")

# Orderbook for the first market
market_ticker = markets[0]["ticker"]
orderbook = get(f"/markets/{market_ticker}/orderbook")["orderbook_fp"]

print(f"\nOrderbook for {market_ticker}:")
print_book_side("YES BIDS", orderbook.get("yes_dollars") or [])
print_book_side("NO BIDS", orderbook.get("no_dollars") or [])
