#!/bin/bash
# Script kiểm tra cron crawler status

echo "🔍 Kiểm Tra Cron Crawler Status"
echo "================================"
echo ""

# 1. Thời gian hiện tại
echo "⏰ Thời gian hiện tại:"
date
echo ""

# 2. Cron schedule
echo "📅 Cron schedule (chạy mỗi 3 phút):"
docker exec uit-bd-cron crontab -l | grep crawl_from_categories
echo ""

# 3. Log mới nhất
echo "📝 Log crawler mới nhất (10 dòng cuối):"
docker exec uit-bd-cron tail -10 /app/logs/cron-crawler.log
echo ""

# 4. Categories status
echo "📊 Status crawl_categories:"
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -c "
  SELECT 
    category_id,
    category_name,
    crawl_status,
    priority,
    TO_CHAR(last_crawled_at, 'YYYY-MM-DD HH24:MI') as last_crawled
  FROM crawl_categories 
  WHERE is_active = true 
  ORDER BY priority DESC;
"
echo ""

# 5. Thống kê
echo "📈 Thống kê:"
docker exec uit-bd-postgres psql -U uit_user -d uit_analytics -tAc "
  SELECT 
    crawl_status,
    COUNT(*) as count
  FROM crawl_categories 
  WHERE is_active = true 
  GROUP BY crawl_status;
" | while IFS='|' read -r status count; do
  echo "  - $status: $count"
done
echo ""

echo "💡 Lệnh hữu ích:"
echo "  - Theo dõi log real-time: docker logs -f uit-bd-cron"
echo "  - Chạy thủ công: docker exec uit-bd-cron python /app/src/crawl_from_categories.py"
echo "  - Reset status: python src/manage_crawl_categories.py reset <category_id>"
