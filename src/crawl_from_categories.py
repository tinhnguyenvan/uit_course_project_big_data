#!/usr/bin/env python3
"""
Script crawl tự động từ bảng crawl_categories
Sử dụng cho cron job
"""
import sys
import os
from datetime import datetime

# Thêm src vào path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models import SessionLocal, CrawlCategory
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def get_next_category_to_crawl(db):
    """Lấy category tiếp theo cần crawl theo priority"""
    # Tìm category đang active, chưa crawl hoặc failed
    category = db.query(CrawlCategory).filter(
        CrawlCategory.is_active == True,
        CrawlCategory.crawl_status.in_(['pending', 'failed'])
    ).order_by(CrawlCategory.priority.desc()).first()
    
    # Nếu không còn, lấy những cái đã completed để crawl lại
    if not category:
        category = db.query(CrawlCategory).filter(
            CrawlCategory.is_active == True,
            CrawlCategory.crawl_status == 'completed'
        ).order_by(
            CrawlCategory.last_crawled_at.asc().nullsfirst(),
            CrawlCategory.priority.desc()
        ).first()
    
    return category


def crawl_category(category_id, max_pages=10, resume=True):
    """Crawl một category sử dụng Scrapy"""
    print(f"🕷️  Bắt đầu crawl category {category_id}")
    print(f"   Max pages: {max_pages}")
    print(f"   Resume: {resume}")
    
    from app.crawlers.spiders.tiki_listing import TikiListingSpider
    
    # Lấy Scrapy settings
    settings = get_project_settings()
    settings.setmodule('app.crawlers.settings')
    
    # Tắt log quá chi tiết cho cron
    settings.set('LOG_LEVEL', 'INFO')
    
    process = CrawlerProcess(settings)
    
    kwargs = {
        'category_id': str(category_id),
        'resume': resume
    }
    
    if max_pages:
        kwargs['max_pages'] = str(max_pages)
    
    process.crawl(TikiListingSpider, **kwargs)
    process.start()
    
    print(f"✓ Hoàn thành crawl category {category_id}")


def update_crawl_status(db, category_id, status, error_msg=None):
    """Cập nhật trạng thái crawl"""
    category = db.query(CrawlCategory).filter_by(category_id=category_id).first()
    
    if category:
        category.crawl_status = status
        category.last_crawled_at = datetime.now()
        
        if error_msg:
            category.notes = f"Error: {error_msg}"
        
        db.commit()


def main():
    """Main function chạy từ cron"""
    print("=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] BẮT ĐẦU CRON CRAWL")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        # Lấy category tiếp theo
        category = get_next_category_to_crawl(db)
        
        if not category:
            print("ℹ️  Không có category nào cần crawl")
            return
        
        print(f"📋 Category được chọn:")
        print(f"   ID: {category.category_id}")
        print(f"   Tên: {category.category_name}")
        print(f"   Priority: {category.priority}")
        print(f"   Max pages: {category.max_pages}")
        print(f"   Status hiện tại: {category.crawl_status}")
        print()
        
        # Cập nhật trạng thái sang in_progress
        category.crawl_status = 'in_progress'
        db.commit()
        
        # Crawl category
        try:
            crawl_category(
                category_id=category.category_id,
                max_pages=category.max_pages,
                resume=True
            )
            
            # Cập nhật trạng thái thành công
            update_crawl_status(db, category.category_id, 'completed')
            print(f"✅ Crawl thành công category {category.category_id}")
            
        except Exception as e:
            print(f"❌ Lỗi khi crawl: {str(e)}")
            update_crawl_status(db, category.category_id, 'failed', str(e))
            raise
    
    except Exception as e:
        print(f"❌ LỖI: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
        print("=" * 80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] KẾT THÚC CRON CRAWL")
        print("=" * 80)
        print()


if __name__ == '__main__':
    main()
