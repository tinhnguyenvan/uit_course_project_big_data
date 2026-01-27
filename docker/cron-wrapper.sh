#!/bin/bash
# Wrapper script for cron jobs to ensure environment variables are set

# Source environment variables
export $(grep -v '^#' /app/.env | xargs)

# Set defaults if not present
export POSTGRES_HOST=${POSTGRES_HOST:-postgres}
export POSTGRES_PORT=${POSTGRES_PORT:-5432}
export POSTGRES_DB=${POSTGRES_DB:-uit_analytics}
export POSTGRES_USER=${POSTGRES_USER:-uit_user}
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-uit_password}
export KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-kafka:29092}
export KAFKA_TOPIC_PRODUCTS=${KAFKA_TOPIC_PRODUCTS:-uit-products}
export KAFKA_TOPIC_REVIEWS=${KAFKA_TOPIC_REVIEWS:-uit-reviews}
export KAFKA_TOPIC_PRICES=${KAFKA_TOPIC_PRICES:-uit-prices}
export KAFKA_TOPIC_SHOPS=${KAFKA_TOPIC_SHOPS:-uit-shops}

# Log start time
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting crawler with SERVICE=$SERVICE CATEGORY_ID=$CATEGORY_ID MAX_PAGES=$MAX_PAGES"

# Change to app directory
cd /app/src

# Run the crawler using scrapy directly
if [ "$SERVICE" = "crawl-listing" ]; then
    if [ -n "$MAX_PAGES" ]; then
        scrapy crawl tiki_listing -a category_id=${CATEGORY_ID:-870} -a max_pages=${MAX_PAGES} -a resume=${RESUME:-true}
    else
        scrapy crawl tiki_listing -a category_id=${CATEGORY_ID:-870} -a resume=${RESUME:-true}
    fi
fi

# Log completion
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Crawler finished"
