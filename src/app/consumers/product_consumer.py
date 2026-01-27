"""
Product consumer - processes products from Kafka and saves to PostgreSQL
"""
import logging
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from .base_consumer import BaseConsumer
from ..models import SessionLocal, Product, Shop, ProductPrice, Category
from ..config import config

logger = logging.getLogger(__name__)


class ProductConsumer(BaseConsumer):
    """Consumer for product messages"""
    
    def __init__(self):
        super().__init__(
            topics=[config.KAFKA_TOPIC_PRODUCTS],
            group_id='product-consumer-group',
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS
        )
        self.db = None
    
    def process_product(self, data: dict) -> bool:
        """
        Process product message and save to database
        
        Args:
            data: Product data from Kafka
            
        Returns:
            True if successful, False otherwise
        """
        self.db = SessionLocal()
        
        try:
            # Save shop if present
            if data.get('shop_id'):
                self._upsert_shop(data)
            
            # Save category if present
            if data.get('category_id'):
                self._ensure_category(data.get('category_id'))
            
            # Save/update product
            product = self.db.query(Product).filter_by(
                product_id=data['product_id']
            ).first()
            
            if product:
                # Update existing product
                product.name = data.get('name', product.name)
                product.url = data.get('url', product.url)
                product.image_url = data.get('image_url', product.image_url)
                product.description = data.get('description', product.description)
                product.rating = data.get('rating', product.rating)
                product.sold_count = data.get('sold_count', product.sold_count)
                product.shop_id = data.get('shop_id', product.shop_id)
                product.category_id = data.get('category_id', product.category_id)
                product.last_updated = datetime.utcnow()
                
                logger.debug(f"Updated product {data['product_id']}")
            else:
                # Create new product
                product = Product(
                    product_id=data['product_id'],
                    name=data['name'],
                    shop_id=data.get('shop_id'),
                    category_id=data.get('category_id'),
                    url=data['url'],
                    image_url=data.get('image_url'),
                    description=data.get('description'),
                    rating=data.get('rating'),
                    sold_count=data.get('sold_count', 0)
                )
                self.db.add(product)
                logger.debug(f"Created new product {data['product_id']}")
            
            # Save price history if price info is available
            if data.get('price'):
                price = ProductPrice(
                    product_id=data['product_id'],
                    price=data['price'],
                    original_price=data.get('original_price'),
                    discount_percent=data.get('discount_percent'),
                    stock_available=data.get('stock_available'),
                    timestamp=datetime.utcnow()
                )
                self.db.add(price)
                logger.debug(f"Added price record for product {data['product_id']}")
            
            self.db.commit()
            logger.info(f"Successfully saved product {data['product_id']}: {data.get('name', '')[:50]}")
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error processing product: {e}")
            self.db.rollback()
            return False
        
        except Exception as e:
            logger.error(f"Error processing product: {e}")
            self.db.rollback()
            return False
        
        finally:
            if self.db:
                self.db.close()
    
    def _upsert_shop(self, data: dict):
        """Create or update shop"""
        shop_id = data.get('shop_id')
        if not shop_id:
            return
        
        shop = self.db.query(Shop).filter_by(shop_id=shop_id).first()
        
        if not shop:
            # Create minimal shop record
            # Full shop details would come from shop-specific crawler
            shop = Shop(
                shop_id=shop_id,
                shop_name=f"Shop {shop_id}",  # Placeholder
                is_official=False
            )
            self.db.add(shop)
            logger.debug(f"Created placeholder for shop {shop_id}")
    
    def _ensure_category(self, category_id: int):
        """Ensure category exists"""
        category = self.db.query(Category).filter_by(category_id=category_id).first()
        
        if not category:
            # Create placeholder category
            category = Category(
                category_id=category_id,
                category_name=f"Category {category_id}"
            )
            self.db.add(category)
            logger.debug(f"Created placeholder for category {category_id}")
    
    def start(self):
        """Start consuming product messages"""
        logger.info("Starting product consumer...")
        self.consume(self.process_product)


# Standalone runner
if __name__ == '__main__':
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        consumer = ProductConsumer()
        consumer.start()
    except KeyboardInterrupt:
        logger.info("Consumer stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        sys.exit(1)
