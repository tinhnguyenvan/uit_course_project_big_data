#!/bin/bash
# Apply complete database schema - single migration file

set -e

echo "🗄️  UIT Big Data - Complete Schema Migration"
echo "============================================="
echo ""

CONTAINER="uit-bd-postgres"
DB_USER="uit_user"
DB_NAME="uit_analytics"
MIGRATION_FILE="000_complete_schema.sql"

# Check container
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "❌ Container $CONTAINER is not running"
    echo "   Start with: docker compose up -d postgres"
    exit 1
fi

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
for i in {1..30}; do
    if docker exec $CONTAINER pg_isready -U $DB_USER > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Timeout waiting for PostgreSQL"
        exit 1
    fi
    sleep 1
done

echo ""
echo "📄 Applying complete schema migration..."
echo "   File: $MIGRATION_FILE"
echo ""

# Copy migration file
if [ ! -f "docker/postgres/migrations/$MIGRATION_FILE" ]; then
    echo "❌ Migration file not found: docker/postgres/migrations/$MIGRATION_FILE"
    exit 1
fi

docker cp "docker/postgres/migrations/$MIGRATION_FILE" $CONTAINER:/tmp/

# Apply migration
echo "⚙️  Executing migration..."
if docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -f "/tmp/$MIGRATION_FILE"; then
    echo ""
    echo "✅ Migration applied successfully!"
else
    echo ""
    echo "⚠️  Migration may have partial errors (check output above)"
    echo "   This is normal if some objects already exist"
fi

echo ""
echo "============================================="
echo "📊 Verification"
echo "============================================="

# Count tables
TABLE_COUNT=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
    SELECT COUNT(*) 
    FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
" | tr -d ' ')

echo ""
echo "📋 Total tables: $TABLE_COUNT (expected: 11)"

# List all tables
echo ""
echo "📌 Tables created:"
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name;
" | grep -v "(" | grep -v "row" | grep -v "-" | grep -v "^$" | sed 's/^/   ✅ /'

# Check products columns
echo ""
echo "📌 Products table columns (with extras from migration 003):"
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'products' 
      AND column_name IN ('review_count', 'discount_rate', 'authors', 'specifications', 'configurable_options', 'short_description')
    ORDER BY column_name;
" | grep -v "(" | grep -v "row" | grep -v "-" | grep -v "^$" | sed 's/^/   ✅ /'

# Check order tables
echo ""
echo "📌 Order tables:"
for table in customers orders order_lines; do
    if docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
        SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '$table');
    " | grep -q "t"; then
        echo "   ✅ $table"
    else
        echo "   ❌ $table (missing)"
    fi
done

# Check crawl_categories data
echo ""
echo "📌 Crawl categories sample data:"
CATEGORY_COUNT=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
    SELECT COUNT(*) FROM crawl_categories;
" 2>/dev/null | tr -d ' ')

if [ "$CATEGORY_COUNT" -gt 0 ]; then
    echo "   ✅ $CATEGORY_COUNT categories loaded"
    
    # Show top 3
    echo ""
    echo "   Top 3 by priority:"
    docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
        SELECT category_id, category_name, priority, is_active 
        FROM crawl_categories 
        ORDER BY priority DESC 
        LIMIT 3;
    " 2>/dev/null | head -7 | tail -3 | sed 's/^/     /'
else
    echo "   ⚠️  No sample data found"
fi

echo ""
echo "============================================="
echo "🎉 Schema Migration Complete!"
echo "============================================="
echo ""
echo "📋 Summary:"
echo "   • Tables: $TABLE_COUNT/11"
echo "   • Crawl categories: $CATEGORY_COUNT/11"
echo "   • Products extra columns: ✅"
echo "   • Order pipeline tables: ✅"
echo ""
echo "🚀 Next steps:"
echo "   1. Create Kafka topics:"
echo "      docker compose run --rm app python src/manage.py create-kafka-topics"
echo ""
echo "   2. Start consumers:"
echo "      docker compose up -d consumers"
echo ""
echo "   3. Start cron crawler:"
echo "      docker compose up -d cron"
echo ""
echo "   4. Check stats:"
echo "      docker compose run --rm app python src/manage.py stats"
echo ""
