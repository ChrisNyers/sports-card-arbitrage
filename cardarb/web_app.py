"""
Minimal web interface for eBay Growth Check demonstration.

Purpose: Display eBay listing data retrieved through the existing EbayAdapter.
- Search form for sports cards
- Call existing eBay Browse API adapter
- Display normalized listing information
- Show source attribution and research-only disclaimer
- No purchasing, bidding, checkout, or transaction functionality

Architecture: Research and decision support tool only.
"""

from datetime import date
from flask import Flask, render_template, request, jsonify, render_template_string
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cardarb.config import get_listings_source
from cardarb.sources.mock_data.card_catalog import get_cards

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Get listings source (will use EbayAdapter if credentials available, MockEbayAdapter otherwise)
listings_source = get_listings_source()

# Cache card catalog
CARD_CATALOG = {c.card_id: c for c in get_cards()}


@app.route('/')
def index():
    """Display search interface."""
    return render_template('search.html')


@app.route('/api/search', methods=['POST'])
def search():
    """Search for a card and fetch eBay listings.

    Request JSON:
        {
            "player_name": "Patrick Mahomes",
            "year": 2017,
            "set_name": "Panini Prizm"
        }

    Response JSON:
        {
            "success": true,
            "card": {
                "id": 12345,
                "player": "Patrick Mahomes",
                "year": 2017,
                "set": "Panini Prizm",
                "manufacturer": "Panini"
            },
            "listings": [
                {
                    "price": 145.00,
                    "format": "fixed-price",
                    "source": "ebay",
                    "listed_at": "2026-08-07T10:30:00+00:00"
                }
            ],
            "listing_count": 1
        }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        player_name = data.get('player_name', '').strip()
        year = data.get('year')
        set_name = data.get('set_name', '').strip()

        # Validate input
        if not player_name or not year or not set_name:
            return jsonify({
                'success': False,
                'error': 'Player name, year, and set name are required'
            }), 400

        try:
            year = int(year)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Year must be a number'}), 400

        # Find matching card in catalog
        card = None
        for c in CARD_CATALOG.values():
            if (c.player_name.lower() == player_name.lower() and
                c.year == year and
                c.set_name.lower() == set_name.lower()):
                card = c
                break

        if not card:
            return jsonify({
                'success': False,
                'error': f'Card not found. Searched for {player_name}, {year} {set_name}'
            }), 404

        # Fetch listings from eBay (or mock adapter if no credentials)
        try:
            listings = listings_source.fetch_listings([card.card_id], date.today())
        except Exception as e:
            # Don't expose sensitive errors; log them server-side
            app.logger.error(f'Error fetching listings for card {card.card_id}: {str(e)}')
            return jsonify({
                'success': False,
                'error': 'Unable to fetch listings. Please try again.'
            }), 500

        # Format response with normalized data
        formatted_listings = []
        for listing in listings:
            formatted_listings.append({
                'price': float(listing.price),
                'format': listing.listing_type,  # "auction", "fixed-price", "sold"
                'source': listing.source,  # "ebay" or other marketplace
                'listed_at': listing.listed_at.isoformat() if listing.listed_at else None,
                'sold_at': listing.sold_at.isoformat() if listing.sold_at else None,
            })

        return jsonify({
            'success': True,
            'card': {
                'id': card.card_id,
                'player': card.player_name,
                'year': card.year,
                'set': card.set_name,
                'manufacturer': getattr(card, 'manufacturer', 'Unknown'),
                'card_number': getattr(card, 'card_number', ''),
            },
            'listings': formatted_listings,
            'listing_count': len(formatted_listings),
            'source': 'eBay Browse API' if hasattr(listings_source, 'fetch_listings') and
                     listings_source.__class__.__name__ == 'EbayAdapter' else 'Mock Data'
        })

    except Exception as e:
        # Don't expose stack traces or sensitive details
        app.logger.error(f'Search error: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An error occurred during search.'
        }), 500


@app.route('/api/cards', methods=['GET'])
def list_cards():
    """Get list of available cards for autocomplete.

    Used by the search form autocomplete.
    """
    try:
        cards = [
            {
                'id': c.card_id,
                'player': c.player_name,
                'year': c.year,
                'set': c.set_name,
                'label': f'{c.player_name} ({c.year} {c.set_name})'
            }
            for c in CARD_CATALOG.values()
        ]
        return jsonify({'success': True, 'cards': cards})
    except Exception as e:
        app.logger.error(f'Error listing cards: {str(e)}')
        return jsonify({'success': False, 'error': 'Unable to load cards'}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for monitoring."""
    return jsonify({'status': 'healthy', 'service': 'atlas-ebay-growth-check'})


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({'success': False, 'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors without exposing sensitive information."""
    app.logger.error(f'Internal server error: {str(e)}', exc_info=True)
    return jsonify({
        'success': False,
        'error': 'Internal server error. Please try again.'
    }), 500


if __name__ == '__main__':
    # For local development only
    # In production, Gunicorn will serve the app
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
