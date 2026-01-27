# 🕐 Cronjob Setup - Tự động chạy Crawler

## 📋 Tổng quan

Hệ thống hỗ trợ chạy crawler tự động theo lịch sử dụng cron trong Docker container.

## 🚀 Cách sử dụng

### Option 1: Chạy Cron Service riêng (Khuyến nghị)

```bash
# Start cron service (sẽ chạy crawler theo schedule)
SERVICE=cron docker-compose up -d app

# Check cron logs
docker-compose logs -f app
tail -f logs/cron.log
```

### Option 2: Docker Compose với cron service

Thêm vào `docker-compose.yml`:

```yaml
  # Cron service for scheduled crawling
  cron:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: uit-bd-cron
    depends_on:
      kafka:
        condition: service_healthy
      postgres:
        condition: service_healthy
    environment:
      # Same as app service
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: uit_analytics
      POSTGRES_USER: uit_user
      POSTGRES_PASSWORD: uit_password
      KAFKA_BOOTSTRAP_SERVERS: kafka:29092
      KAFKA_TOPIC_PRODUCTS: uit-products
      KAFKA_TOPIC_REVIEWS: uit-reviews
      KAFKA_TOPIC_PRICES: uit-prices
      KAFKA_TOPIC_SHOPS: uit-shops
      SERVICE: cron
    volumes:
      - ./src:/app/src
      - ./logs:/app/logs
      - ./data:/app/data
    networks:
      - uit-network
    restart: always
```

Sau đó:
```bash
docker-compose up -d cron
```

## ⚙️ Cấu hình Crontab

Edit file `docker/crontab`:

```cron
# Run every 6 hours (crawl 50 pages)
0 */6 * * * cd /app && SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=50 /app/docker/cron-wrapper.sh >> /app/logs/cron.log 2>&1

# Run daily at 2 AM (crawl 100 pages)
0 2 * * * cd /app && SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=100 /app/docker/cron-wrapper.sh >> /app/logs/cron-daily.log 2>&1

# Run every hour (crawl 10 pages) 
0 * * * * cd /app && SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=10 /app/docker/cron-wrapper.sh >> /app/logs/cron-hourly.log 2>&1
```

### Cron Format

```
* * * * * command
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, Sunday=0 or 7)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

### Ví dụ Schedule

```bash
# Every 30 minutes
*/30 * * * * command

# Every 2 hours
0 */2 * * * command

# Every day at 3 AM
0 3 * * * command

# Every Monday at 9 AM
0 9 * * 1 command

# Every 1st of month at midnight
0 0 1 * * command

# Multiple times a day (6 AM, 12 PM, 6 PM)
0 6,12,18 * * * command
```

## 📊 Multiple Categories

Crawl nhiều categories:

```cron
# Sách kỹ năng sống - Every 6 hours
0 */6 * * * cd /app && SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=50 /app/docker/cron-wrapper.sh >> /app/logs/cron-870.log 2>&1

# Điện thoại - Every 4 hours
0 */4 * * * cd /app && SERVICE=crawl-listing CATEGORY_ID=1789 MAX_PAGES=30 /app/docker/cron-wrapper.sh >> /app/logs/cron-1789.log 2>&1

# Laptop - Every 8 hours
0 */8 * * * cd /app && SERVICE=crawl-listing CATEGORY_ID=1520 MAX_PAGES=40 /app/docker/cron-wrapper.sh >> /app/logs/cron-1520.log 2>&1
```

## 🔧 Rebuild sau khi thay đổi

```bash
# Rebuild container với cron config mới
docker-compose build app

# Restart cron service
SERVICE=cron docker-compose up -d app
```

## 📝 Monitor Cron Jobs

### Check logs

```bash
# Cron service logs
docker-compose logs -f app

# Crawler logs from cron
tail -f logs/cron.log
tail -f logs/cron-870.log

# All cron logs
tail -f logs/cron*.log
```

### Check crontab

```bash
# Exec into container
docker exec -it uit-bd-app bash

# View crontab
crontab -l

# Check cron status
service cron status

# View cron logs
tail -f /var/log/cron.log
```

### Database check

```bash
docker exec -it uit-bd-postgres psql -U uit_user -d uit_analytics

# Check recent crawls
SELECT 
    crawler_type,
    items_crawled,
    status,
    started_at,
    completed_at,
    EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_seconds
FROM crawl_logs 
ORDER BY started_at DESC 
LIMIT 10;

# Check products per hour
SELECT 
    DATE_TRUNC('hour', first_seen) as hour,
    COUNT(*) as products_count
FROM products
WHERE first_seen > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;
```

## 🎯 Production Schedule Khuyến nghị

### Light crawling (Ít resource)
```cron
# Every 6 hours - 50 pages
0 */6 * * * cd /app && SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=50 /app/docker/cron-wrapper.sh >> /app/logs/cron.log 2>&1
```

### Medium crawling (Vừa phải)
```cron
# Every 4 hours - 100 pages
0 */4 * * * cd /app && SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=100 /app/docker/cron-wrapper.sh >> /app/logs/cron.log 2>&1
```

### Heavy crawling (Nhiều data)
```cron
# Every 2 hours - 200 pages
0 */2 * * * cd /app && SERVICE=crawl-listing CATEGORY_ID=870 MAX_PAGES=200 /app/docker/cron-wrapper.sh >> /app/logs/cron.log 2>&1
```

### Full refresh daily
```cron
# Daily at 3 AM - crawl all (no MAX_PAGES)
0 3 * * * cd /app && SERVICE=crawl-listing CATEGORY_ID=870 /app/docker/cron-wrapper.sh >> /app/logs/cron-full.log 2>&1
```

## 🛑 Stop/Disable Cron

```bash
# Stop cron container
docker-compose stop app

# Disable specific job (comment out in crontab)
# Edit docker/crontab and add # before the line

# Rebuild
docker-compose build app
SERVICE=cron docker-compose up -d app
```

## 🚨 Troubleshooting

### Cron không chạy

```bash
# Check cron service
docker exec -it uit-bd-app service cron status

# Check cron logs
docker exec -it uit-bd-app tail -f /var/log/cron.log

# Manually test cron command
docker exec -it uit-bd-app /app/docker/cron-wrapper.sh
```

### Permission issues

```bash
# Fix crontab permissions
docker exec -it uit-bd-app chmod 0644 /etc/cron.d/tiki-crawler

# Fix script permissions
docker exec -it uit-bd-app chmod +x /app/docker/cron-wrapper.sh
```

### Environment variables không load

Đảm bảo `cron-wrapper.sh` load environment variables từ `.env` file.

## 📈 Best Practices

1. **Start small**: Bắt đầu với schedule nhỏ (every 6 hours, 50 pages)
2. **Monitor resources**: Check CPU, memory usage
3. **Log rotation**: Setup logrotate để không đầy disk
4. **Alert on failures**: Setup monitoring/alerting
5. **Resume enabled**: Luôn dùng `resume=true` để tránh duplicate
6. **Stagger schedules**: Đừng chạy nhiều categories cùng lúc

## 🎊 Quick Start

```bash
# 1. Build with cron support
docker-compose build app

# 2. Start consumers (if not running)
SERVICE=consumers-all docker-compose up -d app

# 3. Start cron service
SERVICE=cron docker-compose up -d app

# 4. Check it's working
docker-compose logs -f app
tail -f logs/cron.log
```

**Hệ thống sẽ tự động crawl theo lịch! 🎉**
