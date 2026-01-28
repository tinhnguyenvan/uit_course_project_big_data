"""
Product consumer - xử lý các sản phẩm từ Kafka và lưu vào PostgreSQL
"""
import logging
import json
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from confluent_kafka import Producer

from .base_consumer import BaseConsumer
from ..models import SessionLocal, Product, Shop, ProductPrice, Category
from ..config import config

logger = logging.getLogger(__name__)


class ProductConsumer(BaseConsumer):
    """Consumer xử lý các message sản phẩm"""
    
    def __init__(self):
        super().__init__(
            topics=[config.KAFKA_TOPIC_PRODUCTS],
            group_id='product-consumer-group',
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS
        )
        self.db = None
        self.detail_producer = None
        self._init_detail_producer()
    
    def _init_detail_producer(self):
        """Khởi tạo Kafka producer cho topic chi tiết sản phẩm"""
        try:
            producer_config = {
                'bootstrap.servers': config.KAFKA_BOOTSTRAP_SERVERS,
                'acks': 'all',
                'retries': 3
            }
            self.detail_producer = Producer(producer_config)
            logger.info("Product detail producer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize detail producer: {e}")
            self.detail_producer = None
    
    def process_product(self, data: dict) -> bool:
        """
        Xử lý message sản phẩm và lưu vào database
        
        Args:
            data: Dữ liệu sản phẩm từ Kafka
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        self.db = SessionLocal()
        
        try:
            # Lưu shop nếu có
            if data.get('shop_id'):
                self._upsert_shop(data)
            
            # Lưu category nếu có
            if data.get('category_id'):
                self._ensure_category(data.get('category_id'))
            
            # Lưu/cập nhật sản phẩm
            product = self.db.query(Product).filter_by(
                product_id=data['product_id']
            ).first()
            
            if product:
                # Cập nhật sản phẩm đã tồn tại
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
                # Tạo sản phẩm mới
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
            
            # Lưu lịch sử giá nếu có thông tin giá
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
            
            # Push tới topic chi tiết sản phẩm để crawl chi tiết
            self._push_to_detail_topic(data['product_id'], data.get('spid'))
            
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
        """Tạo hoặc cập nhật shop"""
        shop_id = data.get('shop_id')
        if not shop_id:
            return
        
        shop = self.db.query(Shop).filter_by(shop_id=shop_id).first()
        
        if not shop:
            # Tạo record shop tối thiểu
            # Thông tin đầy đủ về shop sẽ đến từ crawler riêng cho shop
            shop = Shop(
                shop_id=shop_id,
                shop_name=f"Shop {shop_id}",  # Placeholder
                is_official=False
            )
            self.db.add(shop)
            logger.debug(f"Created placeholder for shop {shop_id}")
    
    def _ensure_category(self, category_id: int):
        """Đảm bảo category tồn tại"""
        category = self.db.query(Category).filter_by(category_id=category_id).first()
        
        if not category:
            # Tạo placeholder category
            category = Category(
                category_id=category_id,
                category_name=f"Category {category_id}"
            )
            self.db.add(category)
            logger.debug(f"Created placeholder for category {category_id}")
    
    def _push_to_detail_topic(self, product_id: int, spid: int = None):
        """Push product_id tới topic chi tiết để crawl chi tiết"""
        if not self.detail_producer:
            logger.warning("Detail producer not available, skipping detail push")
            return
        
        try:
            message = {
                'product_id': product_id,
                'spid': spid or product_id  # Sử dụng product_id làm fallback nếu spid không có
            }
            
            # Serialize message sang JSON
            message_json = json.dumps(message).encode('utf-8')
            
            # Gửi message
            self.detail_producer.produce(
                config.KAFKA_TOPIC_PRODUCT_DETAIL,
                value=message_json,
                callback=self._delivery_callback
            )
            
            # Flush để đảm bảo message được gửi
            self.detail_producer.flush()
            logger.debug(f"Pushed product {product_id} to detail topic")
            
        except Exception as e:
            logger.error(f"Failed to push product {product_id} to detail topic: {e}")
    
    def _delivery_callback(self, err, msg):
        """Callback xác nhận gửi message"""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()}")
    
    def start(self):
        """Bắt đầu consumer các message sản phẩm"""
        logger.info("Starting product consumer...")
        self.consume(self.process_product)
    
    def close(self):
        """Đóng kết nối producer"""
        if self.detail_producer:
            self.detail_producer.flush()
        super().close()


# Standalone runner
if __name__ == '__main__':
    import sys
    
    # Thiết lập logging
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
