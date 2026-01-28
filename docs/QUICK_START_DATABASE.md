# 🚀 Quick Start - Database Setup từ đầu

## Trường hợp 1: Setup Database LẦN ĐẦU (Fresh Install)

### Bước 1: Xóa database cũ (nếu có)

```bash
# Stop và xóa containers
docker compose down

# Xóa volume database cũ
docker volume rm project_postgres_data 2>/dev/null || true
```

### Bước 2: Start PostgreSQL với schema ban đầu

```bash
docker compose up -d postgres

# Đợi 10 giây để PostgreSQL khởi tạo
sleep 10

# Verify schema đã được tạo
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "\dt"
```

**Expected: 7 bảng ban đầu**
- categories
- shops
- products
- product_prices
- reviews
- review_sentiment
- crawl_logs

### Bước 3: Apply migrations

```bash
# Chạy script tự động
./scripts/apply_migrations.sh
```

### Bước 4: Verify toàn bộ

```bash
# Kiểm tra có 11 bảng
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
SELECT COUNT(*) as total_tables 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
"
# Expected: 11

# Kiểm tra crawl_categories có data
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
SELECT COUNT(*) FROM crawl_categories;
"
# Expected: 11
```

---

## Trường hợp 2: Database ĐÃ TỒN TẠI (Apply migrations mới)

Nếu database đã có sẵn với schema ban đầu, chỉ cần apply migrations:

```bash
# Chạy script migration
./scripts/apply_migrations.sh
```

Script sẽ tự động:
- ✅ Kiểm tra PostgreSQL đang chạy
- ✅ Apply các migrations theo thứ tự (003, 004, 005)
- ✅ Skip migrations đã apply (không lỗi)
- ✅ Show summary và next steps

---

## Trường hợp 3: Apply Migration thủ công (từng bước)

### Migration 003: Product Details

```bash
docker cp docker/postgres/migrations/003_add_product_detail_columns.sql uit-bd-postgres:/tmp/
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -f /tmp/003_add_product_detail_columns.sql
```

### Migration 004: Order Tables

```bash
docker cp docker/postgres/migrations/004_add_order_tables.sql uit-bd-postgres:/tmp/
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -f /tmp/004_add_order_tables.sql
```

### Migration 005: Crawl Categories

```bash
docker cp docker/postgres/migrations/005_add_crawl_categories.sql uit-bd-postgres:/tmp/
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -f /tmp/005_add_crawl_categories.sql
```

---

## 🔍 Verification

### Kiểm tra tất cả bảng

```bash
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;
"
```

**Expected 11 bảng:**
1. categories
2. crawl_categories ← Migration 005
3. crawl_logs
4. customers ← Migration 004
5. order_lines ← Migration 004
6. orders ← Migration 004
7. product_prices
8. products (với columns mới từ Migration 003)
9. review_sentiment
10. reviews
11. shops

### Kiểm tra columns mới trong products

```bash
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'products' 
  AND column_name IN ('review_count', 'discount_rate', 'authors', 'specifications')
ORDER BY column_name;
"
```

### Kiểm tra sample data trong crawl_categories

```bash
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
SELECT category_id, category_name, priority, is_active 
FROM crawl_categories 
ORDER BY priority DESC 
LIMIT 5;
"
```

---

## 🐛 Troubleshooting

### Lỗi: "database uit_analytics does not exist"

```bash
docker compose down
docker compose up -d postgres
sleep 10
```

### Lỗi: "relation already exists"

Migration đã apply rồi - không sao, skip được:

```bash
# Migrations sử dụng IF NOT EXISTS nên an toàn
```

### Lỗi: "container not found"

Start PostgreSQL trước:

```bash
docker compose up -d postgres
```

### Reset database hoàn toàn

```bash
# ⚠️ CẢNH BÁO: Xóa toàn bộ data!
docker compose down
docker volume rm project_postgres_data
docker compose up -d postgres
sleep 10
./scripts/apply_migrations.sh
```

---

## 📚 Next Steps

Sau khi migrations hoàn tất:

### 1. Tạo Kafka Topics

```bash
docker compose run --rm app python src/manage.py create-kafka-topics
```

### 2. Verify Topics

```bash
docker exec uit-bd-kafka kafka-topics --bootstrap-server localhost:9092 --list | grep uit
```

Expected 8 topics:
- uit-orders
- uit-prices
- uit-product-detail
- uit-products
- uit-review-detail
- uit-review-fetch
- uit-reviews
- uit-shops

### 3. Start Services

```bash
# Start all consumers
docker compose up -d consumers

# Start cron crawler
docker compose up -d cron

# Check logs
docker compose logs -f consumers
```

### 4. Monitor

```bash
# Database stats
docker compose run --rm app python src/manage.py stats

# Crawl categories
python src/manage_crawl_categories.py stats
```

---

## 📋 Complete Setup Checklist

- [ ] PostgreSQL container running
- [ ] Database `uit_analytics` exists
- [ ] Total 11 bảng in database
- [ ] 11 categories trong crawl_categories
- [ ] 8 Kafka topics created
- [ ] Consumers running
- [ ] Cron crawler running

✅ **System ready to crawl!**
