"""Basic usage: create a client and list all active listings.

Run with a real API key:

    PRICELABS_API_KEY=your_key python examples/basic_usage.py

Or pass the key directly (not recommended for production):

    python examples/basic_usage.py
"""

from pricelabs import PriceLabsClient

# Create the client. Reads PRICELABS_API_KEY from the environment when api_key
# is omitted. Adjust timeout and max_retries as needed for your workload.
client = PriceLabsClient(api_key="your_api_key")

# Fetch only listings that are actively syncing prices to their channels.
# Use skip_hidden=True to exclude hidden/archived listings as well.
listings = client.listings.list(only_syncing=True)

print(f"Found {len(listings)} active listing(s):\n")
for listing in listings:
    base = f"${listing.base:.0f}" if listing.base is not None else "unset"
    low = f"${listing.min:.0f}" if listing.min is not None else "?"
    high = f"${listing.max:.0f}" if listing.max is not None else "?"
    print(f"  {listing.name}")
    print(f"    ID: {listing.id}  PMS: {listing.pms}")
    print(f"    Base: {base}  Range: {low}–{high}")
    print(f"    Location: {listing.city_name}, {listing.state}")
    print()

# Always close the client to release HTTP connections.
client.close()
