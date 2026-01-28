"""
Product Detail Consumer - lấy thông tin chi tiết sản phẩm từ Tiki API
"""
import logging
import requests
import json
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from confluent_kafka import Producer

from .base_consumer import BaseConsumer
from ..models import SessionLocal, Product, Shop, Category
from ..config import config

logger = logging.getLogger(__name__)


class ProductDetailConsumer(BaseConsumer):
    """Consumer xử lý message chi tiết sản phẩm - lấy thông tin đầy đủ từ Tiki API"""
    
    def __init__(self):
        super().__init__(
            topics=[config.KAFKA_TOPIC_PRODUCT_DETAIL],
            group_id='product-detail-consumer-group',
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS
        )
        self.db = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://tiki.vn/'
        })
        self.review_fetch_producer = None
        self._init_review_fetch_producer()
    
    def _init_review_fetch_producer(self):
        """Khởi tạo Kafka producer cho topic review fetch"""
        try:
            producer_config = {
                'bootstrap.servers': config.KAFKA_BOOTSTRAP_SERVERS,
                'acks': 'all',
                'retries': 3
            }
            self.review_fetch_producer = Producer(producer_config)
            logger.info("Review fetch producer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize review fetch producer: {e}")
            self.review_fetch_producer = None
    
    def process_detail(self, data: dict) -> bool:
        """
        Xử lý message chi tiết sản phẩm - lấy từ API và cập nhật database
        
        Args:
            data: Message chứa product_id và spid
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        product_id = data.get('product_id')
        spid = data.get('spid', product_id)
        
        if not product_id:
            logger.error("Missing product_id in message")
            return False
        
        try:
            # Lấy chi tiết sản phẩm từ Tiki API
            detail_data = self._fetch_product_detail(product_id, spid)
            
            if not detail_data:
                logger.warning(f"No detail data fetched for product {product_id}")
                return False
            
            # Cập nhật database với thông tin chi tiết
            success = self._update_product_detail(detail_data)
            
            # Nếu thành công, push tới topic review fetch
            if success:
                seller_id = detail_data.get('current_seller', {}).get('id')
                self._push_to_review_fetch(product_id, spid, seller_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing detail for product {product_id}: {e}")
            return False
    
    def _fetch_product_detail(self, product_id: int, spid: int) -> dict:
        """
        Lấy chi tiết sản phẩm từ Tiki API
        
        Args:
            product_id: ID sản phẩm
            spid: ID sản phẩm của seller
            
        Returns:
            Dữ liệu chi tiết sản phẩm hoặc None
        """
        url = f"https://tiki.vn/api/v2/products/{product_id}"
        params = {
            'platform': 'web',
            'spid': spid,
            'version': 3
        }
        
        try:
            logger.info(f"Fetching detail for product {product_id} (spid: {spid})")
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Successfully fetched detail for product {product_id}")
                return data
            else:
                logger.warning(f"Failed to fetch detail: HTTP {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Request error fetching product {product_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for product {product_id}: {e}")
            return None
    
    def _update_product_detail(self, detail_data: dict) -> bool:
        """
        Update product with detailed information
        
        Args:
            detail_data: Full product detail from API
            
        Returns:
            True if successful, False otherwise
        """
        self.db = SessionLocal()
        
        try:
            product_id = detail_data.get('id')
            
            if not product_id:
                logger.error("Missing product ID in detail data")
                return False
            
            # Find existing product
            product = self.db.query(Product).filter_by(product_id=product_id).first()
            
            if not product:
                logger.warning(f"Product {product_id} not found in database, creating new entry")
                product = Product(product_id=product_id)
                self.db.add(product)
            
            # Update basic fields
            if detail_data.get('name'):
                product.name = detail_data['name']
            
            if detail_data.get('short_url'):
                product.url = detail_data['short_url']
            elif detail_data.get('url_path'):
                product.url = f"https://tiki.vn/{detail_data['url_path']}"
            
            if detail_data.get('thumbnail_url'):
                product.image_url = detail_data['thumbnail_url']
            
            # Description - can be short or full
            if detail_data.get('description'):
                product.description = self._clean_html(detail_data['description'])
            elif detail_data.get('short_description'):
                product.description = detail_data['short_description']
            
            # Ratings and reviews
            if detail_data.get('rating_average'):
                product.rating = float(detail_data['rating_average'])
            
            # Sold count
            if detail_data.get('all_time_quantity_sold'):
                product.sold_count = detail_data['all_time_quantity_sold']
            elif detail_data.get('quantity_sold', {}).get('value'):
                product.sold_count = detail_data['quantity_sold']['value']
            
            # Category from breadcrumbs or categories
            if detail_data.get('categories', {}).get('id'):
                category_id = detail_data['categories']['id']
                self._ensure_category(category_id)
                product.category_id = category_id
            
            # Current seller
            if detail_data.get('current_seller', {}).get('id'):
                shop_id = detail_data['current_seller']['id']
                self._upsert_shop(shop_id, detail_data.get('current_seller', {}))
                product.shop_id = shop_id
            
            # Additional detail fields
            if detail_data.get('review_count'):
                product.review_count = detail_data['review_count']
            
            if detail_data.get('discount_rate'):
                product.discount_rate = detail_data['discount_rate']
            
            if detail_data.get('short_description'):
                product.short_description = detail_data['short_description']
            
            # Store authors as JSON
            if detail_data.get('authors'):
                product.authors = json.dumps(detail_data['authors'])
            
            # Store specifications as JSON
            if detail_data.get('specifications'):
                product.specifications = json.dumps(detail_data['specifications'])
            
            # Store configurable options (variants) as JSON
            if detail_data.get('configurable_options'):
                product.configurable_options = json.dumps(detail_data['configurable_options'])
            
            product.last_updated = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Successfully updated detail for product {product_id}: {product.name[:50]}")
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error updating product detail: {e}")
            self.db.rollback()
            return False
        
        except Exception as e:
            logger.error(f"Error updating product detail: {e}")
            self.db.rollback()
            return False
        
        finally:
            if self.db:
                self.db.close()
    
    def _ensure_category(self, category_id: int):
        """Ensure category exists in database"""
        if not category_id:
            return
        
        category = self.db.query(Category).filter_by(category_id=category_id).first()
        
        if not category:
            # Create placeholder category
            category = Category(
                category_id=category_id,
                category_name=f"Category {category_id}"
            )
            self.db.add(category)
            self.db.flush()  # Flush to make it available in same transaction
            logger.debug(f"Created placeholder for category {category_id}")
    
    def _upsert_shop(self, shop_id: int, shop_data: dict):
        """Create or update shop"""
        if not shop_id:
            return
        
        shop = self.db.query(Shop).filter_by(shop_id=shop_id).first()
        
        if not shop:
            # Create shop with available data
            shop = Shop(
                shop_id=shop_id,
                shop_name=shop_data.get('name', f"Shop {shop_id}"),
                is_official=False
            )
            self.db.add(shop)
            self.db.flush()  # Flush to make it available in same transaction
            logger.debug(f"Created shop {shop_id}: {shop.shop_name}")
        elif shop_data.get('name'):
            # Update shop name if provided
            shop.shop_name = shop_data['name']
            logger.debug(f"Updated shop {shop_id}: {shop.shop_name}")
    
    def _clean_html(self, html_text: str) -> str:
        """
        Remove HTML tags from description
        
        Args:
            html_text: HTML string
            
        Returns:
            Plain text
        """
        if not html_text:
            return ""
        
        # Simple HTML tag removal (you might want to use BeautifulSoup for better cleaning)
        import re
        clean_text = re.sub(r'<[^>]+>', '', html_text)
        clean_text = re.sub(r'\s+', ' ', clean_text)
        return clean_text.strip()
    
    def _push_to_review_fetch(self, product_id: int, spid: int, seller_id: int = None):
        """Push product info to review fetch topic"""
        if not self.review_fetch_producer:
            logger.warning("Review fetch producer not available, skipping review fetch push")
            return
        
        try:
            message = {
                'product_id': product_id,
                'spid': spid,
                'seller_id': seller_id or 1  # Default to seller_id 1 if not available
            }
            
            # Serialize message to JSON
            message_json = json.dumps(message).encode('utf-8')
            
            # Send message
            self.review_fetch_producer.produce(
                config.KAFKA_TOPIC_REVIEW_FETCH,
                value=message_json,
                callback=self._delivery_callback
            )
            
            # Flush to ensure message is sent
            self.review_fetch_producer.flush()
            logger.debug(f"Pushed product {product_id} to review fetch topic")
            
        except Exception as e:
            logger.error(f"Failed to push product {product_id} to review fetch topic: {e}")
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery confirmation"""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()}")
    
    def start(self):
        """Start consuming product detail messages"""
        logger.info("Starting product detail consumer...")
        self.consume(self.process_detail)
    
    def close(self):
        """Close connections"""
        if self.session:
            self.session.close()
        if self.review_fetch_producer:
            self.review_fetch_producer.flush()
        super().close()


# Standalone runner
if __name__ == '__main__':
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        consumer = ProductDetailConsumer()
        consumer.start()
    except KeyboardInterrupt:
        logger.info("Consumer stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        sys.exit(1)
