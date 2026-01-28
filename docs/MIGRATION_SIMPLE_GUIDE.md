# 🚀 Hướng Dẫn Migration Database - PHIÊN BẢN ĐƠN GIẢN

## ✅ Giải pháp: 1 File Migration Duy Nhất

Thay vì apply nhiều migration riêng lẻ, giờ có **1 file duy nhất** chứa tất cả:

📄 **`000_complete_schema.sql`** - Tổng hợp hoàn chỉnh:
- ✅ Schema ban đầu (7 bảng)
- ✅ Migration 003 (6 columns mới cho products)
- ✅ Migration 004 (3 bảng orders)
- ✅ Migration 005 (bảng crawl_categories + 11 samples)
- ✅ Indexes, triggers, views
- ✅ TimescaleDB features

**Tổng cộng: 11 bảng + đầy đủ features**

---

## 🎯 Cách Sử Dụng

### **Option 1: Script Tự Động (Recommended)** ⚡

```bash
# Chạy 1 lệnh duy nhất
./scripts/apply_complete_migration.sh
```

**Output mong đợi:**
```
✅ PostgreSQL is ready
⚙️  Executing migration...
✅ Migration applied successfully!

📊 Verification
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Total tables: 11/11 ✅
📌 Crawl categories: 11/11 ✅
📌 Products extra columns: ✅
📌 Order pipeline tables: ✅
```

---

### **Option 2: Manual (Từng bước)** 🔧

```bash
# 1. Copy file vào container
docker cp docker/postgres/migrations/000_complete_schema.sql \
  uit-bd-postgres:/tmp/

# 2. Apply migration
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics \
  -f /tmp/000_complete_schema.sql

# 3. Verify
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  SELECT COUNT(*) FROM crawl_categories;
"
# Expected: 11
```

---

## 🔍 Verification Checklist

Sau khi apply migration, kiểm tra:

### ✅ **11 bảng được tạo:**

```bash
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "\dt"
```

**Expected:**
1. categories
2. crawl_categories ← MỚI
3. crawl_logs
4. customers ← MỚI
5. order_lines ← MỚI
6. orders ← MỚI
7. product_prices (TimescaleDB hypertable)
8. products (+ 6 columns mới)
9. review_sentiment
10. reviews
11. shops

### ✅ **Products có 6 columns mới:**

```bash
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  SELECT column_name 
  FROM information_schema.columns 
  WHERE table_name = 'products' 
    AND column_name IN ('review_count', 'discount_rate', 'authors', 
                        'specifications', 'configurable_options', 'short_description');
"
```

**Expected: 6 rows**

### ✅ **11 sample categories:**

```bash
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  SELECT category_id, category_name, priority 
  FROM crawl_categories 
  ORDER BY priority DESC;
"
```

**Expected:**
```
8322 | Điện Thoại - Máy Tính Bảng       | 10
1789 | Điện Thoại Smartphone            | 9
1801 | Laptop                           | 9
...
```

---

## 🔄 Reset Database (Nếu cần)

Nếu gặp lỗi và muốn reset lại từ đầu:

```bash
# 1. Stop all services
docker compose down

# 2. Xóa volume database cũ
docker volume rm project_postgres_data

# 3. Start lại PostgreSQL
docker compose up -d postgres
sleep 10

# 4. Apply complete migration
./scripts/apply_complete_migration.sh
```

---

## 📊 So Sánh: Cũ vs Mới

### ❌ **Cách cũ (Phức tạp):**

**Vấn đề:**
- Dễ thiếu file
- Phải chạy đúng thứ tự
- Lỗi 1 file → toàn bộ sai

### ✅ **Cách mới (Đơn giản):**

```bash
# 1 lệnh duy nhất
./scripts/apply_complete_migration.sh
```

**Ưu điểm:**
- ✅ Chỉ 1 file SQL duy nhất
- ✅ Tự động verify
- ✅ IF NOT EXISTS → an toàn
- ✅ Clear summary output

---

## 📋 Nội dung File 000_complete_schema.sql

Cấu trúc file:

```sql
-- PHẦN 1: Main tables (7 bảng)
CREATE TABLE categories...
CREATE TABLE shops...
CREATE TABLE products...  -- ★ Đã có 6 columns mới
CREATE TABLE product_prices... (TimescaleDB)
CREATE TABLE reviews...
CREATE TABLE review_sentiment...
CREATE TABLE crawl_logs...

-- PHẦN 2: Order tables (3 bảng)
CREATE TABLE customers...
CREATE TABLE orders...
CREATE TABLE order_lines...

-- PHẦN 3: Crawl categories (1 bảng)
CREATE TABLE crawl_categories...

-- PHẦN 4: Indexes (25 indexes)
CREATE INDEX...

-- PHẦN 5: Triggers (2 triggers)
CREATE TRIGGER...

-- PHẦN 6: Views (4 views)
CREATE VIEW product_stats_daily...
CREATE VIEW sentiment_summary...
CREATE VIEW price_changes...
CREATE VIEW top_selling_products...

-- PHẦN 7: Sample data
INSERT INTO categories... (5 rows)
INSERT INTO crawl_categories... (11 rows)

-- PHẦN 8: TimescaleDB features
CREATE MATERIALIZED VIEW product_prices_hourly...
SELECT add_continuous_aggregate_policy...
SELECT add_retention_policy...

-- PHẦN 9: Permissions
GRANT ALL PRIVILEGES...

-- PHẦN 10: Comments
COMMENT ON...
```

**Tổng cộng: ~476 dòng SQL**

---

## 🐛 Troubleshooting

### Lỗi: "table already exists"

✅ **KHÔNG CÓ VẤN ĐỀ** - File sử dụng `IF NOT EXISTS`

```sql
CREATE TABLE IF NOT EXISTS products...
-- Sẽ skip nếu đã có
```

### Lỗi: "relation does not exist"

❌ Database chưa được tạo. Check:

```bash
docker exec uit-bd-postgres psql -U uit_user -l | grep uit_analytics
```

Nếu không có, restart container:

```bash
docker compose restart postgres
sleep 10
```

### Lỗi: "permission denied"

Check user permissions:

```bash
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  SELECT current_user, current_database();
"
```

---

## 🚀 Next Steps Sau Migration

### 1. Tạo Kafka Topics

```bash
docker compose run --rm app python src/manage.py create-kafka-topics
```

### 2. Verify Topics

```bash
docker exec uit-bd-kafka kafka-topics --bootstrap-server localhost:9092 --list | grep uit
```

**Expected 8 topics:**
- uit-orders ✅
- uit-prices
- uit-product-detail
- uit-products
- uit-review-detail
- uit-review-fetch
- uit-reviews
- uit-shops

### 3. Start Consumers

```bash
docker compose up -d consumers
```

### 4. Start Cron Crawler

```bash
docker compose up -d cron
```

### 5. Monitor

```bash
# Database stats
docker compose run --rm app python src/manage.py stats

# Crawl categories
python src/manage_crawl_categories.py stats
```

---

## 📚 Files Liên Quan

- 📄 [000_complete_schema.sql](../docker/postgres/migrations/000_complete_schema.sql) - Migration tổng hợp
- 🤖 [apply_complete_migration.sh](../scripts/apply_complete_migration.sh) - Script apply
- 📖 [DATABASE_MIGRATION_GUIDE.md](DATABASE_MIGRATION_GUIDE.md) - Hướng dẫn chi tiết (cách cũ)

---

## ✅ Summary

| Aspect | Detail |
|--------|--------|
| **File migration** | 1 file duy nhất (000_complete_schema.sql) |
| **Số bảng** | 11 bảng |
| **Sample data** | 11 crawl categories + 5 categories |
| **Thời gian apply** | ~5 giây |
| **Cần restart?** | Không - chỉ apply 1 lần |
| **An toàn?** | Có - dùng IF NOT EXISTS |

🎉 **Setup database chưa bao giờ đơn giản đến thế!**
