-- Migration: Thêm bảng crawl_categories để quản lý cấu hình crawl
-- Date: 2026-01-28

-- Tạo bảng crawl_categories
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

-- Tạo indexes để tối ưu query
CREATE INDEX IF NOT EXISTS idx_crawl_categories_status ON crawl_categories(crawl_status);
CREATE INDEX IF NOT EXISTS idx_crawl_categories_active ON crawl_categories(is_active);
CREATE INDEX IF NOT EXISTS idx_crawl_categories_priority ON crawl_categories(priority DESC);
CREATE INDEX IF NOT EXISTS idx_crawl_categories_parent ON crawl_categories(parent_category_id);

-- Trigger để tự động cập nhật updated_at
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

-- Insert dữ liệu mẫu các category phổ biến trên Tiki
INSERT INTO crawl_categories (category_id, category_name, category_url, parent_category_id, is_active, priority, max_pages, notes) VALUES
    (8594, 'Nhà Sách Tiki', 'https://tiki.vn/nha-sach-tiki/c8594', NULL, true, 8, 100, 'Category chính - Sách'),
    (871, 'Văn học', 'https://tiki.vn/van-hoc/c871', 8594, true, 7, 80, 'Sách văn học'),
    (316, 'Sách kinh tế', 'https://tiki.vn/sach-kinh-te/c316', 8594, true, 7, 80, 'Sách về kinh tế, kinh doanh'),
ON CONFLICT (category_id) DO NOTHING;

-- Comments để document
COMMENT ON TABLE crawl_categories IS 'Quản lý cấu hình và tiến trình crawl các category Tiki';
COMMENT ON COLUMN crawl_categories.category_id IS 'ID category từ Tiki';
COMMENT ON COLUMN crawl_categories.is_active IS 'Category có đang được crawl không';
COMMENT ON COLUMN crawl_categories.priority IS 'Độ ưu tiên crawl (số càng cao càng ưu tiên)';
COMMENT ON COLUMN crawl_categories.max_pages IS 'Số trang tối đa cần crawl cho category này';
COMMENT ON COLUMN crawl_categories.crawl_status IS 'Trạng thái hiện tại: pending, in_progress, completed, failed, paused';
COMMENT ON COLUMN crawl_categories.last_crawled_page IS 'Trang cuối cùng đã crawl - dùng để resume';
COMMENT ON COLUMN crawl_categories.total_products_crawled IS 'Tổng số sản phẩm đã crawl được từ category này';
