"""
Item processing pipelines
"""
from datetime import datetime
import json
import logging
from confluent_kafka import Producer
from sqlalchemy.exc import SQLAlchemyError

from ..models import SessionLocal, Product, Shop, Review, ProductPrice
from ..schemas import ProductInKafka, ReviewInKafka
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """Validate items using Pydantic schemas"""
    
    def process_item(self, item, spider):
        try:
            item_type = item.get('item_type')
            
            # Add timestamp
            item['crawled_at'] = datetime.utcnow().isoformat()
            
            # Validate based on type
            if item_type == 'product':
                ProductInKafka(**dict(item))
            elif item_type == 'review':
                ReviewInKafka(**dict(item))
            
            logger.debug(f"Item validated: {item_type}")
            return item
            
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            raise


class KafkaProducerPipeline:
    """Send items to Kafka topics"""
    
    def __init__(self, bootstrap_servers, topic_products, topic_reviews, topic_shops):
        self.bootstrap_servers = bootstrap_servers
        self.topic_products = topic_products
        self.topic_reviews = topic_reviews
        self.topic_shops = topic_shops
        self.producer = None
        self.messages_sent = 0
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            bootstrap_servers=crawler.settings.get('KAFKA_BOOTSTRAP_SERVERS'),
            topic_products=crawler.settings.get('KAFKA_TOPIC_PRODUCTS'),
            topic_reviews=crawler.settings.get('KAFKA_TOPIC_REVIEWS'),
            topic_shops=crawler.settings.get('KAFKA_TOPIC_SHOPS')
        )
    
    def open_spider(self, spider):
        """Initialize Kafka producer"""
        try:
            self.producer = Producer({
                'bootstrap.servers': ','.join(self.bootstrap_servers),
                'client.id': f'scrapy-{spider.name}',
                'acks': 'all',
                'retries': 3,
            })
            logger.info("Kafka producer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def close_spider(self, spider):
        """Flush and close producer"""
        if self.producer:
            self.producer.flush()
            logger.info(f"Kafka producer closed. Messages sent: {self.messages_sent}")
    
    def delivery_callback(self, err, msg):
        """Callback when message is delivered"""
        if err:
            logger.error(f'Message delivery failed: {err}')
        else:
            logger.debug(f'Message delivered to {msg.topic()} [{msg.partition()}]')
    
    def process_item(self, item, spider):
        """Send item to appropriate Kafka topic"""
        if not self.producer:
            logger.warning("Kafka producer not available, skipping")
            return item
        
        try:
            item_type = item.get('item_type')
            
            # Determine topic
            if item_type == 'product':
                topic = self.topic_products
                key = str(item.get('product_id'))
            elif item_type == 'review':
                topic = self.topic_reviews
                key = str(item.get('product_id'))
            elif item_type == 'shop':
                topic = self.topic_shops
                key = str(item.get('shop_id'))
            else:
                logger.warning(f"Unknown item type: {item_type}")
                return item
            
            # Add Kafka timestamp
            item['kafka_timestamp'] = datetime.utcnow().isoformat()
            
            # Serialize and send
            value = json.dumps(dict(item), ensure_ascii=False, default=str).encode('utf-8')
            
            self.producer.produce(
                topic=topic,
                value=value,
                key=key.encode('utf-8') if key else None,
                callback=self.delivery_callback
            )
            
            self.producer.poll(0)
            self.messages_sent += 1
            
            logger.info(f"Sent {item_type} to Kafka: {key}")
            
        except Exception as e:
            logger.error(f"Failed to send to Kafka: {e}")
        
        return item


class DatabasePipeline:
    """Fallback pipeline to save items directly to database"""
    
    def __init__(self):
        self.session = None
        self.items_saved = 0
    
    def open_spider(self, spider):
        """Open database session"""
        self.session = SessionLocal()
        logger.info("Database pipeline opened")
    
    def close_spider(self, spider):
        """Close database session"""
        if self.session:
            self.session.close()
            logger.info(f"Database pipeline closed. Items saved: {self.items_saved}")
    
    def process_item(self, item, spider):
        """Save item to database (only if Kafka fails)"""
        # This pipeline is a fallback - normally items go through Kafka consumers
        # You can enable/disable this in settings.py
        
        try:
            item_type = item.get('item_type')
            
            if item_type == 'product':
                self._save_product(dict(item))
            elif item_type == 'review':
                self._save_review(dict(item))
            elif item_type == 'shop':
                self._save_shop(dict(item))
            
            self.items_saved += 1
            
        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            self.session.rollback()
        
        return item
    
    def _save_product(self, data):
        """Save product to database"""
        product = self.session.query(Product).filter_by(
            product_id=data['product_id']
        ).first()
        
        if product:
            # Update existing
            for key, value in data.items():
                if hasattr(product, key) and key not in ['product_id', 'first_seen']:
                    setattr(product, key, value)
        else:
            # Create new
            product = Product(**{
                k: v for k, v in data.items() 
                if k in Product.__table__.columns.keys()
            })
            self.session.add(product)
        
        # Save price if available
        if 'price' in data and data['price']:
            price = ProductPrice(
                product_id=data['product_id'],
                price=data['price'],
                original_price=data.get('original_price'),
                discount_percent=data.get('discount_percent'),
                stock_available=data.get('stock_available')
            )
            self.session.add(price)
        
        self.session.commit()
        logger.debug(f"Saved product: {data['product_id']}")
    
    def _save_review(self, data):
        """Save review to database"""
        review = Review(**{
            k: v for k, v in data.items() 
            if k in Review.__table__.columns.keys()
        })
        self.session.add(review)
        self.session.commit()
        logger.debug(f"Saved review for product: {data['product_id']}")
    
    def _save_shop(self, data):
        """Save shop to database"""
        shop = self.session.query(Shop).filter_by(
            shop_id=data['shop_id']
        ).first()
        
        if shop:
            # Update existing
            for key, value in data.items():
                if hasattr(shop, key) and key not in ['shop_id', 'created_at']:
                    setattr(shop, key, value)
        else:
            # Create new
            shop = Shop(**{
                k: v for k, v in data.items() 
                if k in Shop.__table__.columns.keys()
            })
            self.session.add(shop)
        
        self.session.commit()
        logger.debug(f"Saved shop: {data['shop_id']}")
