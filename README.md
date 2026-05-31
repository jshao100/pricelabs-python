# pricelabs-python

Python client for the [PriceLabs Customer API](https://pricelabs.co).

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Installation

```bash
pip install git+https://github.com/pricelabs-python/pricelabs-python.git
```

With optional 1Password support:

```bash
pip install "git+https://github.com/pricelabs-python/pricelabs-python.git#egg=pricelabs[1password]"
```

## Quickstart

```python
from pricelabs import PriceLabsClient

client = PriceLabsClient(api_key="your_api_key")
listings = client.listings.list()
for listing in listings:
    print(listing.name, listing.id)
client.close()
```

## Authentication

The client resolves your API key in this order:

**1. Explicit argument**

```python
client = PriceLabsClient(api_key="pl_live_...")
```

**2. Environment variable**

```bash
export PRICELABS_API_KEY=pl_live_...
```

```python
client = PriceLabsClient()  # reads PRICELABS_API_KEY automatically
```

**3. 1Password (optional)**

Install the optional extra and pass an `op://` URI as the key. Your application is responsible for resolving the secret via the 1Password SDK before passing it to the client.

```bash
pip install "pricelabs[1password]"
```

```python
import asyncio
import onepassword

async def get_client():
    client_op = await onepassword.Client.authenticate(
        auth=os.environ["OP_SERVICE_ACCOUNT_TOKEN"],
        integration_name="my-app",
        integration_version="1.0.0",
    )
    api_key = await client_op.secrets.resolve("op://vault/pricelabs/api-key")
    return PriceLabsClient(api_key=api_key)
```

**4. Config file**

Set the key in your shell profile or `.env` file and load it before constructing the client:

```bash
# ~/.env or shell profile
export PRICELABS_API_KEY=pl_live_...
```

```python
from dotenv import load_dotenv
load_dotenv()
client = PriceLabsClient()
```

## Usage

### Listings

```python
# List all listings
listings = client.listings.list()
listings = client.listings.list(skip_hidden=True, only_syncing=True)

# Get a single listing
listing = client.listings.get("listing-id-123")

# Update pricing parameters
from pricelabs import ListingUpdate
client.listings.update([
    ListingUpdate(id="listing-id-123", pms="airbnb", min=100, base=150, max=500),
])
```

### Prices

```python
from pricelabs import PriceRequest

requests = [
    PriceRequest(id="listing-id-123", pms="airbnb", date_from="2026-06-01", date_to="2026-06-30"),
]

# Basic prices
prices = client.prices.get(requests)
for lp in prices:
    if lp.error_status:
        print(f"Error for {lp.id}: {lp.error_status}")
    else:
        for day in lp.data:
            print(day.date, day.price)

# Prices with reasoning breakdown
prices = client.prices.get(requests, reason=True)
for lp in prices:
    for day in lp.data:
        if day.reason and day.reason.market_factors:
            print(day.date, day.price, day.reason.market_factors.seasonality_score)

# Rate plans
rate_plans = client.prices.rate_plans(listing_id="listing-id-123", pms_name="airbnb")
```

### Overrides

```python
from pricelabs import OverrideInput

# Create overrides
overrides = client.overrides.create(
    listing_id="listing-id-123",
    pms="airbnb",
    overrides=[
        OverrideInput(date="2026-07-04", price="250", price_type="fixed", min_stay=2),
        OverrideInput(date="2026-12-25", price="300", price_type="fixed"),
    ],
)

# List existing overrides
existing = client.overrides.list(listing_id="listing-id-123", pms="airbnb")
for override in existing:
    print(override.date, override.price)

# Delete overrides
client.overrides.delete(
    listing_id="listing-id-123",
    pms="airbnb",
    dates=["2026-07-04", "2026-12-25"],
)
```

### Market Data

```python
data = client.market.neighborhood(listing_id="listing-id-123", pms="airbnb")
print(data.currency, data.listings_used)
if data.market_kpi:
    print(data.market_kpi.avg_daily_rate, data.market_kpi.occupancy_rate)
```

### Reservations

```python
# Single page
page = client.reservations.list(pms="airbnb", start_date="2026-01-01", end_date="2026-12-31")
for reservation in page.data:
    print(reservation.reservation_id, reservation.check_in, reservation.booking_status)
has_more = page.next_page

# Auto-paginate all results
for reservation in client.reservations.list_all(pms="airbnb", start_date="2026-01-01"):
    print(reservation.reservation_id, reservation.rental_revenue)
```

## Error Handling

All exceptions inherit from `PriceLabsError`:

```
PriceLabsError
├── APIError                   # base for HTTP errors (.status_code, .raw)
│   ├── AuthenticationError    # 401
│   ├── ForbiddenError         # 403
│   ├── NotFoundError          # 404
│   ├── InvalidRequestError    # 422
│   ├── RateLimitError         # 429 (.retry_after seconds)
│   └── ServerError            # 5xx
├── ConfigurationError         # missing or invalid SDK configuration
└── NetworkError               # connection/timeout failures
```

```python
from pricelabs import PriceLabsClient, AuthenticationError, RateLimitError, PriceLabsError

client = PriceLabsClient()
try:
    listings = client.listings.list()
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited — retry after {e.retry_after}s")
except PriceLabsError as e:
    print(f"SDK error: {e}")
```

## Rate Limiting

The PriceLabs API enforces:

- **60 requests/minute**
- **1,000 requests/hour**

The SDK automatically retries on 429 responses using exponential backoff with jitter, respecting the `Retry-After` header when present. By default, the client attempts up to 5 times before raising `RateLimitError`.

## Configuration

### Client options

```python
client = PriceLabsClient(
    api_key="pl_live_...",
    base_url="https://api.pricelabs.co",  # override for testing
    timeout=300,                           # per-request timeout in seconds
    max_retries=5,                         # total attempts including first
)
```

### Environment variables

| Variable | Description |
|---|---|
| `PRICELABS_API_KEY` | API key (required if not passed explicitly) |
| `PRICELABS_BASE_URL` | Override API base URL |

### Context manager

```python
from pricelabs import PriceLabsClient

with PriceLabsClient() as client:
    listings = client.listings.list()
```

> **Note:** `PriceLabsClient` does not implement `__enter__`/`__exit__` natively; call `client.close()` explicitly or wrap with `contextlib.closing`.

```python
from contextlib import closing
from pricelabs import PriceLabsClient

with closing(PriceLabsClient()) as client:
    listings = client.listings.list()
```

## Contributing

```bash
git clone https://github.com/pricelabs-python/pricelabs-python.git
cd pricelabs-python
pip install -e ".[dev]"
pytest
ruff check .
```

Pull requests welcome. Open an issue first for significant changes.

## License

MIT — see [LICENSE](LICENSE).
