"""
Tiki Product Spider

Crawl products from Tiki categories
"""
import scrapy
import json
from datetime import datetime
from urllib.parse import urlencode
import logging

from ..items import ProductItem, ShopItem

logger = logging.getLogger(__name__)


class TikiProductSpider(scrapy.Spider):
    """Spider to crawl Tiki products"""
    
    name = 'tiki_products'
    allowed_domains = ['tiki.vn']
    
    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'DOWNLOAD_DELAY': 1,
    }
    
    def __init__(self, category_id=None, max_pages=10, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category_id = category_id or 1789  # Default: Electronics
        self.max_pages = int(max_pages)
        self.base_url = 'https://tiki.vn/api/v2/products'
        self.products_crawled = 0
    
    def start_requests(self):
        """Generate initial requests"""
        logger.info(f"Starting crawl for category_id: {self.category_id}")
        
        for page in range(1, self.max_pages + 1):
            params = {
                'limit': 40,
                'page': page,
                'category': self.category_id,
                'sort': 'top_seller',
            }
            
            url = f"{self.base_url}?{urlencode(params)}"
            
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={'page': page},
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': 'application/json',
                }
            )
    
    def parse(self, response):
        """Parse product list"""
        try:
            data = json.loads(response.text)
            products = data.get('data', [])
            
            page = response.meta.get('page', 1)
            logger.info(f"Page {page}: Found {len(products)} products")
            
            for product_data in products:
                # Extract product item
                product_item = self.extract_product(product_data)
                if product_item:
                    yield product_item
                    self.products_crawled += 1
                
                # Extract shop item
                shop_item = self.extract_shop(product_data)
                if shop_item:
                    yield shop_item
                
                # Get product details
                product_id = product_data.get('id')
                if product_id:
                    detail_url = f"https://tiki.vn/api/v2/products/{product_id}"
                    yield scrapy.Request(
                        url=detail_url,
                        callback=self.parse_product_detail,
                        meta={'product_id': product_id}
                    )
            
            logger.info(f"Total products crawled: {self.products_crawled}")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Parse error: {e}")
    
    def parse_product_detail(self, response):
        """Parse detailed product information"""
        try:
            data = json.loads(response.text)
            product_id = response.meta.get('product_id')
            
            # Extract additional details
            description = data.get('description', '')
            specifications = data.get('specifications', [])
            
            # You can enhance the product item with more details here
            logger.debug(f"Got details for product {product_id}")
            
        except Exception as e:
            logger.error(f"Error parsing product detail: {e}")
    
    def extract_product(self, data):
        """Extract product data"""
        try:
            product_item = ProductItem()
            
            # Basic info
            product_item['product_id'] = data.get('id')
            product_item['name'] = data.get('name', '').strip()
            product_item['url'] = f"https://tiki.vn/{data.get('url_path', '')}"
            product_item['image_url'] = data.get('thumbnail_url', '')
            product_item['description'] = data.get('short_description', '')
            
            # Shop info
            seller = data.get('seller', {})
            product_item['shop_id'] = seller.get('id', 0)
            
            # Category
            categories = data.get('categories', {})
            if categories:
                product_item['category_id'] = categories.get('id')
            
            # Ratings and sales
            product_item['rating'] = float(data.get('rating_average', 0))
            
            # Extract sold count from quantity_sold
            quantity_sold = data.get('quantity_sold', {})
            if isinstance(quantity_sold, dict):
                product_item['sold_count'] = quantity_sold.get('value', 0)
            else:
                product_item['sold_count'] = 0
            
            # Price info
            product_item['price'] = float(data.get('price', 0))
            product_item['original_price'] = float(data.get('original_price', 0))
            product_item['discount_percent'] = int(data.get('discount_rate', 0))
            product_item['stock_available'] = data.get('stock_item', {}).get('qty', 0)
            
            # Metadata
            product_item['crawled_at'] = datetime.utcnow().isoformat()
            
            return product_item
            
        except Exception as e:
            logger.error(f"Error extracting product: {e}")
            return None
    
    def extract_shop(self, data):
        """Extract shop data"""
        try:
            seller = data.get('seller', {})
            if not seller or not seller.get('id'):
                return None
            
            shop_item = ShopItem()
            shop_item['shop_id'] = seller.get('id')
            shop_item['shop_name'] = seller.get('name', '').strip()
            shop_item['is_official'] = seller.get('is_best_store', False)
            shop_item['crawled_at'] = datetime.utcnow().isoformat()
            
            return shop_item
            
        except Exception as e:
            logger.error(f"Error extracting shop: {e}")
            return None
    
    def closed(self, reason):
        """Called when spider closes"""
        logger.info(f"Spider closed: {reason}. Total products: {self.products_crawled}")
