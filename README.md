# Hệ thống thu thập, xử lý và phân tích bình luận sách trên môi trường trực tuyến

> Đồ án môn Công nghệ Dữ liệu Lớn - Đại học Công nghệ Thông tin


## 🔑 Thông tin Đăng nhập / Login Credentials

| Service | URL | Username | Password |
|---------|-----|----------|----------|
| Kafka | http://localhost:8081/ | admin@gmail.com | Admin@123 |
| Metabase | http://localhost:3000/ | admin@gmail.com | Admin@123 |


## 📋 Tổng quan

Hệ thống thu thập và phân tích dữ liệu sản phẩm và bình luận từ Tiki theo thời gian thực. Sử dụng web crawler để thu thập dữ liệu, Kafka để streaming, PostgreSQL để lưu trữ và Metabase để visualization. Project bao gồm data pipeline hoàn chỉnh: Crawl → Stream → Store → Analyze → Visualize.

## 🎯 Mục tiêu

- **Thu thập dữ liệu từ Tiki**: Crawl thông tin sản phẩm (tên, giá, rating, số lượng bán) và bình luận khách hàng
- **Xây dựng streaming pipeline**: Sử dụng Kafka để stream dữ liệu crawl được theo thời gian thực
- **Lưu trữ và xử lý**: PostgreSQL + TimescaleDB cho dữ liệu time-series
- **Phân tích sentiment**: Phân tích cảm xúc từ bình luận khách hàng (tích cực/tiêu cực/trung tính)
- **Dashboard trực quan**: Metabase dashboards hiển thị insights về sản phẩm, giá cả, xu hướng, sentiment
- **Theo dõi giá**: Tracking thay đổi giá sản phẩm theo thời gian

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────┐
│          Tiki Website                     │
│  (Products + Reviews)                       │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│     Web Crawlers (Scrapy/Selenium)          │
│  - Product Crawler                          │
│  - Review Crawler                           │
│  - Price Tracker                            │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│         Kafka Cluster (2 Topics)            │
│  - uit-products                          │
│  - uit-reviews                           │
└────────────────┬────────────────────────────┘
                 │
       ┌─────────┴──────────┐
       ▼                    ▼
┌─────────────┐      ┌──────────────┐
│  Consumer 1 │      │  Consumer 2  │
│  (Products) │      │  (Reviews)   │
└──────┬──────┘      └──────┬───────┘
       │                    │
       └─────────┬──────────┘
                 ▼
┌─────────────────────────────────────────────┐
│          PostgreSQL + TimescaleDB           │
│  - products (info, price history)           │
│  - reviews (comments, ratings)              │
│  - sentiment_analysis (ML results)          │
│  - price_tracking (time-series)             │
└────────────────┬────────────────────────────┘
                 │
       ┌─────────┴──────────┐
       ▼                    ▼
┌─────────────┐      ┌──────────────────┐
│  Metabase   │      │  Sentiment ML    │
│ (Dashboards)│      │  (TextBlob/BERT) │
└─────────────┘      └──────────────────┘
```

## 🛠️ Tech Stack

- **Web Crawling**: 
  - Scrapy (crawl framework)
  - Selenium (dynamic content)
  - BeautifulSoup4 (HTML parsing)
  - Requests (HTTP requests)
- **Streaming**: Apache Kafka
- **Database**: PostgreSQL + TimescaleDB (time-series cho price tracking)
- **Backend**: Python 3.10+
  - Kafka: confluent-kafka-python
  - Data Processing: Pandas, NumPy
  - Sentiment Analysis: TextBlob, VADER, hoặc PhoBERT (tiếng Việt)
  - API: FastAPI (optional)
- **BI & Visualization**: 
  - Metabase (Business Intelligence)
- **DevOps**: Docker, Docker Compose

## 📊 Các thành phần hệ thống

### 1. Kafka Topics (2 topics)

| Topic | Mô tả | Schema |
|-------|-------|--------|
| `uit-products` | Thông tin sản phẩm từ uit | product_id, name, price, original_price, rating, sold_count, shop_id, category, images, url, crawled_at |
| `uit-reviews` | Bình luận sản phẩm | review_id, product_id, user_name, rating, comment, images, helpful_count, created_at, crawled_at |

### 2. PostgreSQL Schema

**Tables chính:**
- `products`: Thông tin sản phẩm
- `categories`: Danh mục sản phẩm
- `reviews`: Bình luận khách hàng
- `review_sentiment`: Kết quả phân tích sentiment
- `shops`: Thông tin shop
- `orders`: Đơn hàng
- `order_lines`: Line chi tiểt

**Aggregated Views (cho Metabase):**
- `product_stats_daily`: Thống kê sản phẩm theo ngày
- `sentiment_summary`: Tổng hợp sentiment theo sản phẩm
- `price_changes`: Sản phẩm có thay đổi giá

### 3. Các dịch vụ Python

| Dịch vụ | Mô tả | Công nghệ |
|---------|-------|------|
| Product Crawler | Crawl thông tin sản phẩm từ Tiki | Scrapy/Selenium, Requests |
| Review Crawler | Crawl bình luận sản phẩm | Scrapy/Selenium |
| Kafka Producer | Đẩy dữ liệu crawl vào Kafka | confluent-kafka |
| Product Consumer | Nhận và lưu dữ liệu sản phẩm | confluent-kafka, asyncio |
| Review Consumer | Nhận và lưu bình luận | confluent-kafka, asyncio |
| Sentiment Analyzer | Phân tích cảm xúc bình luận | TextBlob/VADER/PhoBERT |
| Price Tracker | Theo dõi thay đổi giá | Pandas, TimescaleDB |
| Data Cleaner | Làm sạch và chuẩn hóa dữ liệu | Pandas, regex |

### 4. Metabase Dashboards (10-12 dashboards)

**Dashboard Tổng quan:**
- Tổng số sản phẩm đã crawl
- Tổng số bình luận đã thu thập
- Số lượng shops được theo dõi
- Thống kê crawling (thành công/lỗi)

**Phân tích Sản phẩm:**
- Top 20 sản phẩm bán chạy nhất (theo sold_count)
- Phân bố giá sản phẩm theo danh mục
- Sản phẩm có rating cao nhất (>= 4.5 sao)
- Sản phẩm đang giảm giá mạnh nhất

**Theo dõi Giá cả:**
- Biểu đồ lịch sử giá theo sản phẩm (time-series)
- Sản phẩm có dao động giá lớn
- So sánh giá trung bình theo danh mục
- Phát hiện giá tốt (price drop alerts)

**Phân tích Sentiment (Cảm xúc):**
- Tỷ lệ sentiment: Positive / Negative / Neutral
- Top sản phẩm có sentiment tích cực nhất
- Top sản phẩm có sentiment tiêu cực nhất
- Word cloud từ bình luận (từ khóa phổ biến)
- Xu hướng sentiment theo thời gian

**Phân tích Rating & Review:**
- Phân bố rating (1-5 sao)
- Số lượng review theo sản phẩm
- Correlation giữa rating và sold_count
- Sản phẩm có nhiều review nhất

**Phân tích Shop:**
- Top shops có nhiều sản phẩm nhất
- Top shops có rating cao nhất
- So sánh giá trung bình theo shop

### 5. Streamlit Real-time Monitor

- Kafka consumer lag monitoring
- Event processing rate
- Database connection pool status
- ML model predictions live
- System health metrics

## 🎁 Features nổi bật

### Core Features:
✅ **Web Crawling**: Thu thập dữ liệu sản phẩm và bình luận từ Tiki  
✅ **Real-time Streaming**: Kafka streaming pipeline cho dữ liệu crawl  
✅ **Time-series Tracking**: Theo dõi lịch sử giá với TimescaleDB  
✅ **Sentiment Analysis**: Phân tích cảm xúc từ bình luận (tiếng Việt)  
✅ **BI Dashboards**: 10+ Metabase dashboards với insights chi tiết  

### Advanced Features:
✅ **Price Change Detection**: Phát hiện sản phẩm giảm giá, tăng giá  
✅ **Product Recommendation**: Gợi ý sản phẩm dựa trên sentiment và rating  
✅ **Trend Analysis**: Phát hiện sản phẩm đang trending  
✅ **Shop Analytics**: So sánh và phân tích shops  

### Bonus Features:
✅ **Duplicate Detection**: Loại bỏ sản phẩm/review trùng lặp  
✅ **Auto Re-crawl**: Tự động crawl lại sản phẩm theo schedule  
✅ **Data Quality Check**: Kiểm tra và làm sạch dữ liệu  
✅ **Export Data**: Export dữ liệu ra CSV/JSON  

## 📅 Timeline thực hiện (12 tuần)

### Giai đoạn 1: Cài đặt & Nền tảng (Tuần 1-2)
- [ ] Cài đặt môi trường Docker
- [ ] Thiết lập Kafka cluster (Zookeeper + Kafka broker)
- [ ] Cài đặt PostgreSQL + TimescaleDB
- [ ] Thiết lập Metabase và kết nối PostgreSQL
- [ ] Cấu trúc Git repository
- [ ] Requirements.txt (scrapy, selenium, kafka, psycopg2, etc.)
- [ ] Nghiên cứu Tiki API/structure

### Giai đoạn 2: Web Crawling (Tuần 3-4)
- [ ] Thiết kế database schema (products, reviews, prices, sentiment)
- [ ] Tạo tables, indexes, TimescaleDB hypertables
- [ ] Phát triển Tiki Product Crawler
  - [ ] Xác định URL patterns
  - [ ] Parse thông tin sản phẩm (tên, giá, rating, sold)
  - [ ] Xử lý pagination
  - [ ] Handle dynamic content (Selenium nếu cần)
- [ ] Phát triển Review Crawler
  - [ ] Crawl bình luận từ từng sản phẩm
  - [ ] Thu thập rating, comment, user, timestamp
- [ ] Triển khai Kafka producers (gửi data vào Kafka)
- [ ] Test crawlers với sample data

### Giai đoạn 3: Streaming & Lưu trữ (Tuần 5-6)
- [ ] Kafka consumers (2 consumers)
  - [ ] Product consumer (nhận và lưu sản phẩm)
  - [ ] Review consumer (nhận và lưu bình luận)
- [ ] Data cleaning & validation
  - [ ] Loại bỏ duplicate
  - [ ] Chuẩn hóa dữ liệu
  - [ ] Handle missing values
- [ ] Lưu dữ liệu vào PostgreSQL
- [ ] Thiết lập TimescaleDB continuous aggregates
- [ ] Xử lý lỗi & logging
- [ ] Schedule crawlers (daily/hourly)

### Giai đoạn 4: Sentiment Analysis (Tuần 7-8)
- [ ] Chọn phương pháp sentiment analysis
  - [ ] TextBlob/VADER (tiếng Anh)
  - [ ] PhoBERT (tiếng Việt - recommend)
  - [ ] Custom model (tùy chọn)
- [ ] Tiền xử lý text (tokenization, cleaning)
- [ ] Phân tích sentiment cho tất cả reviews
- [ ] Lưu kết quả vào bảng `review_sentiment`
- [ ] Tạo aggregated views cho Metabase
- [ ] Đánh giá accuracy của model

### Giai đoạn 5: Metabase Dashboards (Tuần 9-10)
- [ ] Kết nối Metabase với PostgreSQL
- [ ] Tạo 10-12 dashboards:
  - [ ] Dashboard Tổng quan
  - [ ] Phân tích Sản phẩm
  - [ ] Theo dõi Giá cả (time-series charts)
  - [ ] Phân tích Sentiment
  - [ ] Phân tích Rating & Review
  - [ ] Phân tích Shop
- [ ] Tạo custom SQL queries
- [ ] Thiết lập filters và drill-down
- [ ] Thiết lập alerts (giá giảm mạnh, sentiment tiêu cực)

### Giai đoạn 6: Optimization & Features (Tuần 11)
- [ ] Optimize crawler performance
  - [ ] Rate limiting
  - [ ] Concurrent requests
  - [ ] Retry mechanism
- [ ] Triển khai price change detection
- [ ] Phát hiện trending products
- [ ] Tạo product recommendation logic
- [ ] Export data functionality (CSV/JSON)
- [ ] Tối ưu hóa database queries

### Giai đoạn 7: Tài liệu & Demo (Tuần 12)
- [ ] Tài liệu kỹ thuật
  - [ ] Hướng dẫn sử dụng crawlers
  - [ ] Database schema documentation
  - [ ] Kafka topics documentation
- [ ] Hướng dẫn sử dụng Metabase dashboards
- [ ] Chuẩn bị demo
  - [ ] Demo video (5-10 phút)
  - [ ] Slides thuyết trình
- [ ] Code cleanup & comments
- [ ] README với Getting Started guide

## 📁 Cấu trúc thư mục

```
project/
├── docker/
│   ├── docker-compose.yml
│   ├── kafka/
│   ├── postgres/
│   │   └── init.sql
│   └── metabase/
├── src/
│   ├── crawlers/
│   │   ├── uit_product_crawler.py
│   │   ├── uit_review_crawler.py
│   │   ├── spiders/
│   │   │   ├── product_spider.py
│   │   │   └── review_spider.py
│   │   └── scrapy.cfg
│   ├── producers/
│   │   ├── product_producer.py
│   │   └── review_producer.py
│   ├── consumers/
│   │   ├── product_consumer.py
│   │   └── review_consumer.py
│   ├── sentiment/
│   │   ├── sentiment_analyzer.py
│   │   ├── phobert_model.py
│   │   └── text_preprocessor.py
│   ├── utils/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logger.py
│   │   └── data_cleaner.py
│   └── scheduler/
│       ├── crawler_scheduler.py
│       └── price_tracker.py
├── sql/
│   ├── schema.sql
│   ├── views.sql
│   └── indexes.sql
├── metabase/
│   ├── dashboards/
│   │   ├── overview.json
│   │   ├── products.json
│   │   ├── sentiment.json
│   │   └── price_tracking.json
│   └── queries/
├── notebooks/
│   ├── eda_products.ipynb
│   ├── eda_reviews.ipynb
│   └── sentiment_training.ipynb
├── tests/
│   ├── test_crawlers.py
│   ├── test_kafka.py
│   └── test_sentiment.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CRAWLING_GUIDE.md
│   ├── DATABASE_SCHEMA.md
│   └── METABASE_GUIDE.md
├── data/
│   ├── sample_products.json
│   └── sample_reviews.json
├── logs/
│   └── .gitkeep
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- 8GB RAM minimum
- 20GB disk space

### Installation

1. Clone repository:
```bash
git clone <repo-url>
cd project
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Start services with Docker:
```bash
docker-compose up -d
```

4. Install Python dependencies:
```bash
pip install -r requirements.txt
```

5. Setup database:
```bash
python src/utils/setup_db.py
```

6. Generate initial data:
```bash
python src/data_generator/generate_all.py
```

7. Start producers:
```bash
python src/producers/start_all.py
```

8. Start consumers:
```bash
python src/consumers/start_all.py
```

9. Access services:
- Metabase: http://localhost:3000
- Streamlit: http://localhost:8501
- FastAPI: http://localhost:8000/docs

## 📈 Metrics & KPIs

### Technical Metrics:
- **Crawling Performance**:
  - Products crawled per hour
  - Reviews crawled per hour
  - Crawler success rate (>95%)
  - Average response time per request
- **Kafka Metrics**:
  - Message throughput: events/second
  - Consumer lag: < 1000 messages
- **Database Performance**:
  - Write throughput: inserts/second
  - Query response time: < 200ms (p95)

### Business Metrics:
- **Data Collection**:
  - Total products tracked
  - Total reviews collected
  - Number of shops monitored
  - Data freshness (last crawl time)
- **Product Analytics**:
  - Average product price by category
  - Price volatility index
  - Top selling products (by sold_count)
  - Rating distribution
- **Sentiment Metrics**:
  - Positive sentiment ratio
  - Negative sentiment ratio
  - Sentiment trend over time
  - Products with declining sentiment

## 🎓 Kiến thức áp dụng

- **Big Data Concepts**: 3Vs (Volume - nhiều sản phẩm/reviews, Velocity - real-time crawling, Variety - text, numbers, time-series)
- **Web Scraping**: Scrapy framework, Selenium, anti-bot techniques
- **Stream Processing**: Kafka pub-sub pattern, event-driven architecture
- **Time-series Database**: TimescaleDB cho price tracking
- **Natural Language Processing**: Sentiment analysis, text preprocessing
- **Data Warehousing**: Schema design, indexing strategies
- **Business Intelligence**: Dashboard design, data visualization
- **ETL Pipeline**: Data cleaning, transformation, loading

## 📚 Tài liệu tham khảo

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [TimescaleDB Tutorials](https://docs.timescale.com/)
- [Metabase Documentation](https://www.metabase.com/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 👥 Team

- **Họ tên**: [Tên của bạn]
- **MSSV**: [Mã số sinh viên]
- **Lớp**: [Lớp học phần]

## 📝 License

MIT License

---

**Note**: Project này phục vụ mục đích học tập cho môn Công nghệ Dữ liệu Lớn.
