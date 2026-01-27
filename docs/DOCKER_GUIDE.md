# Docker Commands Guide

## 🚀 Build và Start

```bash
# Build image
docker-compose build app

# Start tất cả services
docker-compose up -d

# Hoặc chỉ start app
docker-compose up -d app
```

## 📋 Các Services có thể chạy

Set biến môi trường `SERVICE` để chọn service:

### 1. Check System
```bash
SERVICE=check docker-compose up app
```

### 2. Initialize Database
```bash
SERVICE=init-db docker-compose up app
```

### 3. Create Kafka Topics
```bash
SERVICE=create-topics docker-compose up app
```

### 4. Crawl Products
```bash
# Default: Category 1789 (Electronics), 10 pages
SERVICE=crawl-products docker-compose up app

# Custom category và pages
SERVICE=crawl-products CATEGORY_ID=1520 MAX_PAGES=20 docker-compose up app
```

### 5. Crawl Reviews
```bash
SERVICE=crawl-reviews PRODUCT_IDS="123456,789012" MAX_PAGES=5 docker-compose up app
```

### 6. Run Consumers

**Product Consumer:**
```bash
SERVICE=consumer-products docker-compose up app
```

**Review Consumer:**
```bash
SERVICE=consumer-reviews docker-compose up app
```

**All Consumers:**
```bash
SERVICE=consumers-all docker-compose up app
```

### 7. Interactive Shell
```bash
SERVICE=shell docker-compose up app
# Hoặc
docker-compose exec app /bin/bash
```

## 🔄 Workflow Complete

### Setup lần đầu:
```bash
# 1. Build và start services
docker-compose up -d

# 2. Initialize database
SERVICE=init-db docker-compose up app

# 3. Create Kafka topics
SERVICE=create-topics docker-compose up app

# 4. Check system
SERVICE=check docker-compose up app
```

### Crawl Data:
```bash
# Terminal 1: Crawl products
SERVICE=crawl-products CATEGORY_ID=1789 MAX_PAGES=10 docker-compose up app

# Terminal 2: Start consumers (để nhận data từ Kafka)
SERVICE=consumers-all docker-compose up app
```

### Monitor:
```bash
# View logs
docker-compose logs -f app

# Check container status
docker-compose ps

# Stats
docker stats uit-bd-app
```

## 🛠️ Useful Commands

```bash
# Rebuild image
docker-compose build --no-cache app

# Restart app
docker-compose restart app

# Stop app
docker-compose stop app

# Remove app container
docker-compose rm -f app

# View logs
docker-compose logs -f app

# Execute command in running container
docker-compose exec app python src/manage.py stats

# Access database from app container
docker-compose exec app psql -h postgres -U uit_user -d uit_analytics
```

## 📊 Example Workflows

### Workflow 1: One-time setup
```bash
docker-compose up -d
SERVICE=init-db docker-compose up app
SERVICE=create-topics docker-compose up app
```

### Workflow 2: Daily crawl
```bash
# Morning: Crawl products
SERVICE=crawl-products CATEGORY_ID=1789 MAX_PAGES=50 docker-compose up app

# Afternoon: Crawl reviews for those products
SERVICE=crawl-reviews PRODUCT_IDS="$(get-product-ids)" docker-compose up app
```

### Workflow 3: Run consumers 24/7
```bash
# Detached mode
SERVICE=consumers-all docker-compose up -d app

# View logs
docker-compose logs -f app
```

## 🐛 Debugging

```bash
# Check environment variables
docker-compose exec app env

# Check Python packages
docker-compose exec app pip list

# Test database connection
docker-compose exec app python -c "from app.models import check_connection; print(check_connection())"

# Test Kafka connection
docker-compose exec app python -c "from app.utils import check_kafka_connection; print(check_kafka_connection())"

# Interactive Python shell
docker-compose exec app python
```

## 🔍 Tiki Category IDs

- 1789: Điện thoại - Máy tính bảng
- 1520: Laptop - Máy Vi Tính - Linh kiện PC
- 1846: Máy Ảnh - Máy Quay Phim
- 27498: Tivi - Âm Thanh
- 1882: Đồng hồ thông minh
- 1801: Tai nghe
- 8322: Thiết bị đeo thông minh
