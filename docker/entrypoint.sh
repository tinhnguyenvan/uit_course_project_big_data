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
  
  "crawl-listing")
    echo "🕷️ Starting listing crawler (with resume)..."
    CATEGORY_ID=${CATEGORY_ID:-870}
    MAX_PAGES=${MAX_PAGES:-}
    RESUME=${RESUME:-true}
    cd /app/src
    if [ -n "$MAX_PAGES" ]; then
      scrapy crawl tiki_listing -a category_id=$CATEGORY_ID -a max_pages=$MAX_PAGES -a resume=$RESUME
    else
      scrapy crawl tiki_listing -a category_id=$CATEGORY_ID -a resume=$RESUME
    fi
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
    python src/manage.py start-consumers --consumer products
    ;;
  
  "consumer-reviews")
    echo "📥 Starting review consumer..."
    python src/manage.py start-consumers --consumer reviews
    ;;
  
  "consumers-all")
    echo "📥 Starting all consumers..."
    python src/manage.py start-consumers --consumer all
    ;;
  
  "cron")
    echo "🕐 Starting cron service..."
    /app/docker/start-cron.sh
    ;;
  
  "shell")
    echo "🐚 Starting interactive shell..."
    /bin/bash
    ;;
  
  "cron")
    echo "🕐 Starting cron service..."
    /app/docker/start-cron.sh
    ;;
  
  *)
    echo "❌ Unknown service: $SERVICE"
    echo "Available services: check, init-db, create-topics, crawl-products, crawl-listing, crawl-reviews, consumer-products, consumer-reviews, consumers-all, cron, shell"
    exit 1
    ;;
esac

echo "✨ Done!"
