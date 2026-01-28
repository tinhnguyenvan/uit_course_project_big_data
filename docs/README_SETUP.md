# Hướng dẫn Setup Project

## Bước 1: Prerequisites

Cài đặt các công cụ cần thiết:

```bash
# Docker Desktop
# Download tại: https://www.docker.com/products/docker-desktop

# Python 3.10+
# Download tại: https://www.python.org/downloads/

# Verify installations
docker --version
docker-compose --version
python --version
```

## Bước 2: Clone và Setup Project

```bash
# Di chuyển vào thư mục project
cd /Users/tinhnguyen/Sites/uit/12_cong_nghe_du_lieu_lon/project

# Tạo file .env từ template
cp .env.example .env

# Tạo thư mục logs
mkdir -p logs
mkdir -p data

# Tạo virtual environment (recommended)
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# hoặc: venv\Scripts\activate  # Windows

# Install Python dependencies
pip install -r requirements.txt
```

## Bước 3: Khởi động Docker Services

```bash
# Start all services (Kafka, PostgreSQL, Metabase)
docker-compose up -d

# Check services status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove all data
docker-compose down -v
```

## Bước 4: Verify Services

### 1. Kiểm tra Kafka

```bash
# Access Kafka UI
open http://localhost:8080

# Hoặc kiểm tra topics bằng command line
docker exec -it uit-kafka kafka-topics --list --bootstrap-server localhost:9092

# Tạo topics thủ công (optional - auto create enabled)
docker exec -it uit-kafka kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic uit-products \
  --partitions 3 \
  --replication-factor 1

docker exec -it uit-kafka kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic uit-reviews \
  --partitions 3 \
  --replication-factor 1
```

### 2. Kiểm tra PostgreSQL

```bash
# Connect to PostgreSQL
docker exec -it uit-postgres psql -U uit_user -d uit_analytics

# Run queries
SELECT * FROM categories;
SELECT * FROM information_schema.tables WHERE table_schema = 'public';

# Check TimescaleDB
SELECT * FROM timescaledb_information.hypertables;

# Exit
\q
```

### 3. Kiểm tra Metabase

```bash
# Open Metabase
open http://localhost:3000

# First time setup:
# 1. Create admin account
# 2. Add PostgreSQL database:
#    - Database type: PostgreSQL
#    - Name: Uit Analytics
#    - Host: postgres
#    - Port: 5432
#    - Database name: uit_analytics
#    - Username: uit_user
#    - Password: uit_password
```

## Bước 5: Test Connection

Tạo file test script:

```bash
# Create test script
cat > test_connections.py << 'EOF'
import psycopg2
from confluent_kafka import Producer, Consumer
from dotenv import load_dotenv
import os

load_dotenv()

# Test PostgreSQL
try:
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST'),
        port=os.getenv('POSTGRES_PORT'),
        database=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD')
    )
    print("✅ PostgreSQL connection successful!")
    conn.close()
except Exception as e:
    print(f"❌ PostgreSQL connection failed: {e}")

# Test Kafka
try:
    producer = Producer({'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS')})
    print("✅ Kafka producer connection successful!")
except Exception as e:
    print(f"❌ Kafka connection failed: {e}")
EOF

# Run test
python test_connections.py
```

## Bước 6: Services URLs

Sau khi setup thành công:

| Service | URL | Credentials |
|---------|-----|-------------|
| Kafka UI | http://localhost:8080 | - |
| PostgreSQL | localhost:5432 | uit_user / uit_password |
| Metabase | http://localhost:3000 | Setup on first access |

## Troubleshooting

### Lỗi: Port already in use

```bash
# Check what's using the port
lsof -i :5432  # PostgreSQL
lsof -i :9092  # Kafka
lsof -i :3000  # Metabase

# Kill process hoặc đổi port trong docker-compose.yml
```

### Lỗi: Docker compose version

```bash
# Nếu dùng Docker Compose V1, đổi command thành:
docker-compose up -d  # thay vì docker compose up -d
```

### Lỗi: PostgreSQL không chạy

```bash
# Remove volume và restart
docker-compose down -v
docker-compose up -d
```

### Lỗi: Kafka connection refused

```bash
# Restart Kafka
docker-compose restart kafka

# Check logs
docker-compose logs kafka
```

## Useful Commands

```bash
# View all running containers
docker ps

# View container logs
docker logs uit-kafka
docker logs uit-postgres
docker logs uit-metabase

# Restart specific service
docker-compose restart kafka

# Execute command in container
docker exec -it uit-postgres psql -U uit_user

# Remove all stopped containers
docker container prune

# Remove all unused volumes
docker volume prune
```

## Next Steps

Sau khi setup xong Docker services:

1. ✅ Test connections
2. ✅ Verify database schema
3. ✅ Check Kafka topics
4. ✅ Setup Metabase database connection
5. 🔄 Develop crawlers (Phase 2)
6. 🔄 Develop Kafka producers/consumers (Phase 3)
7. 🔄 Sentiment analysis (Phase 4)
8. 🔄 Create Metabase dashboards (Phase 5)

---

**Note**: Mọi thắc mắc xem logs bằng `docker-compose logs -f`
