"""
Configuration settings for the application
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)


class Config:
    """Application configuration"""
    
    # Project paths
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / 'data'
    LOGS_DIR = BASE_DIR / 'logs'
    
    # Database settings
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'uit_analytics')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'uit_user')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'uit_password')
    
    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    KAFKA_TOPIC_PRODUCTS = os.getenv('KAFKA_TOPIC_PRODUCTS', 'uit-products')
    KAFKA_TOPIC_REVIEWS = os.getenv('KAFKA_TOPIC_REVIEWS', 'uit-reviews')
    KAFKA_TOPIC_PRICES = os.getenv('KAFKA_TOPIC_PRICES', 'uit-prices')
    KAFKA_TOPIC_SHOPS = os.getenv('KAFKA_TOPIC_SHOPS', 'uit-shops')
    
    # Scrapy settings
    SCRAPY_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    SCRAPY_CONCURRENT_REQUESTS = int(os.getenv('SCRAPY_CONCURRENT_REQUESTS', '16'))
    SCRAPY_DOWNLOAD_DELAY = float(os.getenv('SCRAPY_DOWNLOAD_DELAY', '1'))
    SCRAPY_RANDOMIZE_DELAY = True
    
    # Tiki settings
    TIKI_BASE_URL = 'https://tiki.vn'
    TIKI_API_URL = 'https://tiki.vn/api/v2'
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'


config = Config()
