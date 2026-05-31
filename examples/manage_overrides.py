"""Create, list, and delete date-specific price overrides.

Date-specific overrides (DSO) let you apply a fixed price or percent
adjustment to individual calendar dates — useful for holidays, local events,
and seasonal adjustments.

Run with a real API key:

    PRICELABS_API_KEY=your_key python examples/manage_overrides.py
"""

from pricelabs import PriceLabsClient
from pricelabs.overrides import OverrideInput

# Replace with your actual listing ID and PMS name.
LISTING_ID = "your-listing-id"
PMS = "airbnb"

client = PriceLabsClient(api_key="your_api_key")

# --- Create overrides ---
# Each OverrideInput targets one calendar date.
# price_type="fixed" sets an exact nightly rate.
# price_type="percent" adds a percentage premium to the base price.
new_overrides = [
    OverrideInput(
        date="2026-07-04",
        price="25",          # 25% premium above base
        price_type="percent",
        min_stay=3,
        reason="Independence Day weekend",
    ),
    OverrideInput(
        date="2026-12-31",
        price="350",         # Fixed nightly price
        price_type="fixed",
        min_stay=2,
        reason="New Year's Eve",
    ),
]

# Pass update_children=True to cascade overrides to child listings in a group.
created = client.overrides.create(LISTING_ID, PMS, new_overrides, update_children=False)
print(f"Created {len(created)} override(s):")
for o in created:
    print(f"  {o.date}  {o.price_type}  price={o.price}  reason={o.reason}")

# --- List all current overrides ---
print()
all_overrides = client.overrides.list(LISTING_ID, PMS)
print(f"All overrides for listing {LISTING_ID} ({len(all_overrides)} total):")
for o in all_overrides:
    min_stay_str = f"  min_stay={o.min_stay}" if o.min_stay else ""
    print(f"  {o.date}  {o.price_type}  {o.price}{min_stay_str}")

# --- Delete a specific override ---
# Pass the list of dates whose overrides you want to remove.
dates_to_remove = ["2026-07-04"]
client.overrides.delete(LISTING_ID, PMS, dates=dates_to_remove)
print(f"\nDeleted override(s) for: {dates_to_remove}")

# Confirm the deletion by listing again.
remaining = client.overrides.list(LISTING_ID, PMS)
remaining_dates = [o.date for o in remaining]
print(f"Remaining override dates: {remaining_dates}")

client.close()
