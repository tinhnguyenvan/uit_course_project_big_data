"""
Database utilities
"""
import logging
from sqlalchemy.exc import SQLAlchemyError
from ..models.database import SessionLocal, engine, Base, check_connection

logger = logging.getLogger(__name__)


def check_db_connection() -> bool:
    """
    Check database connection
    
    Returns:
        True if connection successful
    """
    return check_connection()


def init_database():
    """
    Initialize database - create all tables
    """
    try:
        logger.info("Initializing database...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def drop_all_tables():
    """
    Drop all tables (use with caution!)
    """
    try:
        logger.warning("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Failed to drop tables: {e}")
        return False


def reset_database():
    """
    Reset database - drop and recreate all tables
    """
    if drop_all_tables():
        return init_database()
    return False


def get_table_counts() -> dict:
    """
    Get row counts for all tables
    
    Returns:
        Dict of table names to row counts
    """
    db = SessionLocal()
    counts = {}
    
    try:
        from ..models import Product, Review, Shop, Category, ProductPrice, ReviewSentiment, CrawlLog
        
        counts['products'] = db.query(Product).count()
        counts['reviews'] = db.query(Review).count()
        counts['shops'] = db.query(Shop).count()
        counts['categories'] = db.query(Category).count()
        counts['product_prices'] = db.query(ProductPrice).count()
        counts['review_sentiment'] = db.query(ReviewSentiment).count()
        counts['crawl_logs'] = db.query(CrawlLog).count()
        
        return counts
        
    except Exception as e:
        logger.error(f"Error getting table counts: {e}")
        return {}
    finally:
        db.close()
