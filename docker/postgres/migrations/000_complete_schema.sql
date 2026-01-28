-- ============================================
-- MIGRATION TỔNG HỢP - UIT Big Data Project
-- Tất cả migrations trong 1 file duy nhất
-- Date: 2026-01-28
-- ============================================
--

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

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

-- Products table (bao gồm CẢ columns từ migration 003)
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
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- ★ Columns từ Migration 003 ★
    review_count INTEGER DEFAULT 0,
    discount_rate INTEGER DEFAULT 0,
    short_description TEXT,
    authors JSONB,
    specifications JSONB,
    configurable_options JSONB
);

-- Product prices (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS product_prices (
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    price DECIMAL(12,2) NOT NULL,
    original_price DECIMAL(12,2),
    discount_percent INTEGER,
    stock_available INTEGER,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, timestamp)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('product_prices', 'timestamp', if_not_exists => TRUE);

-- Reviews table
CREATE TABLE IF NOT EXISTS reviews (
    review_id BIGINT PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    user_name VARCHAR(255),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    has_images BOOLEAN DEFAULT FALSE,
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Review sentiment analysis
CREATE TABLE IF NOT EXISTS review_sentiment (
    sentiment_id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES reviews(review_id) UNIQUE,
    sentiment VARCHAR(20) NOT NULL CHECK (sentiment IN ('positive', 'negative', 'neutral')),
    confidence_score DECIMAL(5,4),
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crawl logs
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
-- PHẦN 2: ORDER TABLES (Migration 004)
-- ============================================

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id BIGINT PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    review_id BIGINT NOT NULL UNIQUE REFERENCES reviews(review_id),
    order_date TIMESTAMPTZ NOT NULL,
    total_amount DECIMAL(12, 2),
    status VARCHAR(50) DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Order lines table
CREATE TABLE IF NOT EXISTS order_lines (
    order_line_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id),
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(12, 2),
    subtotal DECIMAL(12, 2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_quantity_positive CHECK (quantity > 0)
);

-- ============================================
-- PHẦN 3: CRAWL CATEGORIES (Migration 005)
-- ============================================

-- Crawl categories table
CREATE TABLE IF NOT EXISTS crawl_categories (
    category_id INTEGER PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL,
    category_url TEXT NOT NULL,
    parent_category_id INTEGER,
    
    -- Cấu hình crawl
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    max_pages INTEGER DEFAULT 10,
    
    -- Theo dõi tiến trình
    crawl_status VARCHAR(20) DEFAULT 'pending',
    last_crawled_at TIMESTAMPTZ,
    last_crawled_page INTEGER DEFAULT 0,
    total_products_crawled INTEGER DEFAULT 0,
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_crawl_status CHECK (crawl_status IN ('pending', 'in_progress', 'completed', 'failed', 'paused'))
);

-- ============================================
-- PHẦN 4: INDEXES
-- ============================================

-- Products indexes
CREATE INDEX IF NOT EXISTS idx_products_shop_id ON products(shop_id);
CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating DESC);
CREATE INDEX IF NOT EXISTS idx_products_sold_count ON products(sold_count DESC);
CREATE INDEX IF NOT EXISTS idx_products_last_updated ON products(last_updated DESC);
CREATE INDEX IF NOT EXISTS idx_products_review_count ON products(review_count DESC);
CREATE INDEX IF NOT EXISTS idx_products_discount_rate ON products(discount_rate DESC);

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

-- Orders indexes
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_review_id ON orders(review_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);

-- Order lines indexes
CREATE INDEX IF NOT EXISTS idx_order_lines_order_id ON order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_product_id ON order_lines(product_id);

-- Crawl categories indexes
CREATE INDEX IF NOT EXISTS idx_crawl_categories_status ON crawl_categories(crawl_status);
CREATE INDEX IF NOT EXISTS idx_crawl_categories_active ON crawl_categories(is_active);
CREATE INDEX IF NOT EXISTS idx_crawl_categories_priority ON crawl_categories(priority DESC);
CREATE INDEX IF NOT EXISTS idx_crawl_categories_parent ON crawl_categories(parent_category_id);

-- ============================================
-- PHẦN 5: TRIGGERS
-- ============================================

-- Trigger for customers.last_updated
CREATE OR REPLACE FUNCTION update_customer_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_customer_timestamp
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION update_customer_updated_at();

-- Trigger for crawl_categories.updated_at
CREATE OR REPLACE FUNCTION update_crawl_category_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_crawl_category_timestamp
    BEFORE UPDATE ON crawl_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_crawl_category_updated_at();

-- ============================================
-- PHẦN 6: VIEWS
-- ============================================

-- Product stats daily
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
    p.review_count,
    p.discount_rate,
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

-- Sentiment summary
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

-- Price changes
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
    p.review_count,
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
-- PHẦN 7: SAMPLE DATA
-- ============================================

-- Sample categories
INSERT INTO categories (category_name) VALUES 
    ('Electronics'),
    ('Fashion'),
    ('Home & Living'),
    ('Beauty'),
    ('Sports')
ON CONFLICT (category_name) DO NOTHING;

-- Sample crawl categories (11 Tiki categories)
INSERT INTO crawl_categories (category_id, category_name, category_url, parent_category_id, is_active, priority, max_pages, notes) VALUES
    (8322, 'Điện Thoại - Máy Tính Bảng', 'https://tiki.vn/dien-thoai-may-tinh-bang/c8322', NULL, true, 10, 50, 'Category chính'),
    (1789, 'Điện Thoại Smartphone', 'https://tiki.vn/dien-thoai-smartphone/c1789', 8322, true, 9, 50, 'Điện thoại di động'),
    (1846, 'Laptop - Máy Vi Tính - Linh kiện', 'https://tiki.vn/laptop-may-vi-tinh-linh-kien/c1846', NULL, true, 9, 50, 'Công nghệ'),
    (1801, 'Laptop', 'https://tiki.vn/laptop/c1801', 1846, true, 9, 50, 'Laptop các loại'),
    (1795, 'Máy Tính Bảng', 'https://tiki.vn/may-tinh-bang/c1795', 8322, true, 8, 30, 'Tablet'),
    (8594, 'Nhà Sách Tiki', 'https://tiki.vn/nha-sach-tiki/c8594', NULL, true, 8, 100, 'Sách tất cả thể loại'),
    (871, 'Văn học', 'https://tiki.vn/van-hoc/c871', 8594, true, 7, 80, 'Sách văn học'),
    (316, 'Sách kinh tế', 'https://tiki.vn/sach-kinh-te/c316', 8594, true, 7, 80, 'Kinh tế - Kinh doanh'),
    (1882, 'Đồ chơi - Mẹ & Bé', 'https://tiki.vn/do-choi-me-be/c1882', NULL, true, 6, 40, 'Sản phẩm cho trẻ em'),
    (2549, 'Thời trang nữ', 'https://tiki.vn/thoi-trang-nu/c2549', NULL, true, 5, 40, 'Quần áo nữ'),
    (1686, 'Thời trang nam', 'https://tiki.vn/thoi-trang-nam/c1686', NULL, true, 5, 40, 'Quần áo nam')
ON CONFLICT (category_id) DO NOTHING;

-- ============================================
-- PHẦN 8: TIMESCALEDB FEATURES
-- ============================================

-- Continuous aggregate for hourly price stats
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

-- Refresh policy
SELECT add_continuous_aggregate_policy('product_prices_hourly',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Retention policy (90 days)
SELECT add_retention_policy('product_prices', INTERVAL '90 days', if_not_exists => TRUE);

-- ============================================
-- PHẦN 9: PERMISSIONS
-- ============================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO uit_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO uit_user;

-- ============================================
-- PHẦN 10: COMMENTS
-- ============================================

-- Products table comments
COMMENT ON COLUMN products.review_count IS 'Số lượng đánh giá sản phẩm';
COMMENT ON COLUMN products.discount_rate IS 'Phần trăm giảm giá (0-100)';
COMMENT ON COLUMN products.short_description IS 'Mô tả ngắn sản phẩm';
COMMENT ON COLUMN products.authors IS 'Thông tin tác giả (JSON)';
COMMENT ON COLUMN products.specifications IS 'Thông số kỹ thuật (JSON)';
COMMENT ON COLUMN products.configurable_options IS 'Các tùy chọn biến thể (JSON)';

-- Orders table comments
COMMENT ON TABLE customers IS 'Thông tin khách hàng từ reviews (Tiki user)';
COMMENT ON TABLE orders IS 'Đơn hàng tạo từ reviews - mỗi review là 1 đơn';
COMMENT ON TABLE order_lines IS 'Chi tiết sản phẩm trong đơn hàng';
COMMENT ON COLUMN orders.review_id IS 'UNIQUE - ngăn duplicate từ cùng review';
COMMENT ON COLUMN orders.status IS 'Trạng thái - mặc định completed vì review đã tồn tại';

-- Crawl categories comments
COMMENT ON TABLE crawl_categories IS 'Quản lý cấu hình crawl các category Tiki';
COMMENT ON COLUMN crawl_categories.category_id IS 'ID category từ Tiki';
COMMENT ON COLUMN crawl_categories.is_active IS 'Category có đang được crawl không';
COMMENT ON COLUMN crawl_categories.priority IS 'Độ ưu tiên (số càng cao càng ưu tiên)';
COMMENT ON COLUMN crawl_categories.max_pages IS 'Số trang tối đa cần crawl';
COMMENT ON COLUMN crawl_categories.crawl_status IS 'Trạng thái: pending, in_progress, completed, failed, paused';
COMMENT ON COLUMN crawl_categories.last_crawled_page IS 'Trang cuối đã crawl - dùng để resume';
COMMENT ON COLUMN crawl_categories.total_products_crawled IS 'Tổng sản phẩm đã crawl';

-- ============================================
-- SUCCESS MESSAGE
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE '🎉 UIT Big Data - Database Initialized!';
    RAISE NOTICE '============================================';
    RAISE NOTICE '';
    RAISE NOTICE '📊 Tables created (11 total):';
    RAISE NOTICE '   ✅ categories, shops, products (with 6 extra columns)';
    RAISE NOTICE '   ✅ product_prices (TimescaleDB hypertable)';
    RAISE NOTICE '   ✅ reviews, review_sentiment, crawl_logs';
    RAISE NOTICE '   ✅ customers, orders, order_lines';
    RAISE NOTICE '   ✅ crawl_categories (with 11 sample categories)';
    RAISE NOTICE '';
    RAISE NOTICE '📈 Views: product_stats_daily, sentiment_summary, price_changes, top_selling_products';
    RAISE NOTICE '🔄 Triggers: Auto-update timestamps for customers & crawl_categories';
    RAISE NOTICE '⏰ TimescaleDB: Continuous aggregate + retention policy';
    RAISE NOTICE '';
    RAISE NOTICE '============================================';
END $$;
