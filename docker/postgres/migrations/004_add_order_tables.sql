-- Migration: Add customer, order, and order_line tables for order pipeline
-- Date: 2026-01-28

-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id BIGINT PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    review_id BIGINT NOT NULL UNIQUE REFERENCES reviews(review_id),
    order_date TIMESTAMPTZ NOT NULL,
    total_amount DECIMAL(12, 2),
    status VARCHAR(50) DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create order_lines table
CREATE TABLE IF NOT EXISTS order_lines (
    order_line_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id),
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(12, 2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_quantity_positive CHECK (quantity > 0)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_review_id ON orders(review_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_order_lines_order_id ON order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_product_id ON order_lines(product_id);

-- Add trigger to update last_updated timestamp for customers
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

-- Add comments for documentation
COMMENT ON TABLE customers IS 'Customer information extracted from reviews (Tiki user data)';
COMMENT ON TABLE orders IS 'Orders created from reviews - each review represents one order';
COMMENT ON TABLE order_lines IS 'Individual line items for each order';

COMMENT ON COLUMN orders.review_id IS 'Unique constraint prevents duplicate orders from same review';
COMMENT ON COLUMN orders.status IS 'Order status - default completed since review exists';
COMMENT ON COLUMN order_lines.quantity IS 'Product quantity - default 1 per review';
