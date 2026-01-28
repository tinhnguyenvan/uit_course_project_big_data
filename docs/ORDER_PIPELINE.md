# Order Pipeline Documentation

## Overview
Complete pipeline implementation following the "pipeline principle" (đường ống) - each stage processes data and pushes to the next Kafka topic for the next consumer.

## Architecture

```
Crawler/ProductConsumer
    ↓ (uit-products topic)
ProductDetailConsumer
    ↓ (uit-product-detail topic)  
ReviewFetchConsumer
    ↓ (uit-review-fetch topic)
ReviewConsumer
    ↓ (uit-review-detail topic → saves review)
    ↓ (uit-orders topic → NEW!)
OrderConsumer
    ↓ (creates customers, orders, order_lines)
    ↓ (saves to database)
```

## Pipeline Flow

### 1. Product → Product Detail → Review Fetch → Review Detail
- ProductConsumer receives products from crawler
- Pushes to `uit-product-detail` topic
- ProductDetailConsumer fetches product details from Tiki API
- Pushes to `uit-review-fetch` topic
- ReviewFetchConsumer fetches reviews with pagination (5 per page)
- Pushes each individual review to `uit-review-detail` topic

### 2. Review Detail → Order Creation (NEW!)
- ReviewConsumer processes individual reviews
- Saves review to database
- **Pushes order message to `uit-orders` topic**
- OrderConsumer reads from `uit-orders` topic
- Creates/updates customer
- Creates order (linked to review via unique review_id)
- Creates order_line with product details
- Saves all to database

## Database Schema

### customers
```sql
CREATE TABLE customers (
    customer_id BIGINT PRIMARY KEY,          -- Tiki user ID
    customer_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW()
);
```

### orders
```sql
CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    review_id BIGINT NOT NULL UNIQUE REFERENCES reviews(review_id),  -- Prevents duplicates
    order_date TIMESTAMPTZ NOT NULL,
    total_amount DECIMAL(12, 2),
    status VARCHAR(50) DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### order_lines
```sql
CREATE TABLE order_lines (
    order_line_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id),
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(12, 2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Order Message Format

When ReviewConsumer saves a review, it pushes this message to `uit-orders` topic:

```json
{
    "review_id": 12345678,
    "product_id": 276388548,
    "customer_id": 9876543,           // Tiki user ID
    "customer_name": "John Doe",       // From review created_by.full_name
    "order_date": "2026-01-28T10:30:00",
    "rating": 5
}
```

## Key Features

### Duplicate Prevention
- **orders.review_id**: UNIQUE constraint - each review creates only ONE order
- **OrderConsumer**: Checks for existing orders before creating
- **ReviewConsumer**: Only processes new reviews
- **Customer**: Uses Tiki user ID, updates name if changed

### Data Flow
- Each review = 1 order (assumption: reviewers bought the product)
- Order quantity = 1 (default)
- Order status = 'completed' (since review exists, product was delivered)
- Unit price fetched from `product_prices` table (latest price)
- Total amount = unit_price × quantity

## Running the Pipeline

### Start All Consumers (5 parallel processes)
```bash
docker exec uit-bd-consumers python src/manage.py consumers start-all
```

This starts:
1. ProductConsumer ([PRODUCT])
2. ProductDetailConsumer ([PRODUCT-DETAIL])
3. ReviewFetchConsumer ([REVIEW-FETCH])
4. ReviewConsumer ([REVIEW])
5. **OrderConsumer ([ORDER])** ← NEW!

### Test Order Pipeline
```bash
# Trigger pipeline for a product
docker exec uit-bd-consumers python src/test_order_pipeline.py

# Monitor order creation
docker-compose logs -f consumers | grep -E '\[ORDER\]|\[REVIEW\]'
```

### Verify Orders Created
```sql
-- Check customer count
SELECT COUNT(*) FROM customers;

-- Check order count  
SELECT COUNT(*) FROM orders;

-- Check order lines
SELECT COUNT(*) FROM order_lines;

-- View sample orders
SELECT o.order_id, c.customer_name, p.name as product_name, 
       ol.quantity, ol.unit_price, o.total_amount, o.order_date
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_lines ol ON o.order_id = ol.order_id
JOIN products p ON ol.product_id = p.product_id
LIMIT 10;
```

## Files Created/Modified

### New Files
- `src/app/consumers/order_consumer.py` - OrderConsumer implementation
- `src/test_order_pipeline.py` - Test script to trigger complete pipeline
- `docker/postgres/migrations/004_add_order_tables.sql` - Database migration

### Modified Files
- `src/app/models/models.py` - Added Customer, Order, OrderLine models
- `src/app/models/__init__.py` - Export new models
- `src/app/config.py` - Added KAFKA_TOPIC_ORDERS
- `src/app/consumers/review_consumer.py` - Added Kafka producer, pushes to order topic
- `src/app/consumers/run_all.py` - Added OrderConsumer to parallel processing

## Logic Highlights

### OrderConsumer._ensure_customer()
```python
def _ensure_customer(self, customer_id: int, customer_name: str):
    """Create customer if not exists, update name if changed"""
    customer = self.db.query(Customer).filter_by(customer_id=customer_id).first()
    if not customer:
        customer = Customer(customer_id=customer_id, customer_name=customer_name)
        self.db.add(customer)
        self.db.flush()
        logger.info(f"Created new customer {customer_id}: {customer_name}")
    else:
        if customer.customer_name != customer_name:
            customer.customer_name = customer_name
            self.db.flush()
    return customer
```

### OrderConsumer.process_order()
```python
def process_order(self, data: dict) -> bool:
    """Process order message and create order with order lines"""
    
    # Check for duplicate order (unique review_id constraint)
    existing_order = self.db.query(Order).filter_by(review_id=review_id).first()
    if existing_order:
        logger.debug(f"Order for review {review_id} already exists, skipping")
        return True
    
    # Ensure customer exists (create if needed)
    customer = self._ensure_customer(customer_id, customer_name)
    
    # Get product price from product_prices table
    unit_price = self._get_product_price(product_id)
    
    # Create order
    order = Order(
        customer_id=customer_id,
        review_id=review_id,
        order_date=order_date,
        total_amount=unit_price * quantity,
        status='completed'
    )
    self.db.add(order)
    self.db.flush()  # Get order_id
    
    # Create order line
    order_line = OrderLine(
        order_id=order.order_id,
        product_id=product_id,
        quantity=1,
        unit_price=unit_price
    )
    self.db.add(order_line)
    self.db.commit()
```

## Kafka Topics Summary

| Topic | Producer | Consumer | Purpose |
|-------|----------|----------|---------|
| `uit-products` | Crawler | ProductConsumer | Raw product data |
| `uit-product-detail` | ProductConsumer | ProductDetailConsumer | Product IDs to enrich |
| `uit-review-fetch` | ProductDetailConsumer | ReviewFetchConsumer | Products needing review fetch |
| `uit-review-detail` | ReviewFetchConsumer | ReviewConsumer | Individual review details |
| `uit-orders` | **ReviewConsumer** | **OrderConsumer** | **Order creation from reviews** |

## Performance Notes

- **Parallel Processing**: 5 consumer processes running concurrently
- **Duplicate Prevention**: Database constraints + application logic
- **Error Handling**: IntegrityError caught and treated as success (order exists)
- **Transaction Safety**: Uses db.flush() for same-transaction entity availability
- **Price Lookup**: Latest price from product_prices hypertable

## Example Workflow

1. Crawler pushes product 276388548 to `uit-products`
2. ProductConsumer saves product, pushes to `uit-product-detail`
3. ProductDetailConsumer fetches details, pushes to `uit-review-fetch`
4. ReviewFetchConsumer fetches 223 reviews (45 pages × 5 reviews), pushes each to `uit-review-detail`
5. ReviewConsumer processes 223 reviews:
   - Saves each review to database
   - Pushes 223 order messages to `uit-orders`
6. OrderConsumer processes 223 orders:
   - Creates N customers (unique by Tiki user ID)
   - Creates 223 orders (one per review)
   - Creates 223 order_lines

**Result**: Complete order history derived from product reviews!

## Migration Notes

To apply the migration manually:
```bash
docker cp docker/postgres/migrations/004_add_order_tables.sql uit-bd-postgres:/tmp/
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -f /tmp/004_add_order_tables.sql
```

Restart consumers to activate:
```bash
docker-compose restart consumers
```
