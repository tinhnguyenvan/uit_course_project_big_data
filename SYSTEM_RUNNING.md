# 🎉 HỆ THỐNG ĐÃ HOẠT ĐỘNG 100%

## ✅ STATUS

```bash
docker-compose ps
```

**Running:**
- ✅ uit-bd-cron (Auto crawler mỗi 2 phút)
- ✅ uit-bd-consumers (Xử lý Kafka messages)
- ✅ uit-bd-kafka
- ✅ uit-bd-postgres
- ✅ uit-bd-zookeeper
- ✅ uit-bd-metabase
- ✅ uit-bd-conduktor-console

## 📊 KẾT QUẢ HIỆN TẠI

- **Products**: 140+
- **Prices**: 807+
- **Messages processed**: 600+
- **Cron schedule**: Mỗi 2 phút
- **Resume**: Enabled

## 🚀 COMMANDS

### Start tất cả
```bash
docker-compose up -d
```

### Start riêng từng service
```bash
# Cron (auto crawler)
docker-compose up -d cron

# Consumers (process Kafka)
docker-compose up -d consumers

# Infrastructure
docker-compose up -d kafka postgres zookeeper
```

### Stop
```bash
# Stop tất cả
docker-compose down

# Stop riêng lẻ
docker-compose stop cron
docker-compose stop consumers
```

### Logs
```bash
# Xem tất cả logs
docker-compose logs -f

# Riêng từng service
docker-compose logs -f cron
docker-compose logs -f consumers

# Crawler logs (từ cron)
docker exec uit-bd-cron tail -f /app/logs/cron-crawler.log

# Heartbeat
docker exec uit-bd-cron tail -f /app/logs/cron-heartbeat.log
```

### Check database
```bash
docker exec -it uit-bd-postgres psql -U uit_user -d uit_analytics

# Queries
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM product_prices;

SELECT product_id, name, rating, sold_count 
FROM products 
ORDER BY first_seen DESC 
LIMIT 10;
```

### Check Kafka
```bash
# Messages count
docker exec uit-bd-kafka kafka-run-class kafka.tools.GetOffsetShell \
    --broker-list localhost:9092 \
    --topic uit-products 2>/dev/null

# View messages
docker exec uit-bd-kafka kafka-console-consumer \
    --bootstrap-server localhost:9092 \
    --topic uit-products \
    --from-beginning \
    --max-messages 5
```

## 🔧 CONFIGURATION

### Thay đổi cron schedule

Edit `docker/crontab`:
```bash
vim docker/crontab

# Ví dụ: Mỗi 5 phút
*/5 * * * * cd /app/src && scrapy crawl tiki_listing ...

# Rebuild
docker-compose build cron
docker-compose up -d cron
```

### Thay đổi crawler settings

Edit `src/app/crawlers/settings.py`:
- `DOWNLOAD_DELAY`: Delay giữa requests
- `CONCURRENT_REQUESTS`: Số requests đồng thời

```bash
# Restart để apply
docker-compose restart cron
```

## 📈 MONITORING

### Web UIs
- **Metabase**: http://localhost:3000
- **Conduktor Console**: http://localhost:8081

### Watch database grow
```bash
watch -n 5 'docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "SELECT COUNT(*) FROM products;"'
```

### Check system health
```bash
# All containers
docker-compose ps

# Resource usage
docker stats

# Logs for errors
docker-compose logs | grep ERROR
```

## 🎯 WORKFLOW

**Hệ thống tự động:**

1. **Cron** chạy crawler mỗi 2 phút
2. Crawler crawl 10 pages (~100 products)
3. Push data vào **Kafka**
4. **Consumers** nhận và xử lý
5. Lưu vào **PostgreSQL**
6. Repeat...

**Expected growth:**
- Mỗi 2 phút: ~100 products
- Mỗi giờ: ~3,000 products
- Mỗi ngày: ~72,000 products

## 🛑 RESTART ALL

```bash
# Stop everything
docker-compose down

# Start infrastructure
docker-compose up -d kafka postgres zookeeper

# Wait 10 seconds
sleep 10

# Start cron + consumers
docker-compose up -d cron consumers

# Check
docker-compose ps
docker-compose logs -f
```

## 📋 QUICK CHECKS

```bash
# Are containers running?
docker-compose ps | grep -E "(cron|consumers)"

# Recent crawler activity?
docker exec uit-bd-cron tail -20 /app/logs/cron-crawler.log

# Consumers processing?
docker-compose logs consumers | tail -20

# Database growing?
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "SELECT COUNT(*) FROM products;"
```

## 🎊 EVERYTHING IS AUTOMATED!

Bạn không cần làm gì thêm. Hệ thống sẽ tự:
- ✅ Crawl data mỗi 2 phút
- ✅ Xử lý qua Kafka
- ✅ Lưu vào database
- ✅ Resume từ page đã crawl
- ✅ Restart tự động nếu crash

**Just monitor and enjoy! 🚀**
