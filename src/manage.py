#!/usr/bin/env python
"""
CLI tool for managing the Scrapy crawlers and data pipeline
"""
import click
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils import setup_logger, check_kafka_connection, check_db_connection, init_database, get_table_counts, create_topics
from app.config import config

logger = setup_logger('cli', console=True)


@click.group()
def cli():
    """UIT Big Data Project - Management CLI"""
    pass


@cli.command()
def check():
    """Check system connections (Kafka, PostgreSQL)"""
    click.echo("🔍 Checking system connections...")
    
    # Check PostgreSQL
    click.echo("\n📊 PostgreSQL:")
    if check_db_connection():
        click.secho("✓ Database connection successful", fg='green')
        
        # Show table counts
        counts = get_table_counts()
        if counts:
            click.echo("\nTable statistics:")
            for table, count in counts.items():
                click.echo(f"  - {table}: {count:,} rows")
    else:
        click.secho("✗ Database connection failed", fg='red')
    
    # Check Kafka
    click.echo("\n📨 Kafka:")
    if check_kafka_connection():
        click.secho("✓ Kafka connection successful", fg='green')
    else:
        click.secho("✗ Kafka connection failed", fg='red')


@cli.command()
@click.option('--reset', is_flag=True, help='Drop existing tables before creating')
def init_db(reset):
    """Initialize database tables"""
    if reset:
        click.confirm('⚠️  This will drop all existing tables. Continue?', abort=True)
        from app.utils.db_utils import reset_database
        if reset_database():
            click.secho("✓ Database reset successful", fg='green')
        else:
            click.secho("✗ Database reset failed", fg='red')
    else:
        if init_database():
            click.secho("✓ Database initialized successfully", fg='green')
        else:
            click.secho("✗ Database initialization failed", fg='red')


@cli.command()
def create_kafka_topics():
    """Create Kafka topics"""
    click.echo("Creating Kafka topics...")
    
    topics = {
        config.KAFKA_TOPIC_PRODUCTS: 3,
        config.KAFKA_TOPIC_REVIEWS: 3,
        config.KAFKA_TOPIC_PRICES: 3,
        config.KAFKA_TOPIC_SHOPS: 1,
    }
    
    try:
        create_topics(topics)
        click.secho("✓ Topics created successfully", fg='green')
    except Exception as e:
        click.secho(f"✗ Failed to create topics: {e}", fg='red')


@cli.command()
@click.option('--category-id', default=1789, help='Tiki category ID to crawl')
@click.option('--max-pages', default=10, help='Maximum pages to crawl')
def crawl_products(category_id, max_pages):
    """Crawl Tiki products"""
    click.echo(f"🕷️  Starting product crawler (category: {category_id}, max_pages: {max_pages})...")
    
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    from app.crawlers.spiders.tiki_products import TikiProductSpider
    
    # Get Scrapy settings
    settings = get_project_settings()
    settings.setmodule('app.crawlers.settings')
    
    process = CrawlerProcess(settings)
    process.crawl(
        TikiProductSpider,
        category_id=category_id,
        max_pages=max_pages
    )
    
    try:
        process.start()
        click.secho("✓ Crawler finished", fg='green')
    except Exception as e:
        click.secho(f"✗ Crawler failed: {e}", fg='red')


@cli.command()
@click.option('--product-ids', required=True, help='Product IDs to crawl (comma-separated)')
@click.option('--max-pages', default=5, help='Maximum pages per product')
def crawl_reviews(product_ids, max_pages):
    """Crawl Tiki reviews"""
    click.echo(f"🕷️  Starting review crawler (products: {product_ids}, max_pages: {max_pages})...")
    
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    from app.crawlers.spiders.tiki_reviews import TikiReviewSpider
    
    # Get Scrapy settings
    settings = get_project_settings()
    settings.setmodule('app.crawlers.settings')
    
    process = CrawlerProcess(settings)
    process.crawl(
        TikiReviewSpider,
        product_ids=product_ids,
        max_pages=max_pages
    )
    
    try:
        process.start()
        click.secho("✓ Crawler finished", fg='green')
    except Exception as e:
        click.secho(f"✗ Crawler failed: {e}", fg='red')


@cli.command()
@click.option('--category-id', default=870, help='Tiki category ID')
@click.option('--max-pages', default=None, help='Maximum pages to crawl (unlimited if not set)')
@click.option('--resume/--no-resume', default=True, help='Resume from last crawled page')
def crawl_listing(category_id, max_pages, resume):
    """Crawl Tiki listing API (with resume capability)"""
    click.echo(f"🕷️  Starting listing crawler...")
    click.echo(f"   Category: {category_id}")
    click.echo(f"   Max pages: {max_pages if max_pages else 'unlimited'}")
    click.echo(f"   Resume: {resume}")
    
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    from app.crawlers.spiders.tiki_listing import TikiListingSpider
    
    # Get Scrapy settings
    settings = get_project_settings()
    settings.setmodule('app.crawlers.settings')
    
    process = CrawlerProcess(settings)
    
    kwargs = {
        'category_id': category_id,
        'resume': resume
    }
    if max_pages:
        kwargs['max_pages'] = max_pages
    
    process.crawl(TikiListingSpider, **kwargs)
    
    try:
        process.start()
        click.secho("✓ Crawler finished", fg='green')
    except Exception as e:
        click.secho(f"✗ Crawler failed: {e}", fg='red')


@cli.command()
@click.option('--consumer', type=click.Choice(['products', 'reviews', 'all']), default='all')
def start_consumers(consumer):
    """Start Kafka consumers"""
    click.echo(f"Starting {consumer} consumer(s)...")
    
    if consumer == 'products':
        from app.consumers.product_consumer import ProductConsumer
        ProductConsumer().start()
    elif consumer == 'reviews':
        from app.consumers.review_consumer import ReviewConsumer
        ReviewConsumer().start()
    else:
        from app.consumers.run_all import main
        main()


@cli.command()
@click.option('--limit', default=None, help='Limit số categories cần crawl')
@click.option('--status', default=None, help='Chỉ crawl categories với status này')
def crawl_from_db(limit, status):
    """Crawl tự động từ bảng crawl_categories"""
    from app.models import SessionLocal, CrawlCategory
    from datetime import datetime
    
    click.echo("🕷️  Crawl từ database crawl_categories...")
    
    db = SessionLocal()
    
    try:
        # Query categories cần crawl
        query = db.query(CrawlCategory).filter_by(is_active=True)
        
        if status:
            query = query.filter_by(crawl_status=status)
        else:
            # Mặc định lấy pending hoặc failed
            query = query.filter(CrawlCategory.crawl_status.in_(['pending', 'failed']))
        
        query = query.order_by(CrawlCategory.priority.desc())
        
        if limit:
            query = query.limit(limit)
        
        categories = query.all()
        
        if not categories:
            click.secho("ℹ️  Không có category nào cần crawl", fg='yellow')
            return
        
        click.echo(f"\n📋 Tìm thấy {len(categories)} categories cần crawl:\n")
        
        for cat in categories:
            click.echo(f"  • {cat.category_name} (ID: {cat.category_id}, Priority: {cat.priority})")
        
        click.echo()
        
        # Crawl từng category
        for idx, cat in enumerate(categories, 1):
            click.echo(f"\n[{idx}/{len(categories)}] Crawl: {cat.category_name}")
            click.echo(f"  Category ID: {cat.category_id}")
            click.echo(f"  Max pages: {cat.max_pages}")
            
            # Cập nhật status
            cat.crawl_status = 'in_progress'
            db.commit()
            
            try:
                # Import và chạy crawler
                from scrapy.crawler import CrawlerProcess
                from scrapy.utils.project import get_project_settings
                from app.crawlers.spiders.tiki_listing import TikiListingSpider
                
                settings = get_project_settings()
                settings.setmodule('app.crawlers.settings')
                
                process = CrawlerProcess(settings)
                
                kwargs = {
                    'category_id': str(cat.category_id),
                    'resume': True
                }
                
                if cat.max_pages:
                    kwargs['max_pages'] = str(cat.max_pages)
                
                process.crawl(TikiListingSpider, **kwargs)
                process.start()
                
                # Cập nhật thành công
                cat.crawl_status = 'completed'
                cat.last_crawled_at = datetime.now()
                db.commit()
                
                click.secho(f"  ✓ Hoàn thành", fg='green')
                
            except Exception as e:
                click.secho(f"  ✗ Lỗi: {str(e)}", fg='red')
                cat.crawl_status = 'failed'
                cat.notes = f"Error: {str(e)}"
                db.commit()
        
        click.echo("\n" + "=" * 50)
        click.secho("✓ Hoàn thành crawl từ database", fg='green')
        
    finally:
        db.close()


@cli.command()
def stats():
    """Show database statistics"""
    click.echo("📊 Database Statistics\n")
    
    counts = get_table_counts()
    
    if counts:
        click.echo(f"{'Table':<20} {'Count':>15}")
        click.echo("-" * 35)
        for table, count in counts.items():
            click.echo(f"{table:<20} {count:>15,}")
        
        total = sum(counts.values())
        click.echo("-" * 35)
        click.echo(f"{'TOTAL':<20} {total:>15,}")
    else:
        click.secho("No data available", fg='yellow')


if __name__ == '__main__':
    cli()

