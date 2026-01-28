# ✅ Checklist Test Hệ Thống Crawl Categories

## 📋 Trước khi test

- [ ] Database đã có bảng `crawl_categories` (migration 005 đã apply)
- [ ] 11 categories mẫu đã được insert
- [ ] Docker containers đang chạy (postgres, kafka)

## 🧪 Test Cases

### 1. Kiểm tra Database

```bash
# Test 1.1: Xem bảng crawl_categories
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "SELECT COUNT(*) FROM crawl_categories;"
# Expected: 11 rows

# Test 1.2: Xem categories theo priority
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
SELECT category_id, category_name, priority, is_active, crawl_status 
FROM crawl_categories 
ORDER BY priority DESC 
LIMIT 5;
"
# Expected: Top 5 categories với priority cao nhất
```

**✅ Pass nếu:**
- Có 11 rows
- Category ID 8322 có priority = 10 (cao nhất)
- Tất cả is_active = true
- Tất cả crawl_status = 'pending'

---

### 2. Test CLI Management Script

```bash
# Test 2.1: List categories
python src/manage_crawl_categories.py list
# Expected: Hiển thị table với 11 categories

# Test 2.2: Stats
python src/manage_crawl_categories.py stats
# Expected: 
# - Tổng: 11
# - Active: 11
# - Pending: 11
# - Tổng products: 0

# Test 2.3: Get next category
python src/manage_crawl_categories.py next
# Expected: Category ID 8322 (priority cao nhất)

# Test 2.4: Thêm category mới (test)
python src/manage_crawl_categories.py add 9999 "Test Category" "https://test.com" --priority 1
# Expected: ✅ Đã thêm category

# Test 2.5: List lại
python src/manage_crawl_categories.py list
# Expected: 12 categories

# Test 2.6: Deactivate test category
python src/manage_crawl_categories.py deactivate 9999
# Expected: ✅ Đã cập nhật

# Test 2.7: List active only
python src/manage_crawl_categories.py list --active
# Expected: 11 categories (không có 9999)
```

**✅ Pass nếu:**
- Tất cả commands chạy không lỗi
- Data hiển thị đúng
- Add/Update/Deactivate hoạt động

---

### 3. Test Crawl Command trong manage.py

```bash
# Test 3.1: Crawl với limit (DRY RUN - chỉ test code path)
# Note: Test này cần container app chạy được
docker compose run --rm app python src/manage.py crawl-from-db --help
# Expected: Hiển thị help text

# Test 3.2: Nếu muốn test thật (optional - mất thời gian)
# docker compose run --rm app python src/manage.py crawl-from-db --limit 1
# Expected: Crawl 1 category, status → in_progress → completed
```

**✅ Pass nếu:**
- Help text hiển thị đúng options (--limit, --status)
- Command recognized

---

### 4. Test Script Cron

```bash
# Test 4.1: Chạy script trực tiếp (không qua cron)
# Note: Cần có Python environment với dependencies
cd /app && python src/crawl_from_categories.py
# Expected: 
# - Lấy category tiếp theo
# - Crawl category đó
# - Update status

# Hoặc test bằng cách xem help
head -20 src/crawl_from_categories.py
# Expected: Thấy docstring và imports đúng
```

**✅ Pass nếu:**
- Script có thể import modules
- Logic select category đúng

---

### 5. Test Cron Integration

```bash
# Test 5.1: Kiểm tra crontab file
cat docker/crontab
# Expected:
# */3 * * * * cd /app && /usr/local/bin/python src/crawl_from_categories.py >> /app/logs/cron-crawler.log 2>&1

# Test 5.2: Start cron service
docker compose up -d cron
# Expected: Container started

# Test 5.3: Check logs (đợi 3 phút)
docker compose logs cron
# Expected: Thấy log "Starting cron service..."

# Test 5.4: Check cron-crawler.log (sau 3-5 phút)
docker exec -it uit-bd-app tail -20 /app/logs/cron-crawler.log
# Expected: Thấy log crawl với timestamps

# Test 5.5: Check database sau khi cron chạy
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
SELECT category_id, category_name, crawl_status, last_crawled_at 
FROM crawl_categories 
WHERE last_crawled_at IS NOT NULL;
"
# Expected: Có categories đã crawl với timestamp

# Test 5.6: Stop cron
docker compose stop cron
```

**✅ Pass nếu:**
- Cron container start thành công
- Logs hiển thị crawl activity
- Database được update (status, timestamp)

---

### 6. Test SERVICE Environment Variable

```bash
# Test 6.1: Check entrypoint.sh có service mới
grep -A 10 "crawl-from-db" docker/entrypoint.sh
# Expected: Thấy case statement cho crawl-from-db

# Test 6.2: Test service (optional)
# SERVICE=crawl-from-db LIMIT=1 docker compose up app
# Expected: Chạy crawl-from-db với limit 1
```

**✅ Pass nếu:**
- entrypoint.sh có case cho crawl-from-db
- Service có thể được gọi qua env var

---

### 7. Test Update Operations

```bash
# Test 7.1: Update priority
python src/manage_crawl_categories.py update 1789 --priority 11
# Expected: ✅ Đã cập nhật

# Test 7.2: Verify update
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
SELECT category_id, priority FROM crawl_categories WHERE category_id = 1789;
"
# Expected: priority = 11

# Test 7.3: Reset category
python src/manage_crawl_categories.py reset 1789
# Expected: ✅ Đã reset

# Test 7.4: Verify reset
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
SELECT crawl_status, last_crawled_page, total_products_crawled 
FROM crawl_categories 
WHERE category_id = 1789;
"
# Expected: 
# - crawl_status = 'pending'
# - last_crawled_page = 0
# - total_products_crawled = 0
```

**✅ Pass nếu:**
- Update operations hoạt động
- Database được sync đúng

---

### 8. Test Error Handling

```bash
# Test 8.1: Thêm duplicate category
python src/manage_crawl_categories.py add 1789 "Duplicate" "http://test" --priority 1
# Expected: ❌ Category 1789 đã tồn tại!

# Test 8.2: Update non-existent category
python src/manage_crawl_categories.py update 99999 --priority 5
# Expected: ❌ Không tìm thấy category 99999
```

**✅ Pass nếu:**
- Errors được handle gracefully
- Thông báo lỗi rõ ràng

---

## 📊 Final Verification

### Database Schema Check
```sql
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "\d crawl_categories"
```

**Expected columns:**
- category_id (PK)
- category_name
- category_url
- parent_category_id
- is_active
- priority
- max_pages
- crawl_status
- last_crawled_at
- last_crawled_page
- total_products_crawled
- notes
- created_at
- updated_at

### Index Check
```sql
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'crawl_categories';
"
```

**Expected indexes:**
- idx_crawl_categories_status
- idx_crawl_categories_active
- idx_crawl_categories_priority
- idx_crawl_categories_parent

---

## 🎯 Success Criteria

✅ **PASS nếu tất cả:**

1. ✅ Database có 11 categories mẫu
2. ✅ CLI commands hoạt động (list, add, update, stats, next)
3. ✅ manage.py có command crawl-from-db
4. ✅ entrypoint.sh support SERVICE=crawl-from-db
5. ✅ Cron script hoạt động (crawl_from_categories.py)
6. ✅ Crontab được cấu hình (mỗi 3 phút)
7. ✅ Cron service có thể start và crawl
8. ✅ Database được update sau crawl (status, timestamp)
9. ✅ Error handling hoạt động
10. ✅ Documentation đầy đủ

---

## 📝 Test Log Template

```
Date: ___________
Tester: _________

[ ] Test 1: Database - PASS/FAIL
[ ] Test 2: CLI Management - PASS/FAIL
[ ] Test 3: Crawl Command - PASS/FAIL
[ ] Test 4: Cron Script - PASS/FAIL
[ ] Test 5: Cron Integration - PASS/FAIL
[ ] Test 6: SERVICE Variable - PASS/FAIL
[ ] Test 7: Update Operations - PASS/FAIL
[ ] Test 8: Error Handling - PASS/FAIL

Overall: PASS / FAIL

Notes:
______________________________
______________________________
```
