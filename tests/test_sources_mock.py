from datetime import date

from cardarb.sources.ebay import MockEbayAdapter
from cardarb.sources.mock_data.card_catalog import get_cards
from cardarb.sources.news import MockNewsAdapter
from cardarb.sources.psa import MockPsaAdapter
from cardarb.sources.reddit import MockRedditAdapter
from cardarb.sources.twitter import MockTwitterAdapter


def test_ebay_adapter_shape_and_determinism():
    cards = get_cards()[:3]
    card_ids = [c.card_id for c in cards]
    as_of = date(2026, 6, 1)

    adapter = MockEbayAdapter()
    listings_a = adapter.fetch_listings(card_ids, as_of)
    listings_b = adapter.fetch_listings(card_ids, as_of)

    assert len(listings_a) == len(listings_b)
    assert [l.price for l in listings_a] == [l.price for l in listings_b]
    assert all(l.listing_type in ("sold", "active") for l in listings_a)
    assert all(l.price > 0 for l in listings_a)


def test_twitter_and_reddit_adapters():
    card_ids = [c.card_id for c in get_cards()[:2]]
    as_of = date(2026, 6, 1)

    twitter_records = MockTwitterAdapter().fetch_mentions(card_ids, as_of)
    reddit_records = MockRedditAdapter().fetch_mentions(card_ids, as_of)

    assert all(r.source == "twitter" for r in twitter_records)
    assert all(r.source == "reddit" for r in reddit_records)
    assert all(-1.0 <= r.sentiment_score <= 1.0 for r in twitter_records + reddit_records)


def test_psa_adapter():
    card_ids = [c.card_id for c in get_cards()[:2]]
    as_of = date(2026, 6, 1)
    pops = MockPsaAdapter().fetch_population(card_ids, as_of)
    assert len(pops) == 2
    assert all(p.population > 0 for p in pops)


def test_news_adapter_sentiment_bounds():
    card_ids = [c.card_id for c in get_cards()[:5]]
    as_of = date(2026, 6, 1)
    news = MockNewsAdapter().fetch_news(card_ids, as_of)
    assert all(-1.0 <= n.sentiment_score <= 1.0 for n in news)
