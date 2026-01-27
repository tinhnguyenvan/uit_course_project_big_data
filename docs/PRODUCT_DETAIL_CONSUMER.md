# Product Detail Consumer - System Documentation

## Overview
This document describes the product detail enrichment system that fetches detailed product information from Tiki API and updates the database.

## System Architecture

### Workflow
```
Tiki Listing Crawler
  → Kafka Topic: uit-products
    → ProductConsumer
      → Database: products table (basic info)
      → Kafka Topic: uit-product-detail (push product_id + spid)
        → ProductDetailConsumer
          → Tiki Product Detail API
          → Database: products table (detailed info)
```

## Components

### 1. ProductConsumer
**File**: `src/app/consumers/product_consumer.py`

**Responsibilities**:
- Consumes messages from `uit-products` topic
- Saves basic product information to database
- Pushes product_id and spid to `uit-product-detail` topic for detail enrichment

**Key Changes**:
- Added Kafka producer for `uit-product-detail` topic
- Method `_push_to_detail_topic()` sends product info to detail topic after successful save
- Uses `confluent_kafka.Producer` library

### 2. ProductDetailConsumer
**File**: `src/app/consumers/product_detail_consumer.py`

**Responsibilities**:
- Consumes messages from `uit-product-detail` topic
- Fetches detailed product information from Tiki API
- Updates database with enriched data

**API Endpoint**:
```
https://tiki.vn/api/v2/products/{product_id}?platform=web&spid={spid}&version=3
```

**Data Fetched**:
- Basic info: name, url, image_url, description, rating
- Detail info: review_count, discount_rate, short_description
- Sold count: all_time_quantity_sold
- JSON data: authors, specifications, configurable_options
- Seller: current_seller.id
- Category: categories.id

### 3. Database Schema Updates

**New Columns Added to `products` table**:
```sql
-- Scalar fields
review_count         INTEGER DEFAULT 0
discount_rate        INTEGER DEFAULT 0
short_description    TEXT

-- JSON fields
authors              JSONB
specifications       JSONB
configurable_options JSONB
```

**Indexes Created**:
```sql
CREATE INDEX idx_products_review_count ON products(review_count DESC);
CREATE INDEX idx_products_discount_rate ON products(discount_rate DESC);
```

### 4. Configuration

**Config Files Updated**:
- `src/app/config.py`: Added `KAFKA_TOPIC_PRODUCT_DETAIL`
- `src/app/crawlers/settings.py`: Added `KAFKA_TOPIC_PRODUCT_DETAIL`

**Environment Variables**:
```bash
KAFKA_TOPIC_PRODUCT_DETAIL=uit-product-detail
```

### 5. Kafka Topics

**Topic Created**:
```bash
Topic: uit-product-detail
Partitions: 3
Replication Factor: 1
```

**Message Format**:
```json
{
  "product_id": 276388548,
  "spid": 214186190
}
```

## Running the System

### Start All Consumers
```bash
docker-compose up -d consumers
```

This starts 3 consumer processes:
1. **ProductConsumer**: uit-products → database + uit-product-detail
2. **ProductDetailConsumer**: uit-product-detail → Tiki API → database
3. **ReviewConsumer**: uit-reviews → database

### Manual Testing
```bash
# Test product detail fetch for a specific product
docker exec uit-bd-consumers python src/test_product_detail.py
```

### Check Logs
```bash
# All consumers
docker-compose logs -f consumers

# Filter for product detail activity
docker-compose logs consumers | grep -E "PRODUCT-DETAIL|detail topic"
```

## Data Verification

### Check Product Detail Data
```sql
-- View basic detail fields
SELECT 
    product_id, 
    name, 
    review_count, 
    discount_rate, 
    LEFT(short_description, 100) as short_desc
FROM products 
WHERE product_id = 276388548;

-- View JSON fields
SELECT 
    product_id,
    name,
    authors,
    specifications
FROM products 
WHERE product_id = 276388548;

-- Find products with complete detail data
SELECT 
    COUNT(*) 
FROM products 
WHERE review_count > 0 OR authors IS NOT NULL;
```

## Example Data

### Product 276388548 (Sách Tư Duy Nhanh Và Chậm)

**Basic Info**:
- Name: Sách Tư Duy Nhanh Và Chậm (Tái Bản)
- Rating: 4.7
- Sold Count: 3696

**Detail Info**:
- Review Count: 215
- Discount Rate: 34%
- Short Description: "Chúng ta nghĩ rằng mình là người ra quyết định lý trí..."

**JSON Data**:
- Authors: `[{"id": 14879, "name": "Daniel Kahneman", "slug": "daniel-kahneman"}]`
- Specifications: Contains book_version, publisher, publication_date, dimensions, etc.

## Error Handling

### ProductConsumer
- If detail producer fails to initialize, logs warning and skips pushing to detail topic
- Product data is still saved to database even if detail push fails

### ProductDetailConsumer
- Retries API requests with exponential backoff
- Logs errors if product not found or API fails
- Continues processing other messages even if one fails
- Uses requests.Session for connection pooling and retries

## Performance Considerations

### API Rate Limiting
- Uses single requests.Session for connection pooling
- Consider adding delay between API calls if rate limited
- Session headers mimic browser to avoid blocking

### Database Performance
- JSONB columns indexed for faster queries
- Bulk updates possible via upsert logic
- TimescaleDB for price history

### Kafka Performance
- 3 partitions for uit-product-detail topic for parallel processing
- Consumer group ensures no duplicate processing
- Manual commit for reliability

## Monitoring

### Key Metrics
```bash
# Topic lag
docker exec uit-bd-kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group product-detail-consumer-group

# Processing rate
docker-compose logs consumers | grep "Successfully updated detail" | wc -l

# Error rate
docker-compose logs consumers | grep ERROR | wc -l
```

### Database Stats
```sql
-- Products with detail data
SELECT 
    COUNT(*) as total_products,
    COUNT(CASE WHEN review_count > 0 THEN 1 END) as with_reviews,
    COUNT(CASE WHEN authors IS NOT NULL THEN 1 END) as with_authors,
    COUNT(CASE WHEN specifications IS NOT NULL THEN 1 END) as with_specs
FROM products;
```

## Future Improvements

1. **Batch Processing**: Fetch multiple products in parallel
2. **Caching**: Cache API responses to reduce duplicate calls
3. **Retry Logic**: Implement exponential backoff for failed API calls
4. **Dead Letter Queue**: Move failed messages to DLQ for later processing
5. **Schema Validation**: Validate API response against Pydantic models
6. **Monitoring Dashboard**: Real-time metrics for API calls and processing rate

## Troubleshooting

### No messages in uit-product-detail topic
- Check if ProductConsumer detail producer initialized successfully
- Verify Kafka connectivity: `docker exec uit-bd-kafka kafka-topics --list`
- Check logs: `docker-compose logs consumers | grep "detail producer"`

### ProductDetailConsumer not processing
- Verify consumer group active: Check Kafka consumer groups
- Check API accessibility: Try manual curl to Tiki API
- Review logs for errors: `docker-compose logs consumers | grep PRODUCT-DETAIL`

### Database not updating
- Check SQLAlchemy connection
- Verify model has new columns
- Check for database locks or constraints
- Review commit logic in consumer

## Contact

For issues or questions, check:
- Consumer logs: `docker-compose logs consumers`
- Database logs: `docker-compose logs postgres`
- Kafka logs: `docker-compose logs kafka`
