# ⚡ QUICK START - Cron Auto Crawler

## 🚀 Start ngay (1 command)

```bash
# Start cron + consumers
SERVICE=cron docker-compose up -d app && \
sleep 2 && \
docker-compose run -d --name uit-consumers -e SERVICE=consumers-all app

# Hoặc riêng rẽ
SERVICE=cron docker-compose up -d app           # Cron
SERVICE=consumers-all docker-compose up -d app  # Consumers
```

## 📊 Monitor

```bash
# View logs realtime
docker-compose logs -f app

# Check crawler logs (mỗi 2 phút sẽ có log mới)
docker exec uit-bd-app tail -f /app/logs/cron-crawler.log

# Check database
docker exec -it uit-bd-postgres psql -U uit_user -d uit_analytics -c "SELECT COUNT(*) FROM products;"
```

## ⏱️ Schedule hiện tại

- **Crawler**: Mỗi 2 phút (10 pages/lần)
- **Heartbeat**: Mỗi 5 phút (check cron alive)

## 🔧 Thay đổi schedule

Edit `docker/crontab` → Build lại:
```bash
vim docker/crontab
docker-compose build app
SERVICE=cron docker-compose up -d app
```

## 📈 Expected Results

- Mỗi 2 phút: ~100 products
- Mỗi giờ: ~3,000 products
- Mỗi ngày: ~72,000 products

## 🛑 Stop

```bash
docker-compose stop app
```

## ✅ Current Status

- ✅ Cron đang chạy
- ✅ Schedule: Mỗi 2 phút
- ✅ Resume enabled
- ✅ Logs: `/app/logs/cron-*.log`

Xem chi tiết: [CRON_GUIDE.md](CRON_GUIDE.md)
