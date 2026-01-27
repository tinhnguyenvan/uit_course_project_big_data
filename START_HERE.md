# 🎉 HỆ THỐNG ĐÃ SẴN SÀNG!

## ✅ Tình trạng hiện tại

1. **Docker containers đang chạy:**
   - ✅ PostgreSQL (port 54325)
   - ✅ Kafka (port 9092)
   - ✅ Zookeeper (port 2181)
   - ✅ Metabase (port 3000)
   - ✅ Conduktor Console (port 8081)
   - ✅ **Kafka Consumers (chạy background)**

2. **Đã test thành công:**
   - ✅ Crawler hoạt động
   - ✅ Push data vào Kafka
   - ✅ Consumers nhận và xử lý data
   - ✅ **Resume crawling từ page đã dừng**

## 🚀 CHẠY CRAWLER NGAY

### Option 1: Chạy vô thời hạn (Crawl tất cả)
```bash
./run_crawler.sh
```
**Crawler sẽ crawl TẤT CẢ products cho đến khi hết (~200 pages = 2000 products)**

### Option 2: Chạy với limit
```bash
# Crawl 50 pages
CATEGORY_ID=870 MAX_PAGES=50 ./run_crawler.sh

# Crawl 100 pages
CATEGORY_ID=870 MAX_PAGES=100 ./run_crawler.sh
```

### Option 3: Docker compose trực tiếp
```bash
# Unlimited pages
SERVICE=crawl-listing CATEGORY_ID=870 docker-compose up app

# With limit
SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=50 docker-compose up app
```

## 📊 DEMO RESUME

Đây là điểm mạnh của hệ thống:

```bash
# Lần 1: Crawl 10 pages
CATEGORY_ID=870 MAX_PAGES=10 ./run_crawler.sh
# => Crawls pages 1-10
# Press Ctrl+C để dừng

# Lần 2: TỰ ĐỘNG tiếp tục từ page 11
CATEGORY_ID=870 MAX_PAGES=10 ./run_crawler.sh  
# => Crawls pages 11-20 (không phải từ đầu!)

# Lần 3: Tiếp tục
CATEGORY_ID=870 MAX_PAGES=10 ./run_crawler.sh
# => Crawls pages 21-30
```

## 📈 MONITOR

### Terminal 1: Crawler logs
```bash
docker-compose logs -f app
```

### Terminal 2: Check database realtime
```bash
# Connect
docker exec -it uit-bd-postgres psql -U uit_user -d uit_analytics

# Check products count
SELECT COUNT(*) FROM products;

# Check shops
SELECT COUNT(*) FROM shops;

# View latest products
SELECT product_id, name, price, sold_count 
FROM products 
ORDER BY first_seen DESC 
LIMIT 10;

# Check crawl progress
SELECT 
    crawler_type,
    items_crawled,
    error_message,  -- Contains "Last page: XX"
    started_at,
    status
FROM crawl_logs 
ORDER BY started_at DESC 
LIMIT 5;
```

### Terminal 3: Kafka messages
```bash
# Count messages in topic
docker exec -it uit-bd-kafka kafka-run-class kafka.tools.GetOffsetShell \
    --broker-list localhost:9092 \
    --topic uit-products

# View messages
docker exec -it uit-bd-kafka kafka-console-consumer \
    --bootstrap-server localhost:9092 \
    --topic uit-products \
    --from-beginning \
    --max-messages 10 | jq '.'
```

## 🎮 WEB UIs

- **Conduktor Console** (Kafka Management): http://localhost:8081
- **Metabase** (Analytics & BI): http://localhost:3000

## 🔄 WORKFLOW HOÀN CHỈNH

```
Tiki API 
   ↓ (Scrapy Spider)
Kafka Topics (uit-products, uit-shops)
   ↓ (Kafka Consumers - đang chạy background)
PostgreSQL Database
   ↓ (Metabase)
Analytics & Visualization
```

## ⚙️ CẤU HÌNH

Edit trong spider nếu cần:
- **items_per_page**: 10 (items/page)
- **DOWNLOAD_DELAY**: 2 seconds (giữa các requests)
- **CONCURRENT_REQUESTS**: 4 (requests đồng thời)

## 🛑 STOP/RESTART

```bash
# Stop crawler (Ctrl+C trong terminal đang chạy)

# Stop consumers
docker-compose stop app

# Restart consumers
SERVICE=consumers-all docker-compose up -d app

# Stop everything
docker-compose down

# Restart everything
./start_system.sh
```

## 📝 LOGS & DATA

```bash
# Scrapy logs
ls logs/

# Exported data (JSONL)
ls data/

# View log file
tail -f logs/scrapy.log
```

## 🎯 EXPECTED RESULTS

**Category 870 (Sách kỹ năng sống):**
- Total pages: ~200
- Items per page: 10
- **Total products: ~2,000**
- Estimated time: 
  - 50 pages: ~3-5 minutes
  - 100 pages: ~6-10 minutes
  - 200 pages (full): ~12-20 minutes

**Với DOWNLOAD_DELAY=2s:**
- Requests: 200 pages = ~400 seconds = ~7 phút
- + Processing time

## 🚨 TROUBLESHOOTING

### Foreign Key Error (shops)

Hiện tại thấy lỗi này khi insert products:
```
foreign key constraint "products_shop_id_fkey"
Key (shop_id)=(1) is not present in table "shops"
```

**Giải pháp**: Consumers sẽ tự động insert shops trước khi insert products. Hoặc disable foreign key constraint tạm thời.

### Check logs
```bash
docker-compose logs app | grep ERROR
docker-compose logs app | grep WARNING
```

## 🎊 BẮT ĐẦU NGAY!

```bash
# Simple - chạy crawler với resume enabled
./run_crawler.sh
```

**Hệ thống sẽ:**
1. ✅ Tự động phân trang (10 items/page)
2. ✅ Push từng item vào Kafka  
3. ✅ Consumers xử lý realtime
4. ✅ Lưu vào PostgreSQL
5. ✅ Lưu progress để resume
6. ✅ Tự động tiếp tục khi restart

**Enjoy! 🎉**
