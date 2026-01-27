# 🕐 Cron Job - Tự động chạy Crawler

## ✅ ĐÃ CẤU HÌNH

**Cron schedule:** Chạy crawler **mỗi 2 phút** tự động

```bash
*/2 * * * * cd /app/src && scrapy crawl tiki_listing -a category_id=870 -a max_pages=10 -a resume=true
```

## 🚀 CHẠY CRON SERVICE

### Start cron (background mode)
```bash
SERVICE=cron docker-compose up -d app
```

### View logs realtime
```bash
docker-compose logs -f app
```

### Stop cron
```bash
docker-compose stop app
```

## 📊 MONITOR

### Check cron logs
```bash
# Crawler logs
docker exec -it uit-bd-app tail -f /app/logs/cron-crawler.log

# Heartbeat (kiểm tra cron còn sống)
docker exec -it uit-bd-app tail -f /app/logs/cron-heartbeat.log

# Tất cả logs
docker exec -it uit-bd-app tail -f /app/logs/cron-*.log
```

### Check crontab đang chạy
```bash
docker exec -it uit-bd-app crontab -l
```

## 📝 CẤU HÌNH CRON

File: `docker/crontab`

### Mỗi 2 phút (hiện tại)
```bash
*/2 * * * * [command]
```

### Mỗi 5 phút
```bash
*/5 * * * * [command]
```

### Mỗi 15 phút
```bash
*/15 * * * * [command]
```

### Mỗi 30 phút
```bash
*/30 * * * * [command]
```

### Mỗi giờ
```bash
0 * * * * [command]
```

### Mỗi 6 giờ
```bash
0 */6 * * * [command]
```

### Hàng ngày lúc 2 AM
```bash
0 2 * * * [command]
```

### Mỗi ngày lúc 8 AM và 8 PM
```bash
0 8,20 * * * [command]
```

## 🎯 USE CASES

### 1. Chạy background liên tục
```bash
# Start cron service
SERVICE=cron docker-compose up -d app

# Start consumers để xử lý data
SERVICE=consumers-all docker-compose up -d app

# Monitor
docker-compose logs -f app
```

### 2. Nhiều categories
Edit `docker/crontab`:
```bash
# Category 870 - Sách kỹ năng sống (mỗi 2 phút)
*/2 * * * * cd /app/src && scrapy crawl tiki_listing -a category_id=870 -a max_pages=10 -a resume=true >> /app/logs/cron-870.log 2>&1

# Category 1789 - Điện thoại (mỗi 5 phút)
*/5 * * * * cd /app/src && scrapy crawl tiki_listing -a category_id=1789 -a max_pages=20 -a resume=true >> /app/logs/cron-1789.log 2>&1

# Category 1520 - Laptop (mỗi 10 phút)
*/10 * * * * cd /app/src && scrapy crawl tiki_listing -a category_id=1520 -a max_pages=15 -a resume=true >> /app/logs/cron-1520.log 2>&1
```

### 3. Crawl vào giờ thấp điểm
```bash
# Chạy lúc 2 AM hàng ngày (crawl nhiều pages)
0 2 * * * cd /app/src && scrapy crawl tiki_listing -a category_id=870 -a max_pages=200 -a resume=true >> /app/logs/cron-night.log 2>&1

# Chạy mỗi 6 giờ
0 */6 * * * cd /app/src && scrapy crawl tiki_listing -a category_id=870 -a max_pages=50 -a resume=true >> /app/logs/cron-6h.log 2>&1
```

## 🔄 UPDATE CRON SCHEDULE

1. **Edit file:**
```bash
vim docker/crontab
```

2. **Rebuild container:**
```bash
docker-compose build app
```

3. **Restart cron:**
```bash
SERVICE=cron docker-compose up -d app
```

## 📊 KIỂM TRA HOẠT ĐỘNG

### Check database realtime
```bash
# Connect PostgreSQL
docker exec -it uit-bd-postgres psql -U uit_user -d uit_analytics

# Query
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM product_prices;

# View latest crawls
SELECT 
    crawler_type,
    items_crawled,
    error_message,
    started_at,
    status
FROM crawl_logs 
ORDER BY started_at DESC 
LIMIT 10;
```

### Watch products grow
```bash
# Watch count every 2 seconds
watch -n 2 'docker exec -it uit-bd-postgres psql -U uit_user -d uit_analytics -c "SELECT COUNT(*) FROM products;"'
```

## 🐛 TROUBLESHOOTING

### Cron không chạy
```bash
# Check cron process
docker exec -it uit-bd-app ps aux | grep cron

# Check crontab
docker exec -it uit-bd-app crontab -l

# Restart cron
SERVICE=cron docker-compose restart app
```

### View errors
```bash
# Check error logs
docker exec -it uit-bd-app tail -50 /app/logs/cron-crawler.log | grep ERROR

# Check full logs
docker exec -it uit-bd-app cat /app/logs/cron-crawler.log
```

### Test cron manually
```bash
# Run crawler command manually
docker exec -it uit-bd-app bash -c "cd /app/src && scrapy crawl tiki_listing -a category_id=870 -a max_pages=2 -a resume=true"
```

## 📈 PRODUCTION SETUP

### Recommended: Cron + Consumers

**Terminal 1: Cron**
```bash
SERVICE=cron docker-compose up -d app
```

**Terminal 2: Consumers**  
```bash
SERVICE=consumers-all docker-compose up -d app
```

**Monitor:**
```bash
docker-compose logs -f app
```

## 🎊 VÍ DỤ THỰC TẾ

**Với schedule mỗi 2 phút, crawl 10 pages/lần:**

- Mỗi lần chạy: 10 pages = 100 products
- Mỗi giờ: 30 lần × 100 = 3,000 products  
- Mỗi ngày: 24 × 3,000 = 72,000 products
- Mỗi tuần: ~500,000 products

**Lưu ý:** Điều chỉnh schedule và MAX_PAGES phù hợp với:
- Tốc độ cần thiết
- Tài nguyên server
- Rate limit của Tiki

## 📋 CHECKLIST PRODUCTION

- [x] Cron service đã chạy
- [ ] Consumers đã chạy
- [ ] Database có đủ space
- [ ] Monitoring alerts setup
- [ ] Backup strategy
- [ ] Log rotation configured
