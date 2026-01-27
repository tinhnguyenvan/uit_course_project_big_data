# 🚀 Quick Start - Running Crawler

## ✅ Setup đã hoàn tất

**Consumers đã chạy background** - sẵn sàng nhận data từ Kafka

## 🕷️ Chạy Crawler

### Option 1: Script tự động (Khuyến nghị)

```bash
# Chạy crawler với resume (unlimited pages)
./run_crawler.sh

# Hoặc chỉ định category và limit pages
CATEGORY_ID=870 MAX_PAGES=50 ./run_crawler.sh

# Disable resume (bắt đầu từ page 1)
RESUME=false ./run_crawler.sh
```

### Option 2: Docker Compose trực tiếp

```bash
# Crawl unlimited pages (đến khi hết)
SERVICE=crawl-listing CATEGORY_ID=870 docker-compose up app

# Crawl 100 pages
SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=100 docker-compose up app

# Disable resume
SERVICE=crawl-listing CATEGORY_ID=870 RESUME=false docker-compose up app
```

## 📊 Monitoring

### Terminal 1: Crawler logs
```bash
# Xem realtime logs của crawler
docker-compose logs -f app
```

### Terminal 2: Check database
```bash
# Connect PostgreSQL
docker exec -it uit-bd-postgres psql -U uit_user -d uit_analytics

# Queries
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM shops;
SELECT * FROM crawl_logs ORDER BY started_at DESC LIMIT 5;

# Check last crawled page
SELECT 
    crawler_type,
    items_crawled,
    error_message,
    status,
    started_at
FROM crawl_logs 
WHERE crawler_type LIKE 'tiki_listing%' 
ORDER BY started_at DESC 
LIMIT 3;
```

### Terminal 3: Kafka monitoring
```bash
# Count messages
docker exec -it uit-bd-kafka kafka-run-class kafka.tools.GetOffsetShell \
    --broker-list localhost:9092 \
    --topic uit-products

# View messages
docker exec -it uit-bd-kafka kafka-console-consumer \
    --bootstrap-server localhost:9092 \
    --topic uit-products \
    --from-beginning \
    --max-messages 5
```

## 🎮 Demo Resume Feature

```bash
# Step 1: Crawl 10 pages
CATEGORY_ID=870 MAX_PAGES=10 ./run_crawler.sh
# => Crawls pages 1-10

# Press Ctrl+C to stop

# Step 2: Resume crawling (next 10 pages)
CATEGORY_ID=870 MAX_PAGES=10 ./run_crawler.sh
# => Automatically continues from page 11-20

# Step 3: Resume again
CATEGORY_ID=870 MAX_PAGES=10 ./run_crawler.sh
# => Continues from page 21-30
```

## 🔥 Chạy crawler liên tục (Production Mode)

```bash
# Crawl tất cả products trong category (có thể mất nhiều giờ)
CATEGORY_ID=870 ./run_crawler.sh

# Crawler sẽ:
# ✅ Tự động phân trang
# ✅ Push từng item vào Kafka
# ✅ Lưu progress vào database
# ✅ Auto-resume nếu restart
```

## 🛑 Stop Crawler

```bash
# Press Ctrl+C trong terminal đang chạy crawler

# Hoặc force stop
docker-compose stop app
```

## 📈 Web UIs

- **Conduktor Console** (Kafka): http://localhost:8081
- **Metabase** (Analytics): http://localhost:3000

## 📝 Logs

```bash
# View all logs
docker-compose logs

# Only crawler logs
docker-compose logs app

# Follow logs
docker-compose logs -f app

# Last 100 lines
docker-compose logs --tail 100 app
```

## ⚙️ Configuration

Edit trong [docker-compose.yml](../docker-compose.yml):

```yaml
environment:
  CATEGORY_ID: ${CATEGORY_ID:-870}    # Default category
  MAX_PAGES: ${MAX_PAGES:-}           # Unlimited by default
  RESUME: ${RESUME:-true}             # Resume enabled
```

## 🐛 Troubleshooting

**Crawler không chạy:**
```bash
# Check app status
docker-compose ps app

# Restart app
docker-compose restart app
```

**Consumer không nhận data:**
```bash
# Check consumers
SERVICE=consumers-all docker-compose up -d app
docker-compose logs -f app
```

**Database connection error:**
```bash
# Check PostgreSQL
docker-compose ps postgres
docker-compose logs postgres
```

## 🎯 Current Status

✅ **Consumers running** - Background, listening for messages
🔄 **Ready to crawl** - Run `./run_crawler.sh` to start

## 📊 Expected Results

Với category 870 (Sách kỹ năng sống):
- Total pages: ~1000+ pages
- Items per page: 10
- Total products: ~10,000+
- Crawl time: ~5-10 hours (với delay 2s/request)
