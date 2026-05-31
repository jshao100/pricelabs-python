"""Fetch prices with reason breakdown for a listing.

Shows how to retrieve nightly price recommendations and inspect the pricing
signals — seasonality, day-of-week multiplier, min/max thresholds — that
drove each day's recommendation.

Run with a real API key:

    PRICELABS_API_KEY=your_key python examples/fetch_prices.py
"""

from pricelabs import PriceLabsClient
from pricelabs.prices import PriceRequest

# Replace with your actual listing ID and PMS name (e.g. "airbnb", "ownerrez").
LISTING_ID = "your-listing-id"
PMS = "airbnb"

client = PriceLabsClient(api_key="your_api_key")

# Request prices for a 7-day window with reason data included.
# Setting reason=True on both the PriceRequest and prices.get() ensures the
# API returns the full pricing breakdown for each day.
result = client.prices.get(
    [
        PriceRequest(
            id=LISTING_ID,
            pms=PMS,
            date_from="2026-06-01",
            date_to="2026-06-07",
            reason=True,
        )
    ],
    reason=True,
)

for lp in result:
    # When a listing has no data or is toggled off, error_status is set instead
    # of raising an exception — handle it explicitly.
    if lp.error_status:
        print(f"Listing {lp.id}: skipped — {lp.error_status}")
        continue

    print(f"Listing: {lp.id}  PMS: {lp.pms}  Currency: {lp.currency}")
    print(f"Last refreshed: {lp.last_refreshed_at}")
    print()

    for day in lp.data:
        status = day.booking_status or "unknown"
        print(f"  {day.date}  ${day.price:.0f}  {day.demand_color}  [{status}]")

        # reason is populated when reason=True was requested
        if day.reason is None:
            continue

        mf = day.reason.market_factors
        if mf:
            print(
                f"    seasonality={mf.seasonality_score}"
                f"  dow_mult={mf.day_of_week_multiplier}"
                f"  lead={mf.lead_time_days}d"
            )

        th = day.reason.thresholds
        if th:
            print(
                f"    min=${th.min_price}  base=${th.base_price}"
                f"  max=${th.max_price}  health={th.health_score}"
            )

        dbg = day.reason.debug_info
        if dbg:
            print(f"    model={dbg.model_version}  confidence={dbg.confidence}")

client.close()
