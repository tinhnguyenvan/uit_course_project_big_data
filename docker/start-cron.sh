#!/bin/bash
set -e

echo "🕐 Starting Cron Service for Tiki Crawler"
echo "========================================"

# Wait for dependencies
echo "⏳ Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "✓ PostgreSQL is ready"

echo "⏳ Waiting for Kafka..."
while ! nc -z kafka 9092; do
  sleep 1
done
echo "✓ Kafka is ready"

# Setup crontab
echo "📝 Installing crontab..."
cp /app/docker/crontab /etc/cron.d/tiki-crawler
chmod 0644 /etc/cron.d/tiki-crawler

# Apply crontab
crontab /etc/cron.d/tiki-crawler

# Create log files
mkdir -p /app/logs
touch /app/logs/cron-crawler.log
touch /app/logs/cron-heartbeat.log

# Show schedule
echo "✓ Crontab installed"
echo ""
echo "📅 Cron Schedule:"
crontab -l | grep -v "^#" | grep -v "^$" || echo "  No active jobs"
echo ""
echo "📝 Logs:"
echo "  - Crawler: /app/logs/cron-crawler.log"
echo "  - Heartbeat: /app/logs/cron-heartbeat.log"
echo ""
echo "🚀 Starting cron daemon..."
echo "========================================"

# Start cron in foreground and tail logs
cron && tail -f /app/logs/cron-crawler.log /app/logs/cron-heartbeat.log
