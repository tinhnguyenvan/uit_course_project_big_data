#!/bin/bash

echo "🔍 Verifying Sentiment Analysis Setup"
echo "======================================"

# 1. Check if torch is installed
echo ""
echo "1️⃣ Checking PyTorch installation..."
docker compose run --rm consumers python -c "import torch; print(f'✅ PyTorch {torch.__version__}')" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ PyTorch installed"
else
    echo "   ❌ PyTorch NOT installed"
    exit 1
fi

# 2. Check transformers
echo ""
echo "2️⃣ Checking Transformers installation..."
docker compose run --rm consumers python -c "import transformers; print(f'✅ Transformers {transformers.__version__}')" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ Transformers installed"
else
    echo "   ❌ Transformers NOT installed"
    exit 1
fi

# 3. Check sentiment consumer can import
echo ""
echo "3️⃣ Checking SentimentConsumer imports..."
docker compose run --rm consumers python -c "from app.consumers.sentiment_consumer import SentimentConsumer; print('✅ SentimentConsumer imports successfully')" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ SentimentConsumer imports OK"
else
    echo "   ❌ SentimentConsumer import FAILED"
    exit 1
fi

# 4. Check Kafka topic exists
echo ""
echo "4️⃣ Checking Kafka topic..."
TOPIC_EXISTS=$(docker exec uit-bd-kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null | grep "uit-sentiment-analysis")
if [ -n "$TOPIC_EXISTS" ]; then
    echo "   ✅ Topic 'uit-sentiment-analysis' exists"
else
    echo "   ⚠️  Topic 'uit-sentiment-analysis' not found"
    echo "   Creating topic..."
    docker exec uit-bd-kafka kafka-topics \
        --create \
        --if-not-exists \
        --bootstrap-server localhost:9092 \
        --replication-factor 1 \
        --partitions 3 \
        --topic uit-sentiment-analysis
    echo "   ✅ Topic created"
fi

# 5. Check database table
echo ""
echo "5️⃣ Checking database table..."
TABLE_EXISTS=$(docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -tAc "SELECT to_regclass('public.review_sentiment')" 2>/dev/null)
if [ "$TABLE_EXISTS" = "review_sentiment" ]; then
    echo "   ✅ Table 'review_sentiment' exists"
else
    echo "   ❌ Table 'review_sentiment' NOT found"
    echo "   Run migration: ./scripts/apply_complete_migration.sh"
    exit 1
fi

echo ""
echo "======================================"
echo "✅ All checks passed!"
echo ""
echo "🚀 Ready to start sentiment analysis:"
echo "   docker compose up -d consumers"
echo ""
echo "📊 Monitor logs:"
echo "   docker logs -f uit-bd-consumers | grep SENTIMENT"
