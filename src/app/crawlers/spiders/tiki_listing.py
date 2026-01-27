"""
Tiki Listing Spider - Sử dụng API personalish/v1/blocks/listings

Spider này:
- Crawl products từ API listing
- Phân trang tự động (limit=10 items/page)
- Lưu trạng thái crawl để resume
- Push từng item vào Kafka
"""
import scrapy
import json
from datetime import datetime
from urllib.parse import urlencode
import logging

from ..items import ProductItem, ShopItem
from ...models import SessionLocal, CrawlLog

logger = logging.getLogger(__name__)


class TikiListingSpider(scrapy.Spider):
    """Spider crawl Tiki listing API với resume capability"""
    
    name = 'tiki_listing'
    allowed_domains = ['tiki.vn']
    
    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 2,
    }
    
    def __init__(self, category_id=870, max_pages=None, resume=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category_id = int(category_id)
        self.max_pages = int(max_pages) if max_pages else None
        self.resume = resume
        
        self.base_url = 'https://tiki.vn/api/personalish/v1/blocks/listings'
        self.items_per_page = 10
        self.start_page = 1
        self.products_crawled = 0
        
        # Crawl log để track progress
        self.crawl_log_id = None
        
        logger.info(f"Initialized spider for category {self.category_id}")
        logger.info(f"Max pages: {self.max_pages if self.max_pages else 'unlimited'}")
        logger.info(f"Resume mode: {self.resume}")
    
    def start_requests(self):
        """Generate initial requests - resume từ page đã crawl"""
        
        # Get last crawled page nếu resume mode
        if self.resume:
            self.start_page = self._get_last_crawled_page() + 1
            logger.info(f"Resuming from page {self.start_page}")
        
        # Create crawl log entry
        self._create_crawl_log()
        
        # Generate requests
        page = self.start_page
        
        while True:
            # Check max_pages limit
            if self.max_pages and page > (self.start_page + self.max_pages - 1):
                break
            
            params = {
                'limit': self.items_per_page,
                'category': self.category_id,
                'page': page,
            }
            
            url = f"{self.base_url}?{urlencode(params)}"
            
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={'page': page},
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': 'application/json',
                },
                dont_filter=True
            )
            
            page += 1
    
    def parse(self, response):
        """Parse listing response"""
        try:
            data = json.loads(response.text)
            
            # Extract products from response
            products = data.get('data', [])
            page = response.meta.get('page', 1)
            paging = data.get('paging', {})
            
            logger.info(f"Page {page}: Found {len(products)} products")
            logger.info(f"Paging info: total={paging.get('total', 0)}, last_page={paging.get('last_page', 0)}")
            
            # No products = end of pagination
            if not products:
                logger.info(f"No products found on page {page}. Stopping.")
                return
            
            # Process each product
            for product_data in products:
                # Extract product item
                product_item = self.extract_product(product_data)
                if product_item:
                    yield product_item
                    self.products_crawled += 1
                
                # Extract shop item if available
                shop_item = self.extract_shop(product_data)
                if shop_item:
                    yield shop_item
            
            # Update crawl log with progress
            self._update_crawl_log(page, len(products))
            
            logger.info(f"Page {page} completed. Total products: {self.products_crawled}")
            
            # Check if reached last page
            last_page = paging.get('last_page', 0)
            if page >= last_page:
                logger.info(f"Reached last page ({last_page})")
                return
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error on page {response.meta.get('page')}: {e}")
            self._log_error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Parse error on page {response.meta.get('page')}: {e}")
            self._log_error(f"Parse error: {e}")
    
    def extract_product(self, data):
        """Extract product data từ listing API response"""
        try:
            product_item = ProductItem()
            
            # Set item type
            product_item['item_type'] = 'product'
            
            # Basic info
            product_item['product_id'] = data.get('id')
            product_item['name'] = data.get('name', '').strip()
            
            # URL - construct full URL
            url_path = data.get('url_path', '')
            product_item['url'] = f"https://tiki.vn/{url_path}" if url_path else ''
            
            # Images
            product_item['image_url'] = data.get('thumbnail_url', '')
            
            # Description
            product_item['description'] = data.get('short_description', '')
            
            # Shop info - từ seller field
            seller = data.get('seller')
            if seller:
                product_item['shop_id'] = seller.get('id', 0)
            else:
                # Fallback to seller_id nếu có
                product_item['shop_id'] = data.get('seller_id', 0)
            
            # Category - extract từ primary_category_path
            category_path = data.get('primary_category_path', '')
            if category_path:
                # Get last category ID from path like "1/2/8322/316/870/871"
                categories = category_path.split('/')
                if categories:
                    product_item['category_id'] = int(categories[-1])
            
            # Ratings and reviews
            product_item['rating'] = float(data.get('rating_average', 0))
            
            # Sold count - từ quantity_sold
            quantity_sold = data.get('quantity_sold', {})
            if isinstance(quantity_sold, dict):
                product_item['sold_count'] = quantity_sold.get('value', 0)
            else:
                product_item['sold_count'] = 0
            
            # Price info
            product_item['price'] = float(data.get('price', 0))
            product_item['original_price'] = float(data.get('original_price', 0))
            product_item['discount_percent'] = int(data.get('discount_rate', 0))
            
            # Stock - từ availability
            product_item['stock_available'] = 1 if data.get('availability', 0) == 1 else 0
            
            # Metadata
            product_item['crawled_at'] = datetime.utcnow().isoformat()
            
            return product_item
            
        except Exception as e:
            logger.error(f"Error extracting product {data.get('id')}: {e}")
            return None
    
    def extract_shop(self, data):
        """Extract shop data từ seller field"""
        try:
            seller = data.get('seller')
            if not seller:
                return None
            
            shop_id = seller.get('id')
            if not shop_id:
                return None
            
            shop_item = ShopItem()
            shop_item['item_type'] = 'shop'
            shop_item['shop_id'] = shop_id
            shop_item['shop_name'] = seller.get('name', '').strip()
            
            # Check if official store
            seller_type = data.get('visible_impression_info', {}).get('amplitude', {}).get('seller_type', '')
            shop_item['is_official'] = (seller_type == 'OFFICIAL_STORE')
            
            shop_item['crawled_at'] = datetime.utcnow().isoformat()
            
            return shop_item
            
        except Exception as e:
            logger.error(f"Error extracting shop: {e}")
            return None
    
    def _get_last_crawled_page(self):
        """Lấy page cuối cùng đã crawl từ database"""
        try:
            db = SessionLocal()
            
            # Query last successful crawl log
            last_log = db.query(CrawlLog).filter(
                CrawlLog.crawler_type == f'tiki_listing_cat_{self.category_id}',
                CrawlLog.status.in_(['running', 'completed'])
            ).order_by(CrawlLog.started_at.desc()).first()
            
            db.close()
            
            if last_log and last_log.error_message:
                # Parse page number từ error_message (lưu dạng "Last page: 10")
                try:
                    import re
                    match = re.search(r'Last page: (\d+)', last_log.error_message)
                    if match:
                        return int(match.group(1))
                except:
                    pass
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting last crawled page: {e}")
            return 0
    
    def _create_crawl_log(self):
        """Tạo crawl log entry"""
        try:
            db = SessionLocal()
            
            crawl_log = CrawlLog(
                crawler_type=f'tiki_listing_cat_{self.category_id}',
                status='running',
                started_at=datetime.utcnow(),
                error_message=f'Last page: {self.start_page - 1}'
            )
            
            db.add(crawl_log)
            db.commit()
            
            self.crawl_log_id = crawl_log.log_id
            
            db.close()
            
            logger.info(f"Created crawl log ID: {self.crawl_log_id}")
            
        except Exception as e:
            logger.error(f"Error creating crawl log: {e}")
    
    def _update_crawl_log(self, page, items_count):
        """Update crawl log với progress"""
        if not self.crawl_log_id:
            return
        
        try:
            db = SessionLocal()
            
            crawl_log = db.query(CrawlLog).filter_by(log_id=self.crawl_log_id).first()
            if crawl_log:
                crawl_log.items_crawled = self.products_crawled
                crawl_log.error_message = f'Last page: {page}'
                db.commit()
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error updating crawl log: {e}")
    
    def _log_error(self, error_msg):
        """Log error vào database"""
        if not self.crawl_log_id:
            return
        
        try:
            db = SessionLocal()
            
            crawl_log = db.query(CrawlLog).filter_by(log_id=self.crawl_log_id).first()
            if crawl_log:
                crawl_log.errors_count = (crawl_log.errors_count or 0) + 1
                if not crawl_log.error_message:
                    crawl_log.error_message = ''
                crawl_log.error_message += f'\n{error_msg}'
                db.commit()
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error logging error: {e}")
    
    def closed(self, reason):
        """Called when spider closes"""
        
        # Update final crawl log
        if self.crawl_log_id:
            try:
                db = SessionLocal()
                
                crawl_log = db.query(CrawlLog).filter_by(log_id=self.crawl_log_id).first()
                if crawl_log:
                    crawl_log.status = 'completed' if reason == 'finished' else 'failed'
                    crawl_log.completed_at = datetime.utcnow()
                    
                    # Calculate duration
                    if crawl_log.started_at:
                        duration = (datetime.utcnow() - crawl_log.started_at).total_seconds()
                        crawl_log.duration_seconds = int(duration)
                    
                    db.commit()
                
                db.close()
                
            except Exception as e:
                logger.error(f"Error updating final crawl log: {e}")
        
        logger.info(f"Spider closed: {reason}")
        logger.info(f"Total products crawled: {self.products_crawled}")
