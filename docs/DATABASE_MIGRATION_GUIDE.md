# 🗄️ Hướng Dẫn Migration Database Lần Đầu

## 📋 Tổng quan

Hệ thống có **2 cấp độ** setup database:
1. **Schema ban đầu**  - Tạo cấu trúc cơ bản

---

## 🚀 Setup Database Lần Đầu Tiên

### Bước 1: Khởi động Database

```bash
# Start PostgreSQL container
docker compose up -d postgres

# Chờ 5 giây để PostgreSQL khởi động hoàn toàn
sleep 5

# Verify PostgreSQL đang chạy
docker compose ps postgres
```

**Expected output:**
```
NAME              IMAGE         STATUS
uit-bd-postgres   postgres:15   Up X seconds
```

---

### Bước 2: Apply Schema Ban Đầu

Schema ban đầu được **tự động** apply khi container khởi động lần đầu qua volume mount:

**Verify schema đã được tạo:**

```bash
# Kiểm tra các bảng chính
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "\dt"
```

**Expected output:**
```
                List of relations
 Schema |       Name        | Type  |  Owner   
--------+-------------------+-------+----------
 public | categories        | table | uit_user
 public | crawl_logs        | table | uit_user
 public | product_prices    | table | uit_user
 public | products          | table | uit_user
 public | reviews           | table | uit_user
 public | review_sentiment  | table | uit_user
 public | shops             | table | uit_user
```

---

### Bước 3: Apply Migrations Theo Thứ Tự

Sau khi schema ban đầu được tạo, apply các migrations:

#### 📄 Migration 003: Product Detail Columns

Thêm các cột chi tiết sản phẩm (review_count, discount_rate, authors, specifications...)

```bash
# Copy migration file vào container
docker cp docker/postgres/migrations/003_add_product_detail_columns.sql \
  uit-bd-postgres:/tmp/

# Apply migration
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics \
  -f /tmp/003_add_product_detail_columns.sql

# Verify
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  SELECT column_name, data_type 
  FROM information_schema.columns 
  WHERE table_name = 'products' 
    AND column_name IN ('review_count', 'discount_rate', 'authors', 'specifications');
"
```

**Expected output:**
```
   column_name    |   data_type   
------------------+---------------
 review_count     | integer
 discount_rate    | integer
 authors          | jsonb
 specifications   | jsonb
```

---

#### 📄 Migration 004: Order Tables

Tạo bảng customers, orders, order_lines cho order pipeline

```bash
# Copy migration file
docker cp docker/postgres/migrations/004_add_order_tables.sql \
  uit-bd-postgres:/tmp/

# Apply migration
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics \
  -f /tmp/004_add_order_tables.sql

# Verify
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "\dt" | grep -E "(customers|orders|order_lines)"
```

**Expected output:**
```
 public | customers    | table | uit_user
 public | order_lines  | table | uit_user
 public | orders       | table | uit_user
```

---

#### 📄 Migration 005: Crawl Categories

Tạo bảng crawl_categories để quản lý crawl configuration

```bash
# Copy migration file
docker cp docker/postgres/migrations/005_add_crawl_categories.sql \
  uit-bd-postgres:/tmp/

# Apply migration
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics \
  -f /tmp/005_add_crawl_categories.sql

# Verify table và data
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  SELECT category_id, category_name, is_active, priority 
  FROM crawl_categories 
  ORDER BY priority DESC 
  LIMIT 5;
"
```

**Expected output:**
```
 category_id |          category_name           | is_active | priority 
-------------+----------------------------------+-----------+----------
        8322 | Điện Thoại - Máy Tính Bảng       | t         |       10
        1789 | Điện Thoại Smartphone            | t         |        9
        1846 | Laptop - Máy Vi Tính - Linh kiện | t         |        9
        1801 | Laptop                           | t         |        9
        1795 | Máy Tính Bảng                    | t         |        8
```

---

### Bước 4: Verify Toàn Bộ Schema

```bash
# Xem tất cả các bảng
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "\dt"

# Đếm số bảng
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  SELECT COUNT(*) as total_tables 
  FROM information_schema.tables 
  WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
"
```

**Expected: 11 bảng**
- categories
- shops
- products
- product_prices
- reviews
- review_sentiment
- crawl_logs
- customers
- orders
- order_lines
- crawl_categories

---

## 🔄 Script Tự Động (All-in-One)

Tạo script để apply tất cả migrations một lần:

```bash
#!/bin/bash
# File: scripts/apply_all_migrations.sh

echo "🗄️  Applying all database migrations..."

CONTAINER="uit-bd-postgres"
DB_USER="uit_user"
DB_NAME="uit_analytics"

# Check if PostgreSQL is running
if ! docker exec $CONTAINER pg_isready -U $DB_USER > /dev/null 2>&1; then
    echo "❌ PostgreSQL is not ready"
    exit 1
fi

echo "✅ PostgreSQL is ready"

# Array of migrations
MIGRATIONS=(
    "003_add_product_detail_columns.sql"
    "004_add_order_tables.sql"
    "005_add_crawl_categories.sql"
)

# Apply each migration
for migration in "${MIGRATIONS[@]}"; do
    echo ""
    echo "📄 Applying migration: $migration"
    
    # Copy to container
    docker cp "docker/postgres/migrations/$migration" $CONTAINER:/tmp/
    
    # Apply migration
    docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -f "/tmp/$migration"
    
    if [ $? -eq 0 ]; then
        echo "✅ $migration applied successfully"
    else
        echo "❌ Failed to apply $migration"
        exit 1
    fi
done

echo ""
echo "🎉 All migrations applied successfully!"

# Show final table count
echo ""
echo "📊 Database summary:"
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
    SELECT 
        COUNT(*) as total_tables,
        string_agg(table_name, ', ' ORDER BY table_name) as tables
    FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
"
```

**Chạy script:**

```bash
# Tạo script
chmod +x scripts/apply_all_migrations.sh

# Chạy
./scripts/apply_all_migrations.sh
```

---

## 🔍 Kiểm Tra & Troubleshooting

### Kiểm tra migration đã apply chưa

```bash
# Kiểm tra bảng orders có tồn tại không (migration 004)
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_name = 'orders'
  );
"
```

### Kiểm tra data mẫu trong crawl_categories

```bash
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  SELECT COUNT(*) as total_categories FROM crawl_categories;
"
# Expected: 11
```

### Reset database (nếu cần)

```bash
# ⚠️ CẢNH BÁO: Xóa toàn bộ data!
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  DROP SCHEMA public CASCADE;
  CREATE SCHEMA public;
"

# Sau đó restart container để apply
docker compose restart postgres

# Rồi apply lại migrations
./scripts/apply_all_migrations.sh
```

---

## 📊 Verification Checklist

Sau khi apply migrations, verify:

- [ ] **11 bảng** đã được tạo
- [ ] Bảng `products` có cột `review_count`, `discount_rate`
- [ ] Bảng `customers`, `orders`, `order_lines` tồn tại
- [ ] Bảng `crawl_categories` có **11 rows** data mẫu
- [ ] Foreign keys hoạt động:
  ```bash
  docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
    SELECT 
      tc.table_name, 
      kcu.column_name, 
      ccu.table_name AS foreign_table_name,
      ccu.column_name AS foreign_column_name 
    FROM information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_name IN ('orders', 'order_lines')
    ORDER BY tc.table_name;
  "
  ```

---

## 🎯 Next Steps

Sau khi migrations hoàn tất:

1. ✅ **Tạo Kafka topics:**
   ```bash
   docker compose run --rm app python src/manage.py create-kafka-topics
   ```

2. ✅ **Start consumers:**
   ```bash
   docker compose up -d consumers
   ```

3. ✅ **Start cron crawl:**
   ```bash
   docker compose up -d cron
   ```

4. ✅ **Verify data flow:**
   ```bash
   # Sau vài phút
   python src/manage.py stats
   ```

---

## 📚 Tham khảo