"""
Migration to add product detail columns

This migration adds columns to store detailed product information from Tiki API:
- review_count: Number of reviews
- discount_rate: Discount percentage
- short_description: Brief product description
- authors: Author information (JSON)
- specifications: Product specifications (JSON)
- configurable_options: Product variants (JSON)
"""

-- Add review_count column
ALTER TABLE products ADD COLUMN IF NOT EXISTS review_count INTEGER DEFAULT 0;

-- Add discount_rate column
ALTER TABLE products ADD COLUMN IF NOT EXISTS discount_rate INTEGER DEFAULT 0;

-- Add short_description column
ALTER TABLE products ADD COLUMN IF NOT EXISTS short_description TEXT;

-- Add authors column (JSON)
ALTER TABLE products ADD COLUMN IF NOT EXISTS authors JSONB;

-- Add specifications column (JSON)
ALTER TABLE products ADD COLUMN IF NOT EXISTS specifications JSONB;

-- Add configurable_options column (JSON) for product variants
ALTER TABLE products ADD COLUMN IF NOT EXISTS configurable_options JSONB;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_products_review_count ON products(review_count DESC);
CREATE INDEX IF NOT EXISTS idx_products_discount_rate ON products(discount_rate DESC);

-- Add comment to the table
COMMENT ON COLUMN products.review_count IS 'Number of product reviews';
COMMENT ON COLUMN products.discount_rate IS 'Discount percentage (0-100)';
COMMENT ON COLUMN products.short_description IS 'Short product description';
COMMENT ON COLUMN products.authors IS 'Product authors information (JSON)';
COMMENT ON COLUMN products.specifications IS 'Product specifications (JSON)';
COMMENT ON COLUMN products.configurable_options IS 'Product variants/options (JSON)';
