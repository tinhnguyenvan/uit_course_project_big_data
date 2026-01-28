# 🧠 Sentiment Analysis Pipeline - Hướng Dẫn

## 📖 Tổng Quan

Hệ thống phân tích cảm xúc tự động cho các đánh giá sản phẩm sử dụng **PhoBERT** (Vietnamese BERT).

### 🎯 Mục Tiêu

- **Tự động phân tích** cảm xúc từng review sau khi được lưu
- **Phân loại** cảm xúc: `positive`, `negative`, `neutral`
- **Tính toán** độ tin cậy (confidence score)
- **Lưu trữ** kết quả vào database để truy vấn/phân tích

---

## 🏗️ Kiến Trúc Pipeline

```
ReviewConsumer (Lưu review)
       │
       ├─→ Kafka Topic: uit-orders (Tạo đơn hàng)
       │
       └─→ Kafka Topic: uit-sentiment-analysis (Phân tích cảm xúc)
                    ↓
         SentimentConsumer (PhoBERT Model)
                    ↓
         review_sentiment table (Database)
```

### 📊 Luồng Dữ Liệu

1. **ReviewConsumer** nhận review từ topic `uit-review-detail`
2. Lưu review vào bảng `reviews`
3. Push 2 messages:
   - → `uit-orders`: Tạo đơn hàng
   - → `uit-sentiment-analysis`: Phân tích cảm xúc
4. **SentimentConsumer** nhận message từ `uit-sentiment-analysis`
5. Sử dụng PhoBERT phân tích cảm xúc
6. Lưu kết quả vào `review_sentiment`

---

## 🛠️ Cài Đặt

### 1. Cài Dependencies

```bash
# Cài các thư viện ML (PyTorch + Transformers)
cd /Users/tinhnguyen/Sites/UIT/12_cong_nghe_du_lieu_lon/project
pip install -r requirements.txt

# Hoặc cài riêng lẻ:
pip install transformers==4.35.2 torch==2.1.1 sentencepiece==0.1.99
```

**Lưu ý:**
- PyTorch size ~2GB (CPU version)
- GPU: Cài `torch` với CUDA nếu có GPU

### 2. Tạo Kafka Topic

```bash
docker exec uit-bd-kafka kafka-topics \
  --create \
  --bootstrap-server localhost:9092 \
  --replication-factor 1 \
  --partitions 3 \
  --topic uit-sentiment-analysis
```

Verify:
```bash
docker exec uit-bd-kafka kafka-topics \
  --list \
  --bootstrap-server localhost:9092 | grep sentiment
```

Expected: `uit-sentiment-analysis`

### 3. Verify Database Schema

Bảng `review_sentiment` đã có sẵn trong migration:

```sql
-- Kiểm tra bảng
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  SELECT column_name, data_type 
  FROM information_schema.columns 
  WHERE table_name = 'review_sentiment';
"
```

Expected:
```
 column_name | data_type
-------------+-----------
 review_id   | bigint
 sentiment   | varchar
 confidence  | decimal
 analyzed_at | timestamp
```

---

## 🚀 Sử Dụng

### Option 1: Chạy Tất Cả Consumers (Recommended)

```bash
# 6 consumers song song (bao gồm SentimentConsumer)
docker compose up -d consumers
```

Hoặc chạy manual:
```bash
cd src/app/consumers
python -m run_all
```

### Option 2: Chạy Riêng SentimentConsumer

```bash
# Test riêng sentiment consumer
cd src/app/consumers
python sentiment_consumer.py
```

---

## 🧪 Testing

### Test 1: Gửi Sample Review

```bash
# Tạo test message
cat > test_sentiment.json << 'EOF'
{
  "review_id": 999999,
  "product_id": 123456,
  "comment": "Sản phẩm tuyệt vời! Chất lượng rất tốt, giao hàng nhanh. Tôi rất hài lòng!",
  "rating": 5,
  "created_at": "2026-01-28T10:00:00"
}
EOF

# Push vào topic
docker exec -i uit-bd-kafka kafka-console-producer \
  --broker-list localhost:9092 \
  --topic uit-sentiment-analysis < test_sentiment.json
```

### Test 2: Kiểm Tra Kết Quả

```bash
# Xem log consumer
docker logs -f uit-bd-consumers | grep SENTIMENT

# Expected:
# [SENTIMENT] Analyzing sentiment for review 999999
# [SENTIMENT] Saved sentiment for review 999999: positive (confidence: 0.9854)
```

### Test 3: Query Database

```sql
-- Xem kết quả phân tích
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  SELECT 
    rs.review_id,
    r.comment,
    r.rating,
    rs.sentiment,
    rs.confidence,
    rs.analyzed_at
  FROM review_sentiment rs
  JOIN reviews r ON rs.review_id = r.review_id
  ORDER BY rs.analyzed_at DESC
  LIMIT 10;
"
```

---

## 📈 Model PhoBERT

### Model Đang Sử Dụng

**uitnlp/visobert** - Vietnamese Sentiment BERT
- Hugging Face: https://huggingface.co/uitnlp/visobert
- Training: Vietnamese sentiment dataset
- Output: `positive`, `negative`, `neutral`

### Cấu Hình

Trong [config.py](../src/app/config.py):

```python
# Sentiment Analysis
SENTIMENT_MODEL_NAME = 'uitnlp/visobert'  # PhoBERT cho tiếng Việt
SENTIMENT_BATCH_SIZE = 8                  # Batch processing
SENTIMENT_MAX_LENGTH = 256                # Max tokens
SENTIMENT_DEVICE = 'cpu'                  # 'cpu' hoặc 'cuda'
```

### Thay Đổi Model

Để sử dụng model khác:

```bash
# 1. Thêm vào .env
echo "SENTIMENT_MODEL_NAME=vinai/phobert-base" >> .env

# 2. Restart consumers
docker compose restart consumers
```

**Models thay thế:**
- `vinai/phobert-base` - Base PhoBERT
- `wonrax/phobert-base-vietnamese-sentiment` - Sentiment fine-tuned
- `uitnlp/visobert` - ViSoBERT (đang dùng)

---

## 📊 Phân Tích Kết Quả

### Query 1: Tổng Hợp Cảm Xúc

```sql
SELECT 
  sentiment,
  COUNT(*) as total_reviews,
  ROUND(AVG(confidence)::numeric, 4) as avg_confidence,
  ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) as percentage
FROM review_sentiment
GROUP BY sentiment
ORDER BY total_reviews DESC;
```

Expected Output:
```
sentiment | total_reviews | avg_confidence | percentage
----------+---------------+----------------+-----------
positive  |         45231 |         0.8923 |      76.89
negative  |         10450 |         0.8456 |      17.76
neutral   |          3120 |         0.7234 |       5.35
```

### Query 2: Mismatch Rating vs Sentiment

Tìm review có rating cao nhưng sentiment negative:

```sql
SELECT 
  r.review_id,
  r.rating,
  rs.sentiment,
  rs.confidence,
  r.comment
FROM reviews r
JOIN review_sentiment rs ON r.review_id = rs.review_id
WHERE r.rating >= 4 AND rs.sentiment = 'negative'
ORDER BY rs.confidence DESC
LIMIT 10;
```

### Query 3: Sentiment Trend Theo Thời Gian

```sql
SELECT 
  DATE(rs.analyzed_at) as date,
  sentiment,
  COUNT(*) as count
FROM review_sentiment rs
WHERE analyzed_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(rs.analyzed_at), sentiment
ORDER BY date DESC, sentiment;
```

---

## 🎯 Performance

### Tốc Độ Xử Lý

**CPU (Intel i5):**
- Single review: ~200-500ms
- Batch 8 reviews: ~1-2 seconds
- Throughput: ~200-400 reviews/minute

**GPU (NVIDIA T4):**
- Single review: ~50-100ms
- Batch 32 reviews: ~500ms-1s
- Throughput: ~2000-3000 reviews/minute

### Tối Ưu Hóa

#### 1. Tăng Batch Size (nếu có RAM)

```python
# .env
SENTIMENT_BATCH_SIZE=16  # Mặc định: 8
```

#### 2. Sử Dụng GPU

```python
# .env
SENTIMENT_DEVICE=cuda

# Cài CUDA-enabled PyTorch
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

#### 3. Giảm Max Length (nếu comment ngắn)

```python
# .env
SENTIMENT_MAX_LENGTH=128  # Mặc định: 256
```

---

## 🐛 Troubleshooting

### Lỗi: Model Download Failed

```bash
# Download thủ công
python -c "
from transformers import AutoTokenizer, AutoModelForSequenceClassification
AutoTokenizer.from_pretrained('uitnlp/visobert')
AutoModelForSequenceClassification.from_pretrained('uitnlp/visobert')
"
```

### Lỗi: Out of Memory

Giảm batch size:
```python
# .env
SENTIMENT_BATCH_SIZE=4  # Giảm từ 8 xuống 4
```

### Lỗi: Topic không tồn tại

```bash
# Tạo lại topic
docker exec uit-bd-kafka kafka-topics \
  --create \
  --bootstrap-server localhost:9092 \
  --topic uit-sentiment-analysis
```

### Consumer Không Chạy

```bash
# Check logs
docker logs uit-bd-consumers | grep SENTIMENT

# Test riêng
docker compose run --rm app python -m app.consumers.sentiment_consumer
```

---

## 📚 Database Schema

### Bảng `review_sentiment`

```sql
CREATE TABLE review_sentiment (
    review_id BIGINT PRIMARY KEY REFERENCES reviews(review_id),
    sentiment VARCHAR(20),      -- 'positive', 'negative', 'neutral'
    confidence DECIMAL(5,4),    -- 0.0000 - 1.0000
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index
CREATE INDEX idx_sentiment ON review_sentiment(sentiment);
CREATE INDEX idx_confidence ON review_sentiment(confidence);
```

### Join với Reviews

```sql
-- Xem đầy đủ thông tin review + sentiment
SELECT 
  r.review_id,
  r.product_id,
  r.user_name,
  r.rating,
  r.comment,
  r.created_at,
  rs.sentiment,
  rs.confidence,
  rs.analyzed_at
FROM reviews r
LEFT JOIN review_sentiment rs ON r.review_id = rs.review_id
WHERE rs.sentiment IS NOT NULL
ORDER BY r.created_at DESC;
```

---

## 🔄 Integration với Existing Reviews

### Backfill Sentiment cho Reviews Cũ

Tạo script backfill:

```python
# src/backfill_sentiments.py
import json
from confluent_kafka import Producer
from app.models import SessionLocal, Review
from app.config import config

def backfill_sentiments():
    """Push tất cả reviews chưa có sentiment vào topic"""
    db = SessionLocal()
    producer = Producer({'bootstrap.servers': config.KAFKA_BOOTSTRAP_SERVERS})
    
    # Lấy reviews chưa có sentiment
    reviews = db.query(Review).filter(
        ~Review.review_id.in_(
            db.query(ReviewSentiment.review_id)
        )
    ).limit(10000).all()
    
    print(f"Found {len(reviews)} reviews without sentiment")
    
    for review in reviews:
        message = {
            'review_id': review.review_id,
            'product_id': review.product_id,
            'comment': review.comment,
            'rating': review.rating,
            'created_at': review.created_at.isoformat()
        }
        
        producer.produce(
            config.KAFKA_TOPIC_SENTIMENT_ANALYSIS,
            key=str(review.review_id).encode('utf-8'),
            value=json.dumps(message).encode('utf-8')
        )
    
    producer.flush()
    print(f"Pushed {len(reviews)} messages to sentiment topic")
    db.close()

if __name__ == '__main__':
    backfill_sentiments()
```

Chạy:
```bash
python src/backfill_sentiments.py
```

---

## 📊 Analytics Views

### View: Sentiment Summary by Product

```sql
CREATE VIEW product_sentiment_summary AS
SELECT 
  r.product_id,
  p.name as product_name,
  COUNT(*) as total_reviews,
  COUNT(CASE WHEN rs.sentiment = 'positive' THEN 1 END) as positive_count,
  COUNT(CASE WHEN rs.sentiment = 'negative' THEN 1 END) as negative_count,
  COUNT(CASE WHEN rs.sentiment = 'neutral' THEN 1 END) as neutral_count,
  ROUND(AVG(rs.confidence)::numeric, 4) as avg_confidence
FROM reviews r
JOIN review_sentiment rs ON r.review_id = rs.review_id
JOIN products p ON r.product_id = p.product_id
GROUP BY r.product_id, p.name;

-- Query
SELECT * FROM product_sentiment_summary 
ORDER BY total_reviews DESC 
LIMIT 10;
```

---

## ✅ Summary

| Aspect | Detail |
|--------|--------|
| **Model** | uitnlp/visobert (PhoBERT) |
| **Input** | Vietnamese review comments |
| **Output** | positive/negative/neutral + confidence |
| **Pipeline** | ReviewConsumer → Topic → SentimentConsumer → DB |
| **Performance** | ~200-400 reviews/min (CPU) |
| **Database** | review_sentiment table |
| **Consumers** | 6 parallel (bao gồm Sentiment) |

🎉 **Sentiment Analysis Pipeline hoàn chỉnh!**
