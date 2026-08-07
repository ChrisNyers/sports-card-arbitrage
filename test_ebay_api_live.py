#!/usr/bin/env python3
"""Test eBay Browse API integration with real data."""

from datetime import date
from cardarb.sources.ebay import EbayAdapter
from cardarb.sources.mock_data.card_catalog import get_cards

# Get some real card IDs to search for
cards = get_cards()
card_ids = [c.card_id for c in cards[:3]]  # Test with first 3 cards

print("=" * 100)
print("eBay Browse API Live Test")
print("=" * 100)

try:
    adapter = EbayAdapter()
    print(f"\n✓ eBay adapter initialized")
    print(f"✓ Will search for {len(card_ids)} cards")

    # Get today's date
    today = date.today()

    # Fetch listings
    print(f"\nFetching listings from eBay Browse API...")
    listings = adapter.fetch_listings(card_ids, today)

    print(f"\n{'=' * 100}")
    print(f"Results:")
    print(f"{'=' * 100}")
    print(f"Total listings found: {len(listings)}")

    if listings:
        # Show first 10
        for i, listing in enumerate(listings[:10], 1):
            card = next((c for c in cards if c.card_id == listing.card_id), None)
            if card:
                print(f"\n{i}. {card.player_name} - {card.year} {card.set_name} #{card.card_number}")
                print(f"   Price: ${listing.price:.2f}")
                print(f"   Type: {listing.listing_type}")
                print(f"   Listed: {listing.listed_at}")
    else:
        print("\nNo listings found. Possible issues:")
        print("  1. eBay API credentials not set (check .env)")
        print("  2. eBay API rate limit hit")
        print("  3. Search keywords not matching any listings")
        print("  4. eBay API access not enabled for your app")

    print(f"\n{'=' * 100}")

except Exception as e:
    print(f"\n✗ Error: {e}")
    print(f"\nTroubleshooting:")
    print(f"  1. Check EBAY_APP_ID and EBAY_CERT_ID in .env")
    print(f"  2. Verify eBay API credentials are active")
    print(f"  3. Check eBay developer portal for API status")
