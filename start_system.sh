#!/bin/bash
# Khởi động hoàn chỉnh hệ thống crawling

echo "🚀 Starting UIT Big Data System"
echo "================================"

# Step 1: Build containers
echo ""
echo "📦 Step 1: Building Docker containers..."
docker-compose build app
if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi
echo "✅ Build completed"

# Step 2: Start all infrastructure services
echo ""
echo "🔧 Step 2: Starting infrastructure services..."
docker-compose up -d zookeeper kafka postgres metabase conduktor-console conduktor-postgresql
sleep 5
echo "✅ Infrastructure services started"

# Step 3: Initialize database
echo ""
echo "📊 Step 3: Initializing database..."
SERVICE=init-db docker-compose up app
if [ $? -ne 0 ]; then
    echo "❌ Database initialization failed!"
    exit 1
fi
echo "✅ Database initialized"

# Step 4: Create Kafka topics
echo ""
echo "📨 Step 4: Creating Kafka topics..."
SERVICE=create-topics docker-compose up app
if [ $? -ne 0 ]; then
    echo "❌ Topic creation failed!"
    exit 1
fi
echo "✅ Kafka topics created"

# Step 5: Start consumers
echo ""
echo "📥 Step 5: Starting Kafka consumers..."
SERVICE=consumers-all docker-compose up -d app
sleep 3
echo "✅ Consumers started"

# Step 6: Show status
echo ""
echo "================================"
echo "✨ System Ready!"
echo "================================"
echo ""
echo "📊 Services:"
echo "  - PostgreSQL:     localhost:54325"
echo "  - Kafka:          localhost:9092"
echo "  - Conduktor:      http://localhost:8081"
echo "  - Metabase:       http://localhost:3000"
echo ""
echo "🕷️  To start crawler:"
echo "  ./run_crawler.sh"
echo ""
echo "📝 Monitor logs:"
echo "  docker-compose logs -f app"
echo ""
echo "🛑 Stop all:"
echo "  docker-compose down"
echo ""
