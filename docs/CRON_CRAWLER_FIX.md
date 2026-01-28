# 🔧 Sửa Lỗi: Cron Crawler Không Chạy

## ❌ Vấn Đề

Cron service đang chạy nhưng **không crawl theo table `crawl_categories`**.

## 🔍 Nguyên Nhân

1. **Crontab file cũ**: Container sử dụng file crontab cũ (chạy category 870 cố định)
2. **Đường dẫn sai**: `cd /app && python src/...` → thiếu `/app/src/`
3. **Category stuck**: Category 8594 bị trạng thái `in_progress`

## ✅ Đã Sửa

### 1. Cập nhật crontab mới

**File:** [docker/crontab](../docker/crontab)

```bash
# Crawl categories từ database mỗi 3 phút (auto-select theo priority)
*/3 * * * * /usr/local/bin/python /app/src/crawl_from_categories.py >> /app/logs/cron-crawler.log 2>&1
```

**Thay vì cũ:**
```bash
*/2 * * * * cd /app/src && scrapy crawl tiki_listing -a category_id=870 ...
```

### 2. Apply vào container

```bash
# Update crontab trong container đang chạy
docker cp docker/crontab uit-bd-cron:/app/docker/crontab
docker exec uit-bd-cron crontab /app/docker/crontab
```

### 3. Reset category stuck

```bash
# Reset category về pending nếu bị stuck
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c \
  "UPDATE crawl_categories SET crawl_status = 'pending' WHERE crawl_status = 'in_progress';"
```

---

## 🧪 Kiểm Tra

### Script tự động

```bash
# Kiểm tra toàn bộ status
./scripts/check_cron_crawler.sh
```

### Manual checks

```bash
# 1. Xem crontab hiện tại
docker exec uit-bd-cron crontab -l

# 2. Theo dõi log real-time
docker logs -f uit-bd-cron

# 3. Xem crawler log
docker exec uit-bd-cron tail -f /app/logs/cron-crawler.log

# 4. Test chạy thủ công
docker exec uit-bd-cron python /app/src/crawl_from_categories.py

# 5. Kiểm tra status categories
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  SELECT category_id, category_name, crawl_status, priority 
  FROM crawl_categories 
  WHERE is_active = true 
  ORDER BY priority DESC;
"
```

---

## 📊 Cách Hoạt Động

### Logic crawl tự động

1. **Cron chạy mỗi 3 phút** (00, 03, 06, 09, 12, 15...)
2. **Script `crawl_from_categories.py`**:
   - Query category có `crawl_status = pending` hoặc `failed`
   - Sắp xếp theo `priority DESC`
   - Lấy category đầu tiên
   - Crawl với `max_pages` từ database
   - Cập nhật `crawl_status` và `last_crawled_at`

3. **Nếu hết pending/failed**:
   - Lấy category `completed` lâu nhất chưa crawl
   - Crawl lại để cập nhật data

### Priority crawl

```
Priority 10 → Điện Thoại - Máy Tính Bảng  (chưa crawl → ưu tiên CAO)
Priority 9  → Điện Thoại Smartphone        (pending → ưu tiên cao)
Priority 8  → Nhà Sách Tiki                (completed → ưu tiên thấp hơn)
Priority 7  → Văn học                      (pending → ưu tiên trung bình)
```

---

## 🎯 Kết Quả Mong Đợi

### Sau 3-5 phút:

```bash
# Log sẽ hiển thị
================================================================================
[2026-01-28 13:54:00] BẮT ĐẦU CRON CRAWL
================================================================================
📋 Category được chọn:
   ID: 8594
   Tên: Nhà Sách Tiki
   Priority: 8
   Max pages: 100
   Status hiện tại: pending

🕷️  Bắt đầu crawl category 8594
...
✅ Crawl thành công category 8594
================================================================================
[2026-01-28 13:55:32] KẾT THÚC CRON CRAWL
================================================================================
```

### Database sẽ cập nhật:

```sql
-- Category vừa crawl
crawl_status: 'completed'
last_crawled_at: '2026-01-28 13:55:32'

-- Category tiếp theo
crawl_status: 'in_progress' → sẽ chạy ở lần cron kế tiếp
```

---

## 🛠️ Quản Lý Categories

### CLI Tool: manage_crawl_categories.py

```bash
# Xem danh sách
python src/manage_crawl_categories.py list

# Thêm category mới
python src/manage_crawl_categories.py add <category_id> "Tên category" --priority 9

# Cập nhật priority
python src/manage_crawl_categories.py update <category_id> --priority 10 --max-pages 200

# Activate/Deactivate
python src/manage_crawl_categories.py activate <category_id>
python src/manage_crawl_categories.py deactivate <category_id>

# Reset status về pending
python src/manage_crawl_categories.py reset <category_id>

# Xem category tiếp theo sẽ crawl
python src/manage_crawl_categories.py next

# Thống kê
python src/manage_crawl_categories.py stats
```

---

## 📝 Files Liên Quan

| File | Mô tả |
|------|-------|
| [docker/crontab](../docker/crontab) | Cron schedule (✅ đã fix) |
| [src/crawl_from_categories.py](../src/crawl_from_categories.py) | Script chính |
| [docker/start-cron.sh](../docker/start-cron.sh) | Khởi động cron service |
| [scripts/check_cron_crawler.sh](../scripts/check_cron_crawler.sh) | Script kiểm tra status |
| [src/manage_crawl_categories.py](../src/manage_crawl_categories.py) | CLI quản lý |

---

## ⚠️ Lưu Ý

### Rebuild image nếu cần

Nếu restart container mà vẫn dùng crontab cũ:

```bash
# Rebuild cron service
docker compose build cron

# Hoặc recreate
docker compose up -d --force-recreate cron
```

### Monitor logs

```bash
# Real-time monitoring
docker logs -f uit-bd-cron 2>&1 | grep -E "BẮT ĐẦU|KẾT THÚC|Category"
```

### Debug

```bash
# Nếu cron không chạy, check process
docker exec uit-bd-cron pgrep cron || echo "Cron not running"

# Restart cron trong container
docker compose restart cron
```

---

## ✅ Checklist Hoàn Tất

- [x] Cập nhật file `docker/crontab` với logic mới
- [x] Apply crontab vào container
- [x] Reset category stuck về pending
- [x] Tạo script kiểm tra `check_cron_crawler.sh`
- [x] Test chạy thủ công thành công
- [x] Cron schedule đúng (mỗi 3 phút)
- [x] Sẵn sàng crawl tự động từ database

🎉 **Cron crawler đã được sửa và sẵn sàng hoạt động!**
