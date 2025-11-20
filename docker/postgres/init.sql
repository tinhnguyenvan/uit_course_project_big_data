-- Shopee Analytics Database Initialization Script
-- This script sets up the database schema for storing Shopee product and review data

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create Metabase database (for Metabase internal use)
CREATE DATABASE metabase;

-- Connect to uit_analytics database
\c uit_analytics;

-- ============================================
-- MAIN TABLES
-- ============================================

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL UNIQUE,
    parent_id INTEGER REFERENCES categories(category_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shops table
CREATE TABLE IF NOT EXISTS shops (
    shop_id BIGINT PRIMARY KEY,
    shop_name VARCHAR(255) NOT NULL,
    rating DECIMAL(3,2),
    response_rate INTEGER,
    follower_count INTEGER,
    is_official BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    product_id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    shop_id BIGINT REFERENCES shops(shop_id),
    category_id INTEGER REFERENCES categories(category_id),
    url TEXT NOT NULL,
    image_url TEXT,
    description TEXT,
    rating DECIMAL(3,2),
    sold_count INTEGER DEFAULT 0,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product prices (TimescaleDB hypertable for time-series data)
CREATE TABLE IF NOT EXISTS product_prices (
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    price DECIMAL(12,2) NOT NULL,
    original_price DECIMAL(12,2),
    discount_percent INTEGER,
    stock_available INTEGER,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, timestamp)
);

-- Convert product_prices to TimescaleDB hypertable
SELECT create_hypertable('product_prices', 'timestamp', if_not_exists => TRUE);

-- Reviews table
CREATE TABLE IF NOT EXISTS reviews (
    review_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    user_name VARCHAR(255),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    has_images BOOLEAN DEFAULT FALSE,
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Review sentiment analysis results
CREATE TABLE IF NOT EXISTS review_sentiment (
    sentiment_id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES reviews(review_id) UNIQUE,
    sentiment VARCHAR(20) NOT NULL CHECK (sentiment IN ('positive', 'negative', 'neutral')),
    confidence_score DECIMAL(5,4),
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crawl logs table (for monitoring)
CREATE TABLE IF NOT EXISTS crawl_logs (
    log_id BIGSERIAL PRIMARY KEY,
    crawler_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    items_crawled INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INTEGER
);

-- ============================================
-- INDEXES
-- ============================================

-- Products indexes
CREATE INDEX IF NOT EXISTS idx_products_shop_id ON products(shop_id);
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating DESC);
CREATE INDEX IF NOT EXISTS idx_products_sold_count ON products(sold_count DESC);
CREATE INDEX IF NOT EXISTS idx_products_last_updated ON products(last_updated DESC);

-- Product prices indexes
CREATE INDEX IF NOT EXISTS idx_product_prices_product_id ON product_prices(product_id);
CREATE INDEX IF NOT EXISTS idx_product_prices_timestamp ON product_prices(timestamp DESC);

-- Reviews indexes
CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);
CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_crawled_at ON reviews(crawled_at DESC);

-- Review sentiment indexes
CREATE INDEX IF NOT EXISTS idx_review_sentiment_review_id ON review_sentiment(review_id);
CREATE INDEX IF NOT EXISTS idx_review_sentiment_sentiment ON review_sentiment(sentiment);

-- Shops indexes
CREATE INDEX IF NOT EXISTS idx_shops_rating ON shops(rating DESC);

-- ============================================
-- VIEWS FOR ANALYTICS
-- ============================================

-- Product stats daily view
CREATE OR REPLACE VIEW product_stats_daily AS
SELECT 
    p.product_id,
    p.name,
    p.shop_id,
    s.shop_name,
    p.category_id,
    c.category_name,
    p.rating,
    p.sold_count,
    pp.price,
    pp.original_price,
    pp.discount_percent,
    pp.timestamp::date as date
FROM products p
LEFT JOIN shops s ON p.shop_id = s.shop_id
LEFT JOIN categories c ON p.category_id = c.category_id
LEFT JOIN LATERAL (
    SELECT price, original_price, discount_percent, timestamp
    FROM product_prices
    WHERE product_id = p.product_id
    ORDER BY timestamp DESC
    LIMIT 1
) pp ON true;

-- Sentiment summary by product
CREATE OR REPLACE VIEW sentiment_summary AS
SELECT 
    p.product_id,
    p.name,
    COUNT(r.review_id) as total_reviews,
    COUNT(CASE WHEN rs.sentiment = 'positive' THEN 1 END) as positive_count,
    COUNT(CASE WHEN rs.sentiment = 'negative' THEN 1 END) as negative_count,
    COUNT(CASE WHEN rs.sentiment = 'neutral' THEN 1 END) as neutral_count,
    ROUND(COUNT(CASE WHEN rs.sentiment = 'positive' THEN 1 END)::numeric / 
          NULLIF(COUNT(r.review_id), 0) * 100, 2) as positive_percentage,
    AVG(rs.confidence_score) as avg_confidence
FROM products p
LEFT JOIN reviews r ON p.product_id = r.product_id
LEFT JOIN review_sentiment rs ON r.review_id = rs.review_id
GROUP BY p.product_id, p.name;

-- Price changes view (products with price changes in last 7 days)
CREATE OR REPLACE VIEW price_changes AS
WITH price_comparison AS (
    SELECT 
        product_id,
        price as current_price,
        LAG(price) OVER (PARTITION BY product_id ORDER BY timestamp DESC) as previous_price,
        timestamp as current_timestamp,
        LAG(timestamp) OVER (PARTITION BY product_id ORDER BY timestamp DESC) as previous_timestamp
    FROM product_prices
    WHERE timestamp >= NOW() - INTERVAL '7 days'
)
SELECT 
    p.product_id,
    p.name,
    pc.current_price,
    pc.previous_price,
    pc.current_price - pc.previous_price as price_difference,
    ROUND(((pc.current_price - pc.previous_price) / NULLIF(pc.previous_price, 0) * 100)::numeric, 2) as price_change_percent,
    pc.current_timestamp,
    pc.previous_timestamp
FROM price_comparison pc
JOIN products p ON pc.product_id = p.product_id
WHERE pc.previous_price IS NOT NULL
  AND pc.current_price != pc.previous_price
ORDER BY ABS(pc.current_price - pc.previous_price) DESC;

-- Top selling products
CREATE OR REPLACE VIEW top_selling_products AS
SELECT 
    p.product_id,
    p.name,
    s.shop_name,
    c.category_name,
    p.rating,
    p.sold_count,
    pp.price,
    pp.discount_percent
FROM products p
LEFT JOIN shops s ON p.shop_id = s.shop_id
LEFT JOIN categories c ON p.category_id = c.category_id
LEFT JOIN LATERAL (
    SELECT price, discount_percent
    FROM product_prices
    WHERE product_id = p.product_id
    ORDER BY timestamp DESC
    LIMIT 1
) pp ON true
ORDER BY p.sold_count DESC
LIMIT 100;

-- ============================================
-- SAMPLE DATA (for testing)
-- ============================================

-- Insert sample category
INSERT INTO categories (category_name) VALUES 
    ('Electronics'),
    ('Fashion'),
    ('Home & Living'),
    ('Beauty'),
    ('Sports')
ON CONFLICT (category_name) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO uit_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO uit_user;

-- Create continuous aggregate for hourly price statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS product_prices_hourly
WITH (timescaledb.continuous) AS
SELECT 
    product_id,
    time_bucket('1 hour', timestamp) AS bucket,
    AVG(price) as avg_price,
    MIN(price) as min_price,
    MAX(price) as max_price,
    COUNT(*) as price_changes
FROM product_prices
GROUP BY product_id, bucket
WITH NO DATA;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('product_prices_hourly',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Create retention policy (keep data for 90 days)
SELECT add_retention_policy('product_prices', INTERVAL '90 days', if_not_exists => TRUE);

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Shopee Analytics Database initialized successfully!';
    RAISE NOTICE 'Tables created: categories, shops, products, product_prices, reviews, review_sentiment, crawl_logs';
    RAISE NOTICE 'Views created: product_stats_daily, sentiment_summary, price_changes, top_selling_products';
    RAISE NOTICE 'TimescaleDB hypertable: product_prices';
END $$;
