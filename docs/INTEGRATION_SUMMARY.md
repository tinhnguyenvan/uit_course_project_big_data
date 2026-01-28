# 📝 Tổng Kết Tích Hợp Crawl Categories với Cron

## ✅ Đã hoàn thành

### 1. Database & Model
- ✅ Tạo bảng `crawl_categories` với migration 005
- ✅ Model `CrawlCategory` trong SQLAlchemy
- ✅ 11 categories mẫu đã được insert
- ✅ Indexes và triggers tự động

### 2. Scripts & Commands
- ✅ `src/manage_crawl_categories.py` - CLI quản lý categories
- ✅ `src/crawl_from_categories.py` - Script cho cron job
- ✅ `python src/manage.py crawl-from-db` - Command mới trong manage.py
- ✅ `SERVICE=crawl-from-db` - Service mới trong entrypoint.sh

### 3. Cron Integration
- ✅ Cập nhật `docker/crontab` - Chạy mỗi 3 phút
- ✅ Cron tự động select category theo priority
- ✅ Auto-resume từ `last_crawled_page`
- ✅ Tracking tiến độ trong database

### 4. Documentation
- ✅ `docs/CRAWL_CATEGORIES.md` - Hướng dẫn đầy đủ
- ✅ `docs/QUICK_START_CRAWL.md` - Quick start guide
- ✅ SQL queries examples
- ✅ Troubleshooting guide

## 🎯 Cấu trúc hoàn chỉnh

```
project/
├── src/
│   ├── manage.py                      # Thêm command crawl-from-db
│   ├── manage_crawl_categories.py     # CLI quản lý categories (NEW)
│   ├── crawl_from_categories.py       # Script cho cron (NEW)
│   └── app/
│       └── models/
│           └── models.py              # Thêm CrawlCategory model
├── docker/
│   ├── crontab                        # Cập nhật: chạy mỗi 3 phút (UPDATED)
│   ├── entrypoint.sh                  # Thêm SERVICE=crawl-from-db (UPDATED)
│   ├── cron-wrapper.sh
│   └── postgres/
│       └── migrations/
│           └── 005_add_crawl_categories.sql  # Migration mới (NEW)
└── docs/
    ├── CRAWL_CATEGORIES.md            # Hướng dẫn chi tiết (NEW)
    └── QUICK_START_CRAWL.md           # Quick start (NEW)
```

## 🚀 Cách sử dụng

### A. Quản lý Categories (CLI)

```bash
# Xem danh sách
python src/manage_crawl_categories.py list

# Xem thống kê
python src/manage_crawl_categories.py stats

# Thêm category
python src/manage_crawl_categories.py add 1234 "Tên" "URL" --priority 8 --max-pages 50

# Cập nhật
python src/manage_crawl_categories.py update 1789 --priority 10

# Kích hoạt/Vô hiệu hóa
python src/manage_crawl_categories.py activate 1789
python src/manage_crawl_categories.py deactivate 1789

# Reset để crawl lại
python src/manage_crawl_categories.py reset 1789

# Xem category tiếp theo
python src/manage_crawl_categories.py next
```

### B. Chạy Crawler

#### Option 1: Manual (test)
```bash
# Trong container
docker compose run --rm app python src/manage.py crawl-from-db

# Limit 3 categories
docker compose run --rm app python src/manage.py crawl-from-db --limit 3

# Chỉ crawl pending
docker compose run --rm app python src/manage.py crawl-from-db --status pending
```

#### Option 2: Environment Variable
```bash
# Crawl từ database
SERVICE=crawl-from-db docker compose up app

# Với limit
SERVICE=crawl-from-db LIMIT=5 docker compose up app

# Với status filter
SERVICE=crawl-from-db STATUS=failed docker compose up app
```

#### Option 3: Cron Tự Động (Recommended)
```bash
# Start cron service
docker compose up -d cron

# Xem logs
docker compose logs -f cron

# Hoặc
docker exec -it uit-bd-app tail -f /app/logs/cron-crawler.log

# Stop cron
docker compose stop cron
```

### C. Theo dõi tiến độ

```bash
# Thống kê tổng quan
python src/manage_crawl_categories.py stats

# Chi tiết categories
python src/manage_crawl_categories.py list --active

# SQL query
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
SELECT 
    category_id, 
    category_name, 
    crawl_status, 
    priority,
    total_products_crawled,
    last_crawled_at
FROM crawl_categories 
WHERE is_active = true 
ORDER BY priority DESC;
"
```

## 🔄 Workflow Tự Động

```
┌─────────────────────────────────────────┐
│  Cron Job (Mỗi 3 phút)                 │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  src/crawl_from_categories.py           │
│  - Query active categories              │
│  - Select theo priority DESC            │
│  - Status: pending/failed trước         │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Update status → in_progress            │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Scrapy Crawler                         │
│  - category_id                          │
│  - max_pages (từ DB)                    │
│  - resume = true                        │
└───────────────┬─────────────────────────┘
                │
        ┌───────┴───────┐
        │               │
        ▼               ▼
┌─────────────┐  ┌──────────────┐
│  Success    │  │    Failed    │
│  status:    │  │    status:   │
│  completed  │  │    failed    │
│  update     │  │    save      │
│  timestamp  │  │    error     │
└─────────────┘  └──────────────┘
```

## 📊 Categories Mẫu

| ID | Tên | Priority | Max Pages | Status |
|----|-----|----------|-----------|--------|
| 8322 | Điện Thoại - Máy Tính Bảng | 10 | 50 | pending |
| 1789 | Điện Thoại Smartphone | 9 | 50 | pending |
| 1846 | Laptop - Máy Vi Tính - Linh kiện | 9 | 50 | pending |
| 1801 | Laptop | 9 | 50 | pending |
| 1795 | Máy Tính Bảng | 8 | 30 | pending |
| 8594 | Nhà Sách Tiki | 8 | 100 | pending |
| 871 | Văn học | 7 | 80 | pending |
| 316 | Sách kinh tế | 7 | 80 | pending |
| 1882 | Đồ chơi - Mẹ & Bé | 6 | 40 | pending |
| 2549 | Thời trang nữ | 5 | 40 | pending |
| 1686 | Thời trang nam | 5 | 40 | pending |

## 🎯 Tính năng chính

### 1. Auto-selection theo Priority
- Categories priority cao được crawl trước
- Pending/Failed được ưu tiên
- Sau đó crawl lại completed (cũ nhất trước)

### 2. Resume Capability
- Lưu `last_crawled_page` trong DB
- Nếu bị gián đoạn, tiếp tục từ trang cuối
- Không crawl lại data đã có

### 3. Progress Tracking
- `crawl_status`: pending → in_progress → completed/failed
- `total_products_crawled`: Đếm tổng sản phẩm
- `last_crawled_at`: Timestamp crawl cuối

### 4. Flexible Configuration
- `is_active`: Bật/tắt category
- `priority`: Điều chỉnh độ ưu tiên
- `max_pages`: Giới hạn pages mỗi category
- `notes`: Ghi chú, error messages

### 5. Error Handling
- Lỗi → status = 'failed'
- Error message → notes field
- Có thể reset để thử lại

## 📝 Cron Configuration

File: `docker/crontab`

```bash
# Crawl categories từ database mỗi 3 phút (auto-select theo priority)
*/3 * * * * cd /app && /usr/local/bin/python src/crawl_from_categories.py >> /app/logs/cron-crawler.log 2>&1

# Heartbeat log every 5 minutes
*/5 * * * * echo "[$(date)] Cron is alive" >> /app/logs/cron-heartbeat.log 2>&1
```

**Thay đổi từ:**
- Hardcode `category_id=870`
- Chạy mỗi 2 phút
- Max pages cố định

**Thành:**
- Auto-select từ database
- Chạy mỗi 3 phút (ít hơn để tránh overlap)
- Max pages từ config per category

## 🔧 Troubleshooting

### Cron không chạy
```bash
# Check container
docker compose ps cron

# Check crontab
docker exec -it uit-bd-app crontab -l

# Check logs
docker exec -it uit-bd-app tail -f /app/logs/cron-crawler.log
```

### Category bị failed
```bash
# Xem lỗi
python src/manage_crawl_categories.py list --status failed

# Reset
python src/manage_crawl_categories.py reset <category_id>
```

### Database không có categories
```bash
# Kiểm tra
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "SELECT COUNT(*) FROM crawl_categories;"

# Nếu trống, apply migration lại
docker cp docker/postgres/migrations/005_add_crawl_categories.sql uit-bd-postgres:/tmp/
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -f /tmp/005_add_crawl_categories.sql
```

## 🎓 Best Practices

1. **Priority Management**
   - 10: Rất quan trọng (Điện thoại, Laptop)
   - 7-9: Quan trọng (Sách, Tablet)
   - 4-6: Bình thường (Thời trang, Đồ chơi)
   - 1-3: Thấp (Categories ít quan trọng)

2. **Max Pages**
   - Dựa trên số lượng sản phẩm trong category
   - Categories lớn: 100 pages
   - Categories trung bình: 50 pages
   - Categories nhỏ: 30-40 pages

3. **Active Management**
   - Deactivate thay vì xóa (giữ lịch sử)
   - Reset định kỳ để re-crawl
   - Monitor failed categories

4. **Monitoring**
   - Check stats hàng ngày
   - Review failed categories
   - Adjust priority based on performance

## 📚 Tài liệu tham khảo

- [CRAWL_CATEGORIES.md](docs/CRAWL_CATEGORIES.md) - Chi tiết đầy đủ
- [QUICK_START_CRAWL.md](docs/QUICK_START_CRAWL.md) - Quick start
- [CRON_GUIDE.md](docs/CRON_GUIDE.md) - Hướng dẫn Cron

## 🎉 Kết luận

Hệ thống crawl categories đã được tích hợp hoàn chỉnh với:
- ✅ Database-driven configuration
- ✅ Auto-selection và priority
- ✅ Resume capability
- ✅ Progress tracking
- ✅ Cron automation
- ✅ CLI management
- ✅ Error handling
- ✅ Full documentation

**Sẵn sàng để production!** 🚀
