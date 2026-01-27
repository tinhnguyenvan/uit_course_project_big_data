# 🚀 Quick Start Guide

## Đã sửa lỗi thành công!

### ✅ Build & Start

```bash
# Build Docker image
docker-compose build app

# Start tất cả services
docker-compose up -d
```

### 📋 Các lệnh sử dụng

#### 1. Check hệ thống
```bash
SERVICE=check docker-compose up app
```

#### 2. Khởi tạo database
```bash
SERVICE=init-db docker-compose up app
```

#### 3. Tạo Kafka topics
```bash
SERVICE=create-topics docker-compose up app
```

#### 4. Crawl Products
```bash
# Default: Category Electronics (1789), 10 pages
SERVICE=crawl-products docker-compose up app

# Custom category
SERVICE=crawl-products CATEGORY_ID=1520 MAX_PAGES=20 docker-compose up app
```

#### 5. Crawl Reviews
```bash
SERVICE=crawl-reviews PRODUCT_IDS="123456,789012" docker-compose up app
```

#### 6. Run Consumers (Background)
```bash
# Tất cả consumers
SERVICE=consumers-all docker-compose up -d app

# Chỉ product consumer
SERVICE=consumer-products docker-compose up -d app

# Chỉ review consumer  
SERVICE=consumer-reviews docker-compose up -d app

# View logs
docker-compose logs -f app
```

#### 7. Interactive Shell
```bash
SERVICE=shell docker-compose up app
```

### 🔍 Monitoring

```bash
# View logs
docker-compose logs -f app

# Check status
docker-compose ps

# Access Conduktor Console (Kafka UI)
open http://localhost:8081

# Access Metabase
open http://localhost:3000

# Access PostgreSQL
docker exec -it uit-bd-postgres psql -U uit_user -d uit_analytics
```

### 📊 Workflow Example

```bash
# 1. Start all infrastructure
docker-compose up -d

# 2. Initialize (one-time setup)
SERVICE=init-db docker-compose up app
SERVICE=create-topics docker-compose up app

# 3. Start consumers (background)
SERVICE=consumers-all docker-compose up -d app

# 4. Crawl data
SERVICE=crawl-products CATEGORY_ID=1789 MAX_PAGES=5 docker-compose up app

# 5. View logs
docker-compose logs -f app

# 6. Check stats
SERVICE=check docker-compose up app
```

### 🛠️ Troubleshooting

#### Rebuild image nếu có thay đổi code
```bash
docker-compose build app
docker-compose up -d app
```

#### Xem logs nếu có lỗi
```bash
docker-compose logs app
```

#### Restart container
```bash
docker-compose restart app
```

#### Stop tất cả services
```bash
docker-compose down
```

#### Stop và xóa volumes (reset toàn bộ data)
```bash
docker-compose down -v
```

### 📝 Notes

- **Lỗi đã sửa**: 
  - ✅ Thêm system dependencies (gcc, g++, libxml, libxslt, etc.)
  - ✅ Commented out `underthesea` (cần Rust compiler)
  - ✅ Fixed SQLAlchemy 2.0 compatibility (thêm `text()`)
  - ✅ Copy entrypoint.sh vào container
  - ✅ Fixed imports trong utils/__init__.py

- **Services khả dụng**:
  - check, init-db, create-topics
  - crawl-products, crawl-reviews
  - consumer-products, consumer-reviews, consumers-all
  - shell

- **Nếu cần Vietnamese NLP**: Uncomment transformers/torch trong requirements.txt hoặc cài riêng
