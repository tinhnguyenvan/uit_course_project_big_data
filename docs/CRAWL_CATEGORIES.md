# Quản lý Crawl Categories

Hệ thống quản lý cấu hình crawl categories từ Tiki.

## Cấu trúc bảng

Bảng `crawl_categories` quản lý danh sách các categories cần crawl với các thông tin:

| Column | Type | Mô tả |
|--------|------|-------|
| `category_id` | INTEGER | ID category từ Tiki (Primary Key) |
| `category_name` | VARCHAR(255) | Tên category |
| `category_url` | TEXT | URL đến trang category |
| `parent_category_id` | INTEGER | ID category cha (nếu có) |
| `is_active` | BOOLEAN | Có đang active để crawl không |
| `priority` | INTEGER | Độ ưu tiên (cao hơn = ưu tiên hơn) |
| `max_pages` | INTEGER | Số trang tối đa cần crawl |
| `crawl_status` | VARCHAR(20) | Trạng thái: `pending`, `in_progress`, `completed`, `failed`, `paused` |
| `last_crawled_at` | TIMESTAMP | Thời điểm crawl lần cuối |
| `last_crawled_page` | INTEGER | Trang cuối đã crawl (để resume) |
| `total_products_crawled` | INTEGER | Tổng số sản phẩm đã crawl |
| `notes` | TEXT | Ghi chú |
| `created_at` | TIMESTAMP | Ngày tạo |
| `updated_at` | TIMESTAMP | Ngày cập nhật |

## Sử dụng Script Quản lý

### 1. Xem danh sách categories

```bash
# Xem tất cả
python src/manage_crawl_categories.py list

# Chỉ xem active
python src/manage_crawl_categories.py list --active

# Lọc theo status
python src/manage_crawl_categories.py list --status pending
python src/manage_crawl_categories.py list --status completed
```

### 2. Thêm category mới

```bash
python src/manage_crawl_categories.py add \
  1234 \
  "Tên Category" \
  "https://tiki.vn/category-url" \
  --priority 8 \
  --max-pages 50 \
  --notes "Ghi chú"
```

### 3. Cập nhật thông tin

```bash
# Thay đổi priority
python src/manage_crawl_categories.py update 1789 --priority 10

# Thay đổi max pages
python src/manage_crawl_categories.py update 1789 --max-pages 100

# Thay đổi status
python src/manage_crawl_categories.py update 1789 --status completed
```

### 4. Kích hoạt / Vô hiệu hóa

```bash
# Kích hoạt để crawl
python src/manage_crawl_categories.py activate 1789

# Vô hiệu hóa (không crawl)
python src/manage_crawl_categories.py deactivate 1789
```

### 5. Reset trạng thái

```bash
# Reset để crawl lại từ đầu
python src/manage_crawl_categories.py reset 1789
```

### 6. Lấy category tiếp theo

```bash
# Lấy category có priority cao nhất cần crawl
python src/manage_crawl_categories.py next
```

### 7. Xem thống kê

```bash
python src/manage_crawl_categories.py stats
```

## Tích hợp với Crawler

### Cách 1: Chạy manual từ manage.py

```bash
# Crawl tất cả categories đang active (pending/failed)
docker compose run --rm app python src/manage.py crawl-from-db

# Crawl chỉ 3 categories đầu tiên
docker compose run --rm app python src/manage.py crawl-from-db --limit 3

# Crawl chỉ categories có status cụ thể
docker compose run --rm app python src/manage.py crawl-from-db --status pending
```

### Cách 2: Sử dụng SERVICE environment variable

```bash
# Crawl từ database
SERVICE=crawl-from-db docker compose up app

# Với limit
SERVICE=crawl-from-db LIMIT=5 docker compose up app

# Với status filter
SERVICE=crawl-from-db STATUS=failed docker compose up app
```

### Cách 3: Cron tự động (Recommended)

Cron job đã được cấu hình để tự động crawl mỗi 3 phút:

```bash
# Start cron service
docker compose up -d cron

# Xem logs
docker compose logs -f cron

# Hoặc xem log file
docker exec -it uit-bd-app tail -f /app/logs/cron-crawler.log
```

File cron: `/docker/crontab`
```bash
# Crawl categories từ database mỗi 3 phút (auto-select theo priority)
*/3 * * * * cd /app && /usr/local/bin/python src/crawl_from_categories.py >> /app/logs/cron-crawler.log 2>&1
```

### Cách 4: Sử dụng trực tiếp từ Python Code

```python
from app.models import SessionLocal, CrawlCategory

db = SessionLocal()

# Lấy tất cả active categories theo priority
categories = db.query(CrawlCategory).filter_by(
    is_active=True
).order_by(CrawlCategory.priority.desc()).all()

for cat in categories:
    # Cập nhật status
    cat.crawl_status = 'in_progress'
    db.commit()
    
    # Crawl với resume support
    start_page = cat.last_crawled_page + 1
    products = crawl_category(
        category_id=cat.category_id,
        max_pages=cat.max_pages,
        start_page=start_page
    )
    
    # Cập nhật tiến độ
    cat.last_crawled_page = current_page
    cat.total_products_crawled += len(products)
    cat.crawl_status = 'completed'
    cat.last_crawled_at = datetime.now()
    db.commit()

db.close()
```

## Cách chạy Cron Service

### 1. Start cron service

```bash
# Start service
docker compose up -d cron

# Check status
docker compose ps cron

# Xem logs real-time
docker compose logs -f cron
```

### 2. Xem logs

```bash
# Log crawler
docker exec -it uit-bd-app tail -f /app/logs/cron-crawler.log

# Log heartbeat
docker exec -it uit-bd-app tail -f /app/logs/cron-heartbeat.log

# Tất cả logs
docker exec -it uit-bd-app tail -f /app/logs/cron-*.log
```

### 3. Kiểm tra crontab đang chạy

```bash
docker exec -it uit-bd-app crontab -l
```

### 4. Stop cron service

```bash
docker compose stop cron
```

### Cách 2: Cập nhật entrypoint.sh

Thay đổi từ hardcode:
```bash
python src/main.py crawl-listing --category_id 1789
```

Thành sử dụng database:
```bash
# Lấy danh sách active categories
python src/crawl_from_db.py
```

## Truy vấn SQL hữu ích

### Xem categories đang active

```sql
SELECT category_id, category_name, priority, max_pages, crawl_status
FROM crawl_categories
WHERE is_active = true
ORDER BY priority DESC;
```

### Xem tiến độ crawl

```sql
SELECT 
    category_name,
    last_crawled_page,
    total_products_crawled,
    crawl_status,
    last_crawled_at
FROM crawl_categories
WHERE is_active = true
ORDER BY last_crawled_at DESC NULLS LAST;
```

### Tổng sản phẩm đã crawl

```sql
SELECT 
    SUM(total_products_crawled) as total_products,
    COUNT(*) as total_categories,
    COUNT(CASE WHEN crawl_status = 'completed' THEN 1 END) as completed_categories
FROM crawl_categories
WHERE is_active = true;
```

## Sample Data

Migration đã tự động thêm 11 categories phổ biến từ Tiki:

| ID | Category | Priority | Max Pages |
|----|----------|----------|-----------|
| 8322 | Điện Thoại - Máy Tính Bảng | 10 | 50 |
| 1789 | Điện Thoại Smartphone | 9 | 50 |
| 1846 | Laptop - Máy Vi Tính - Linh kiện | 9 | 50 |
| 1801 | Laptop | 9 | 50 |
| 1795 | Máy Tính Bảng | 8 | 30 |
| 8594 | Nhà Sách Tiki | 8 | 100 |
| 871 | Văn học | 7 | 80 |
| 316 | Sách kinh tế | 7 | 80 |
| 1882 | Đồ chơi - Mẹ & Bé | 6 | 40 |
| 2549 | Thời trang nữ | 5 | 40 |
| 1686 | Thời trang nam | 5 | 40 |

## Workflow Crawl

1. **Planning**: Thêm categories vào bảng với priority phù hợp
2. **Execution**: Crawler lấy categories theo priority, crawl từng category
3. **Tracking**: Cập nhật `last_crawled_page` và `total_products_crawled` sau mỗi batch
4. **Resume**: Nếu fail, có thể resume từ `last_crawled_page`
5. **Completion**: Đánh dấu `crawl_status = 'completed'` khi xong
6. **Re-crawl**: Reset category để crawl lại (cập nhật data mới)

## Best Practices

- **Priority**: 10 = cao nhất (categories quan trọng nhất), 1 = thấp nhất
- **Max Pages**: Điều chỉnh dựa trên số lượng sản phẩm trong category
- **Active Flag**: Tắt thay vì xóa để giữ lịch sử crawl
- **Resume**: Luôn update `last_crawled_page` để có thể resume khi bị gián đoạn
- **Notes**: Ghi chú lý do priority cao/thấp, hoặc đặc điểm category
