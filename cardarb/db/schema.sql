CREATE TABLE IF NOT EXISTS cards (
    card_id INTEGER PRIMARY KEY,
    player_name TEXT NOT NULL,
    year INTEGER NOT NULL,
    set_name TEXT NOT NULL,
    card_number TEXT,
    variant TEXT,
    sport TEXT NOT NULL,
    grade TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_listings (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL REFERENCES cards(card_id),
    source TEXT NOT NULL,
    listing_type TEXT NOT NULL,
    price REAL NOT NULL,
    listed_at TEXT NOT NULL,
    sold_at TEXT,
    ingested_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raw_listings_card ON raw_listings(card_id);

CREATE TABLE IF NOT EXISTS raw_social_mentions (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL REFERENCES cards(card_id),
    source TEXT NOT NULL,
    mention_count INTEGER NOT NULL,
    sentiment_score REAL NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raw_social_card ON raw_social_mentions(card_id);

CREATE TABLE IF NOT EXISTS raw_psa_pop (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL REFERENCES cards(card_id),
    grade TEXT NOT NULL,
    population INTEGER NOT NULL,
    population_change_30d INTEGER NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raw_psa_card ON raw_psa_pop(card_id);

CREATE TABLE IF NOT EXISTS raw_news (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL REFERENCES cards(card_id),
    headline TEXT NOT NULL,
    sentiment_score REAL NOT NULL,
    published_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raw_news_card ON raw_news(card_id);

CREATE TABLE IF NOT EXISTS features (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL REFERENCES cards(card_id),
    as_of_date TEXT NOT NULL,
    avg_sold_price_7d REAL,
    avg_sold_price_30d REAL,
    price_change_pct_7d REAL,
    price_change_pct_30d REAL,
    sales_velocity_7d INTEGER,
    listing_count_active INTEGER,
    listing_count_trend_pct REAL,
    price_volatility_30d REAL,
    social_mention_count_7d INTEGER,
    social_sentiment_avg_7d REAL,
    psa_pop_growth_30d_pct REAL,
    news_sentiment_avg_7d REAL,
    UNIQUE(card_id, as_of_date)
);

CREATE TABLE IF NOT EXISTS bubble_scores (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL REFERENCES cards(card_id),
    as_of_date TEXT NOT NULL,
    velocity_signal REAL,
    volatility_signal REAL,
    sentiment_signal REAL,
    listing_trend_signal REAL,
    psa_pop_signal REAL,
    composite_score REAL NOT NULL,
    risk_label TEXT NOT NULL,
    UNIQUE(card_id, as_of_date)
);

CREATE TABLE IF NOT EXISTS ml_predictions (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL REFERENCES cards(card_id),
    as_of_date TEXT NOT NULL,
    model_version TEXT NOT NULL,
    prob_price_rise REAL NOT NULL,
    predicted_label INTEGER NOT NULL,
    UNIQUE(card_id, as_of_date)
);

CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL REFERENCES cards(card_id),
    as_of_date TEXT NOT NULL,
    current_price REAL NOT NULL,
    target_sell_price REAL NOT NULL,
    estimated_cost_basis REAL NOT NULL,
    estimated_roic_pct REAL NOT NULL,
    ml_prob_price_rise REAL NOT NULL,
    bubble_composite_score REAL NOT NULL,
    opportunity_score REAL NOT NULL,
    rank INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_opportunities_date ON opportunities(as_of_date, rank);

CREATE TABLE IF NOT EXISTS approval_decisions (
    id INTEGER PRIMARY KEY,
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(id),
    decision TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    notes TEXT,
    actual_buy_price REAL
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL REFERENCES cards(card_id),
    opportunity_id INTEGER REFERENCES opportunities(id),
    buy_price REAL NOT NULL,
    buy_date TEXT NOT NULL,
    buy_fees REAL NOT NULL DEFAULT 0,
    quantity INTEGER NOT NULL DEFAULT 1,
    current_market_price REAL,
    current_price_updated_at TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    sell_price REAL,
    sell_date TEXT,
    sell_fees REAL NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
