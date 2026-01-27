"""
Product Detail Consumer - fetches detailed product information from Tiki API
"""
import logging
import requests
import json
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from .base_consumer import BaseConsumer
from ..models import SessionLocal, Product
from ..config import config

logger = logging.getLogger(__name__)


class ProductDetailConsumer(BaseConsumer):
    """Consumer for product detail messages - fetches full product info from Tiki API"""
    
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
    
    def process_detail(self, data: dict) -> bool:
        """
        Process product detail message - fetch from API and update database
        
        Args:
            data: Message containing product_id and spid
            
        Returns:
            True if successful, False otherwise
        """
        product_id = data.get('product_id')
        spid = data.get('spid', product_id)
        
        if not product_id:
            logger.error("Missing product_id in message")
            return False
        
        try:
            # Fetch product detail from Tiki API
            detail_data = self._fetch_product_detail(product_id, spid)
            
            if not detail_data:
                logger.warning(f"No detail data fetched for product {product_id}")
                return False
            
            # Update database with detail information
            return self._update_product_detail(detail_data)
            
        except Exception as e:
            logger.error(f"Error processing detail for product {product_id}: {e}")
            return False
    
    def _fetch_product_detail(self, product_id: int, spid: int) -> dict:
        """
        Fetch product detail from Tiki API
        
        Args:
            product_id: Product ID
            spid: Seller product ID
            
        Returns:
            Product detail data or None
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
                product.category_id = detail_data['categories']['id']
            
            # Current seller
            if detail_data.get('current_seller', {}).get('id'):
                product.shop_id = detail_data['current_seller']['id']
            
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
    
    def start(self):
        """Start consuming product detail messages"""
        logger.info("Starting product detail consumer...")
        self.consume(self.process_detail)
    
    def close(self):
        """Close connections"""
        if self.session:
            self.session.close()
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
