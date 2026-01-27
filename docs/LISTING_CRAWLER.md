# Demo Tiki Listing Crawler với Resume

## 🎯 Tính năng

1. ✅ **Crawl từ API listing**: `https://tiki.vn/api/personalish/v1/blocks/listings`
2. ✅ **Phân trang tự động**: Limit 10 items/page
3. ✅ **Resume crawling**: Lưu trạng thái và tiếp tục từ page đã crawl
4. ✅ **Push Kafka**: Mỗi item được push vào Kafka topic
5. ✅ **Logging**: Lưu log crawl vào database

## 🚀 Sử dụng

### 1. Crawl với limit pages

```bash
# Crawl 10 pages đầu (category 870 - Sách kỹ năng sống)
SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=10 docker-compose up app

# Hoặc sử dụng CLI
python src/manage.py crawl-listing --category-id 870 --max-pages 10
```

### 2. Crawl với resume (tiếp tục từ page đã dừng)

```bash
# Lần 1: Crawl 10 pages
SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=10 docker-compose up app

# Stop crawler (Ctrl+C)

# Lần 2: Tiếp tục từ page 11
SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=10 docker-compose up app
# => Sẽ crawl từ page 11-20
```

### 3. Disable resume (bắt đầu từ page 1)

```bash
SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=10 RESUME=false docker-compose up app

# Hoặc CLI
python src/manage.py crawl-listing --category-id 870 --no-resume
```

### 4. Crawl unlimited (đến khi hết)

```bash
# Không set MAX_PAGES = crawl tất cả
SERVICE=crawl-listing CATEGORY_ID=870 docker-compose up app
```

## 📊 Workflow đầy đủ

### Terminal 1: Start Consumers
```bash
# Start consumers để nhận data từ Kafka
SERVICE=consumers-all docker-compose up -d app

# View logs
docker-compose logs -f app
```

### Terminal 2: Run Crawler
```bash
# Crawl 50 pages
SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=50 docker-compose up app
```

### Terminal 3: Monitor
```bash
# Check database
docker exec -it uit-bd-postgres psql -U uit_user -d uit_analytics

# Query products
SELECT COUNT(*) FROM products;

# Query crawl logs
SELECT * FROM crawl_logs ORDER BY started_at DESC LIMIT 5;

# Check last page crawled
SELECT error_message FROM crawl_logs 
WHERE crawler_type LIKE 'tiki_listing%' 
ORDER BY started_at DESC LIMIT 1;
```

## 🔍 API Response Structure

API trả về format như trong `list.json`:

```json
{
  "data": [
    {
      "id": 278997895,
      "name": "Sách Cờ Đỏ Cờ Xanh",
      "price": 172500,
      "original_price": 230000,
      "discount_rate": 25,
      "rating_average": 0,
      "quantity_sold": {"value": 18},
      "thumbnail_url": "https://...",
      "seller_id": 1,
      "primary_category_path": "1/2/8322/316/870/67945/67946"
    }
  ],
  "paging": {
    "current_page": 1,
    "total": 2000,
    "last_page": 1000,
    "per_page": 2
  }
}
```

## 📝 Resume Logic

Spider lưu trạng thái trong bảng `crawl_logs`:

```sql
-- Xem crawl logs
SELECT 
    log_id,
    crawler_type,
    status,
    items_crawled,
    error_message,  -- Chứa "Last page: 10"
    started_at,
    completed_at
FROM crawl_logs
WHERE crawler_type = 'tiki_listing_cat_870'
ORDER BY started_at DESC;
```

**Resume flow:**
1. Query `crawl_logs` để lấy last page
2. Parse từ `error_message`: `"Last page: 10"`
3. Tiếp tục từ page `11`

## 🎲 Test Resume

```bash
# Step 1: Crawl 5 pages
SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=5 docker-compose up app
# => Crawl pages 1-5

# Step 2: Crawl tiếp 5 pages
SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=5 docker-compose up app
# => Crawl pages 6-10

# Step 3: Reset và crawl lại từ đầu
SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=5 RESUME=false docker-compose up app
# => Crawl pages 1-5 lại
```

## 🗂️ Category IDs

**Sách:**
- 870: Sách kỹ năng sống
- 871: Sách tư duy
- 316: Sách thiếu nhi
- 8322: Sách tiếng Việt

**Điện tử:**
- 1789: Điện thoại
- 1520: Laptop
- 1846: Máy ảnh

## 📈 Monitoring Kafka

```bash
# List topics
docker exec -it uit-bd-kafka kafka-topics --bootstrap-server localhost:9092 --list

# View messages
docker exec -it uit-bd-kafka kafka-console-consumer \
    --bootstrap-server localhost:9092 \
    --topic uit-products \
    --from-beginning \
    --max-messages 10

# Conduktor UI
open http://localhost:8081
```

## ⚙️ Configuration

Edit trong spider:
- `items_per_page = 10` - Items per page
- `DOWNLOAD_DELAY = 2` - Delay giữa các requests
- `CONCURRENT_REQUESTS = 4` - Số requests đồng thời

## 🐛 Debug

```bash
# View Scrapy logs
docker-compose logs app | grep "tiki_listing"

# Check last crawled page
python src/manage.py shell
>>> from app.models import SessionLocal, CrawlLog
>>> db = SessionLocal()
>>> log = db.query(CrawlLog).filter(
...     CrawlLog.crawler_type == 'tiki_listing_cat_870'
... ).order_by(CrawlLog.started_at.desc()).first()
>>> print(log.error_message)
Last page: 10
```
