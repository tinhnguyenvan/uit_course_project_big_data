"""
Script quản lý crawl categories
"""
import sys
import os
from datetime import datetime

# Thêm src vào path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models import SessionLocal, CrawlCategory


def list_categories(status=None, active_only=False):
    """Liệt kê các categories"""
    db = SessionLocal()
    
    try:
        query = db.query(CrawlCategory)
        
        if status:
            query = query.filter_by(crawl_status=status)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        categories = query.order_by(CrawlCategory.priority.desc()).all()
        
        print(f"\n📋 Danh sách Categories (Tổng: {len(categories)})")
        print("=" * 120)
        print(f"{'ID':<8} {'Tên':<40} {'Status':<12} {'Active':<8} {'Priority':<10} {'Pages':<8} {'Products':<10}")
        print("=" * 120)
        
        for cat in categories:
            active_icon = "✓" if cat.is_active else "✗"
            print(f"{cat.category_id:<8} {cat.category_name[:38]:<40} {cat.crawl_status:<12} "
                  f"{active_icon:<8} {cat.priority:<10} {cat.max_pages:<8} {cat.total_products_crawled:<10}")
        
        print("=" * 120)
        
    finally:
        db.close()


def add_category(category_id: int, name: str, url: str, parent_id=None, 
                priority=0, max_pages=10, notes=''):
    """Thêm category mới"""
    db = SessionLocal()
    
    try:
        # Kiểm tra đã tồn tại chưa
        existing = db.query(CrawlCategory).filter_by(category_id=category_id).first()
        
        if existing:
            print(f"❌ Category {category_id} đã tồn tại!")
            return False
        
        category = CrawlCategory(
            category_id=category_id,
            category_name=name,
            category_url=url,
            parent_category_id=parent_id,
            priority=priority,
            max_pages=max_pages,
            notes=notes,
            is_active=True,
            crawl_status='pending'
        )
        
        db.add(category)
        db.commit()
        
        print(f"✅ Đã thêm category: {name} (ID: {category_id})")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi thêm category: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def update_category(category_id: int, **kwargs):
    """Cập nhật thông tin category"""
    db = SessionLocal()
    
    try:
        category = db.query(CrawlCategory).filter_by(category_id=category_id).first()
        
        if not category:
            print(f"❌ Không tìm thấy category {category_id}")
            return False
        
        # Cập nhật các trường được cung cấp
        for key, value in kwargs.items():
            if hasattr(category, key):
                setattr(category, key, value)
        
        db.commit()
        
        print(f"✅ Đã cập nhật category {category_id}")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi cập nhật: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def activate_category(category_id: int):
    """Kích hoạt category để crawl"""
    return update_category(category_id, is_active=True)


def deactivate_category(category_id: int):
    """Vô hiệu hóa category"""
    return update_category(category_id, is_active=False)


def reset_category(category_id: int):
    """Reset trạng thái crawl của category"""
    return update_category(
        category_id, 
        crawl_status='pending',
        last_crawled_page=0,
        total_products_crawled=0,
        last_crawled_at=None
    )


def get_next_category():
    """Lấy category tiếp theo cần crawl (theo priority)"""
    db = SessionLocal()
    
    try:
        category = db.query(CrawlCategory).filter_by(
            is_active=True,
            crawl_status='pending'
        ).order_by(CrawlCategory.priority.desc()).first()
        
        if category:
            print(f"\n🎯 Category tiếp theo: {category.category_name} (ID: {category.category_id})")
            print(f"   Priority: {category.priority}, Max pages: {category.max_pages}")
            print(f"   URL: {category.category_url}")
            return category.category_id
        else:
            print("✓ Không còn category nào cần crawl")
            return None
            
    finally:
        db.close()


def show_stats():
    """Hiển thị thống kê"""
    db = SessionLocal()
    
    try:
        total = db.query(CrawlCategory).count()
        active = db.query(CrawlCategory).filter_by(is_active=True).count()
        pending = db.query(CrawlCategory).filter_by(crawl_status='pending').count()
        in_progress = db.query(CrawlCategory).filter_by(crawl_status='in_progress').count()
        completed = db.query(CrawlCategory).filter_by(crawl_status='completed').count()
        failed = db.query(CrawlCategory).filter_by(crawl_status='failed').count()
        
        total_products = db.query(
            db.func.sum(CrawlCategory.total_products_crawled)
        ).scalar() or 0
        
        print("\n📊 Thống kê Crawl Categories")
        print("=" * 60)
        print(f"Tổng categories:        {total}")
        print(f"Active:                 {active}")
        print(f"Pending:                {pending}")
        print(f"In Progress:            {in_progress}")
        print(f"Completed:              {completed}")
        print(f"Failed:                 {failed}")
        print(f"Tổng sản phẩm crawled:  {total_products}")
        print("=" * 60)
        
    finally:
        db.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Quản lý Crawl Categories')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List
    list_parser = subparsers.add_parser('list', help='Liệt kê categories')
    list_parser.add_argument('--status', help='Lọc theo status')
    list_parser.add_argument('--active', action='store_true', help='Chỉ hiện active')
    
    # Add
    add_parser = subparsers.add_parser('add', help='Thêm category mới')
    add_parser.add_argument('category_id', type=int, help='Category ID')
    add_parser.add_argument('name', help='Tên category')
    add_parser.add_argument('url', help='URL category')
    add_parser.add_argument('--parent', type=int, help='Parent category ID')
    add_parser.add_argument('--priority', type=int, default=0, help='Priority')
    add_parser.add_argument('--max-pages', type=int, default=10, help='Max pages')
    add_parser.add_argument('--notes', default='', help='Ghi chú')
    
    # Update
    update_parser = subparsers.add_parser('update', help='Cập nhật category')
    update_parser.add_argument('category_id', type=int, help='Category ID')
    update_parser.add_argument('--priority', type=int, help='Priority mới')
    update_parser.add_argument('--max-pages', type=int, help='Max pages mới')
    update_parser.add_argument('--status', help='Status mới')
    
    # Activate/Deactivate
    activate_parser = subparsers.add_parser('activate', help='Kích hoạt category')
    activate_parser.add_argument('category_id', type=int, help='Category ID')
    
    deactivate_parser = subparsers.add_parser('deactivate', help='Vô hiệu hóa category')
    deactivate_parser.add_argument('category_id', type=int, help='Category ID')
    
    # Reset
    reset_parser = subparsers.add_parser('reset', help='Reset trạng thái category')
    reset_parser.add_argument('category_id', type=int, help='Category ID')
    
    # Next
    subparsers.add_parser('next', help='Lấy category tiếp theo cần crawl')
    
    # Stats
    subparsers.add_parser('stats', help='Hiển thị thống kê')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_categories(status=args.status, active_only=args.active)
    elif args.command == 'add':
        add_category(
            args.category_id, args.name, args.url,
            parent_id=args.parent, priority=args.priority,
            max_pages=args.max_pages, notes=args.notes
        )
    elif args.command == 'update':
        kwargs = {}
        if args.priority is not None:
            kwargs['priority'] = args.priority
        if args.max_pages is not None:
            kwargs['max_pages'] = args.max_pages
        if args.status:
            kwargs['crawl_status'] = args.status
        update_category(args.category_id, **kwargs)
    elif args.command == 'activate':
        activate_category(args.category_id)
    elif args.command == 'deactivate':
        deactivate_category(args.category_id)
    elif args.command == 'reset':
        reset_category(args.category_id)
    elif args.command == 'next':
        get_next_category()
    elif args.command == 'stats':
        show_stats()
    else:
        parser.print_help()
