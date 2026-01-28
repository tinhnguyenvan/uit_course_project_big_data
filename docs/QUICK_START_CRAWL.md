# 🚀 Quick Start - Crawl từ Database

## Tóm tắt
Hệ thống crawl tự động từ bảng `crawl_categories` với các tính năng:
- ✅ Auto-select categories theo priority
- ✅ Resume từ trang cuối đã crawl
- ✅ Tracking tiến độ (total_products_crawled)
- ✅ Cron tự động mỗi 3 phút
- ✅ Quản lý categories qua CLI

## Bước 1: Kiểm tra categories

```bash
# Xem tất cả categories
python src/manage_crawl_categories.py list

# Xem chỉ active
python src/manage_crawl_categories.py list --active

# Xem thống kê
python src/manage_crawl_categories.py stats
```

## Bước 2: Thêm/Cập nhật categories (nếu cần)

```bash
# Thêm category mới
python src/manage_crawl_categories.py add 1234 "Tên Category" "https://tiki.vn/..." --priority 8 --max-pages 50

# Cập nhật priority
python src/manage_crawl_categories.py update 1789 --priority 10

# Kích hoạt category
python src/manage_crawl_categories.py activate 1789

# Vô hiệu hóa category
python src/manage_crawl_categories.py deactivate 1789
```

## Bước 3: Chạy crawler

### Option 1: Manual (test một lần)

```bash
# Crawl tất cả active categories
docker compose run --rm app python src/manage.py crawl-from-db

# Chỉ crawl 3 categories đầu tiên (test)
docker compose run --rm app python src/manage.py crawl-from-db --limit 3
```

### Option 2: Cron tự động (recommended)

```bash
# Start cron service (chạy mỗi 3 phút tự động)
docker compose up -d cron

# Xem logs real-time
docker compose logs -f cron

# Hoặc xem file log
docker exec -it uit-bd-app tail -f /app/logs/cron-crawler.log
```

### Option 3: Environment variable

```bash
# Crawl từ database
SERVICE=crawl-from-db docker compose up app

# Với limit
SERVICE=crawl-from-db LIMIT=5 docker compose up app
```

## Bước 4: Theo dõi tiến độ

```bash
# Xem thống kê
python src/manage_crawl_categories.py stats

# Output:
# 📊 Thống kê Crawl Categories
# ============================================================
# Tổng categories:        11
# Active:                 11
# Pending:                8
# In Progress:            1
# Completed:              2
# Failed:                 0
# Tổng sản phẩm crawled:  15420
# ============================================================

# Xem chi tiết
python src/manage_crawl_categories.py list
```

## Workflow tự động

1. **Cron chạy mỗi 3 phút** → Gọi `src/crawl_from_categories.py`
2. Script **lấy category tiếp theo** theo priority (pending/failed trước)
3. **Cập nhật status** → `in_progress`
4. **Crawl category** với max_pages và resume=true
5. **Cập nhật kết quả**:
   - Thành công → `completed`, update `last_crawled_at`
   - Lỗi → `failed`, ghi lại error trong `notes`
6. **Lặp lại** → Chọn category tiếp theo

## Categories mẫu đã có

| ID | Tên | Priority | Max Pages |
|----|-----|----------|-----------|
| 8322 | Điện Thoại - Máy Tính Bảng | 10 | 50 |
| 1789 | Điện Thoại Smartphone | 9 | 50 |
| 1801 | Laptop | 9 | 50 |
| 8594 | Nhà Sách Tiki | 8 | 100 |
| 871 | Văn học | 7 | 80 |
| 316 | Sách kinh tế | 7 | 80 |

## Quản lý nâng cao

### Reset category để crawl lại

```bash
# Reset trạng thái (về pending, xóa progress)
python src/manage_crawl_categories.py reset 1789
```

### Lấy category tiếp theo

```bash
# Xem category nào sẽ được crawl tiếp
python src/manage_crawl_categories.py next
```

### Truy vấn SQL trực tiếp

```bash
# Xem tiến độ
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
SELECT 
    category_id, 
    category_name, 
    crawl_status, 
    last_crawled_page,
    total_products_crawled,
    last_crawled_at
FROM crawl_categories 
WHERE is_active = true 
ORDER BY priority DESC;
"
```

## Troubleshooting

### Cron không chạy?

```bash
# Check container running
docker compose ps cron

# Check crontab installed
docker exec -it uit-bd-app crontab -l

# Check logs
docker exec -it uit-bd-app tail -f /app/logs/cron-crawler.log
```

### Category bị failed?

```bash
# Xem error message
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
SELECT category_id, category_name, notes 
FROM crawl_categories 
WHERE crawl_status = 'failed';
"

# Reset để thử lại
python src/manage_crawl_categories.py reset <category_id>
```

### Muốn dừng crawl category nào đó?

```bash
# Deactivate
python src/manage_crawl_categories.py deactivate <category_id>
```

## Best Practices

1. **Priority cao (9-10)**: Categories quan trọng, nhiều traffic
2. **Priority trung bình (5-8)**: Categories bình thường
3. **Priority thấp (1-4)**: Categories ít quan trọng
4. **Max pages**: Điều chỉnh dựa trên số lượng sản phẩm
   - Lớn (100 pages): Sách, văn học
   - Trung bình (50 pages): Điện thoại, laptop
   - Nhỏ (30-40 pages): Thời trang, đồ chơi
5. **Deactivate thay vì xóa**: Giữ lại lịch sử crawl
6. **Reset định kỳ**: Re-crawl để cập nhật data mới
