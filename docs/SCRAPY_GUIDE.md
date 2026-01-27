# UIT Big Data Project - Scrapy Web Crawling

## 📋 Cấu trúc Project

```
src/app/
├── __init__.py
├── config.py                    # Configuration settings
├── manage.py                    # CLI management tool
│
├── models/                      # SQLAlchemy ORM Models
│   ├── __init__.py
│   ├── database.py             # Database connection
│   └── models.py               # Product, Review, Shop, etc.
│
├── schemas/                     # Pydantic Schemas
│   ├── __init__.py
│   ├── products.py
│   ├── reviews.py
│   ├── shops.py
│   ├── categories.py
│   └── prices.py
│
├── crawlers/                    # Scrapy Project
│   ├── settings.py             # Scrapy settings
│   ├── items.py                # Scrapy items
│   ├── middlewares.py          # Scrapy middlewares
│   ├── pipelines.py            # Item pipelines (Kafka producer)
│   └── spiders/
│       ├── __init__.py
│       ├── tiki_products.py    # Product spider
│       └── tiki_reviews.py     # Review spider
│
├── consumers/                   # Kafka Consumers
│   ├── __init__.py
│   ├── base_consumer.py        # Base consumer class
│   ├── product_consumer.py     # Product consumer
│   ├── review_consumer.py      # Review consumer
│   └── run_all.py              # Run all consumers
│
└── utils/                       # Utilities
    ├── __init__.py
    ├── logger.py               # Logging setup
    ├── kafka_utils.py          # Kafka helpers
    └── db_utils.py             # Database helpers
```

## 🚀 Cài đặt

### 1. Clone và cài đặt dependencies

```bash
cd /Users/tinhnguyen/Sites/UIT/12_cong_nghe_du_lieu_lon/project

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Cài đặt packages
pip install -r requirements.txt
```

### 2. Tạo file .env

```bash
cp .env.example .env
# Edit .env nếu cần thay đổi cấu hình
```

### 3. Khởi động Docker services

```bash
docker-compose up -d
```

### 4. Kiểm tra kết nối

```bash
# Sử dụng CLI tool
python src/manage.py check
```

Output:
```
🔍 Checking system connections...

📊 PostgreSQL:
✓ Database connection successful

Table statistics:
  - products: 0 rows
  - reviews: 0 rows
  - shops: 0 rows
  ...

📨 Kafka:
✓ Kafka connection successful
```

### 5. Khởi tạo database

```bash
python src/manage.py init-db
```

### 6. Tạo Kafka topics

```bash
python src/manage.py create-kafka-topics
```

## 📝 Sử dụng

### 1. Crawl Products

```bash
# Crawl 10 pages từ category Electronics (1789)
python src/manage.py crawl-products --category-id 1789 --max-pages 10

# Hoặc sử dụng Scrapy trực tiếp
cd src
scrapy crawl tiki_products -a category_id=1789 -a max_pages=10
```

### 2. Crawl Reviews

```bash
# Crawl reviews cho products (comma-separated IDs)
python src/manage.py crawl-reviews --product-ids "123456,789012" --max-pages 5

# Hoặc sử dụng Scrapy trực tiếp
cd src
scrapy crawl tiki_reviews -a product_ids="123456,789012" -a max_pages=5
```

### 3. Chạy Kafka Consumers

```bash
# Chạy tất cả consumers
python src/manage.py start-consumers --consumer all

# Hoặc chạy từng consumer riêng
python src/manage.py start-consumers --consumer products
python src/manage.py start-consumers --consumer reviews
```

### 4. Xem thống kê

```bash
python src/manage.py stats
```

## 🔄 Data Flow

```
┌─────────────────┐
│  Scrapy Spider  │
│  (tiki_products)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│ Kafka Producer  │─────▶│ Kafka Topic  │
│   (Pipeline)    │      │uit-products  │
└─────────────────┘      └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │   Consumer   │
                         │  (products)  │
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │  PostgreSQL  │
                         │ (TimescaleDB)│
                         └──────────────┘
```

## 📊 Kafka Topics

| Topic | Partitions | Description |
|-------|-----------|-------------|
| `uit-products` | 3 | Product data |
| `uit-reviews` | 3 | Review data |
| `uit-prices` | 3 | Price history |
| `uit-shops` | 1 | Shop/seller data |

## 🎯 Spider Options

### Product Spider

```bash
scrapy crawl tiki_products \
    -a category_id=1789 \      # Category ID (default: 1789 - Electronics)
    -a max_pages=10            # Max pages to crawl (default: 10)
```

**Tiki Category IDs:**
- 1789: Điện thoại - Máy tính bảng
- 1520: Laptop
- 1846: Máy ảnh
- 1882: Đồng hồ thông minh
- 27498: Tivi
- 1801: Tai nghe

### Review Spider

```bash
scrapy crawl tiki_reviews \
    -a product_ids="12345,67890" \  # Comma-separated product IDs
    -a max_pages=5                   # Max pages per product (default: 5)
```

## 🛠️ CLI Commands

```bash
# Check system
python src/manage.py check

# Initialize database
python src/manage.py init-db
python src/manage.py init-db --reset  # Drop and recreate

# Create Kafka topics
python src/manage.py create-kafka-topics

# Crawl data
python src/manage.py crawl-products --category-id 1789 --max-pages 10
python src/manage.py crawl-reviews --product-ids "123,456" --max-pages 5

# Start consumers
python src/manage.py start-consumers --consumer all
python src/manage.py start-consumers --consumer products
python src/manage.py start-consumers --consumer reviews

# View statistics
python src/manage.py stats
```

## 📦 Database Schema

### Products
- product_id (PK)
- name, description, url, image_url
- shop_id (FK), category_id (FK)
- rating, sold_count
- first_seen, last_updated

### Reviews
- review_id (PK)
- product_id (FK)
- user_name, rating, comment
- has_images, helpful_count
- created_at, crawled_at

### Product Prices (TimescaleDB Hypertable)
- product_id (PK)
- price, original_price, discount_percent
- stock_available
- timestamp (PK)

### Shops
- shop_id (PK)
- shop_name, rating, response_rate
- follower_count, is_official
- created_at, last_updated

## 🔍 Monitoring

### Conduktor Console
- URL: http://localhost:8081
- View Kafka topics, messages, consumer groups

### Metabase
- URL: http://localhost:3000
- Create dashboards, visualizations

### PostgreSQL
```bash
docker exec -it uit-bd-postgres psql -U uit_user -d uit_analytics
```

## 🐛 Debugging

### View Scrapy logs
```bash
tail -f logs/scrapy.log
```

### View consumer logs
```bash
tail -f logs/consumers.log
```

### Check Kafka messages
```bash
# List topics
docker exec -it uit-bd-kafka kafka-topics --bootstrap-server localhost:9092 --list

# Consume messages
docker exec -it uit-bd-kafka kafka-console-consumer \
    --bootstrap-server localhost:9092 \
    --topic uit-products \
    --from-beginning
```

## 🎓 Next Steps

1. **Implement Sentiment Analysis**
   - Add sentiment consumer
   - Use Vietnamese NLP (underthesea)
   - Save to review_sentiment table

2. **Add Apache Airflow**
   - Schedule crawlers
   - Monitor pipelines
   - Handle failures

3. **Create API Layer**
   - FastAPI for REST endpoints
   - Query products, reviews
   - Trigger crawls

4. **Build Dashboards**
   - Product rankings
   - Price trends
   - Sentiment analysis

## 📚 Resources

- [Scrapy Documentation](https://docs.scrapy.org/)
- [Kafka Python](https://docs.confluent.io/kafka-clients/python/current/overview.html)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [TimescaleDB](https://docs.timescale.com/)
