#!/bin/bash
set -e

echo "🚀 UIT Big Data Application Starting..."

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "✓ PostgreSQL is ready"

# Wait for Kafka
echo "⏳ Waiting for Kafka..."
while ! nc -z kafka 9092; do
  sleep 1
done
echo "✓ Kafka is ready"

# Check what service to run based on environment variable
SERVICE=${SERVICE:-check}

case "$SERVICE" in
  "check")
    echo "🔍 Running system check..."
    python src/manage.py check
    ;;
  
  "init-db")
    echo "📊 Initializing database..."
    python src/manage.py init-db
    ;;
  
  "create-topics")
    echo "📨 Creating Kafka topics..."
    python src/manage.py create-kafka-topics
    ;;
  
  "crawl-products")
    echo "🕷️ Starting product crawler..."
    CATEGORY_ID=${CATEGORY_ID:-1789}
    MAX_PAGES=${MAX_PAGES:-10}
    python src/manage.py crawl-products --category-id $CATEGORY_ID --max-pages $MAX_PAGES
    ;;
  
  "crawl-reviews")
    echo "🕷️ Starting review crawler..."
    if [ -z "$PRODUCT_IDS" ]; then
      echo "❌ Error: PRODUCT_IDS environment variable is required"
      exit 1
    fi
    MAX_PAGES=${MAX_PAGES:-5}
    python src/manage.py crawl-reviews --product-ids "$PRODUCT_IDS" --max-pages $MAX_PAGES
    ;;
  
  "consumer-products")
    echo "📥 Starting product consumer..."
    python src/app/consumers/product_consumer.py
    ;;
  
  "consumer-reviews")
    echo "📥 Starting review consumer..."
    python src/app/consumers/review_consumer.py
    ;;
  
  "consumers-all")
    echo "📥 Starting all consumers..."
    python src/app/consumers/run_all.py
    ;;
  
  "shell")
    echo "🐚 Starting interactive shell..."
    /bin/bash
    ;;
  
  *)
    echo "❌ Unknown service: $SERVICE"
    echo "Available services: check, init-db, create-topics, crawl-products, crawl-reviews, consumer-products, consumer-reviews, consumers-all, shell"
    exit 1
    ;;
esac

echo "✨ Done!"
