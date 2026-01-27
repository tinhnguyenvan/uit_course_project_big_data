"""
Tiki Review Spider

Crawl reviews for specific products
"""
import scrapy
import json
from datetime import datetime
from urllib.parse import urlencode
import logging

from ..items import ReviewItem

logger = logging.getLogger(__name__)


class TikiReviewSpider(scrapy.Spider):
    """Spider to crawl Tiki product reviews"""
    
    name = 'tiki_reviews'
    allowed_domains = ['tiki.vn']
    
    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 2,
    }
    
    def __init__(self, product_ids=None, max_pages=5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # product_ids can be a single ID or comma-separated IDs
        if product_ids:
            if isinstance(product_ids, str):
                self.product_ids = [int(pid.strip()) for pid in product_ids.split(',')]
            else:
                self.product_ids = [int(product_ids)]
        else:
            self.product_ids = []
        
        self.max_pages = int(max_pages)
        self.base_url = 'https://tiki.vn/api/v2/reviews'
        self.reviews_crawled = 0
    
    def start_requests(self):
        """Generate initial requests"""
        if not self.product_ids:
            logger.warning("No product_ids provided")
            return
        
        logger.info(f"Starting review crawl for {len(self.product_ids)} products")
        
        for product_id in self.product_ids:
            for page in range(1, self.max_pages + 1):
                params = {
                    'product_id': product_id,
                    'page': page,
                    'limit': 20,
                    'sort': 'score|desc,id|desc,stars|all',
                }
                
                url = f"{self.base_url}?{urlencode(params)}"
                
                yield scrapy.Request(
                    url=url,
                    callback=self.parse,
                    meta={
                        'product_id': product_id,
                        'page': page
                    },
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        'Accept': 'application/json',
                    }
                )
    
    def parse(self, response):
        """Parse review list"""
        try:
            data = json.loads(response.text)
            reviews = data.get('data', [])
            
            product_id = response.meta.get('product_id')
            page = response.meta.get('page', 1)
            
            logger.info(f"Product {product_id}, Page {page}: Found {len(reviews)} reviews")
            
            if not reviews:
                logger.info(f"No more reviews for product {product_id} at page {page}")
                return
            
            for review_data in reviews:
                review_item = self.extract_review(review_data, product_id)
                if review_item:
                    yield review_item
                    self.reviews_crawled += 1
            
            logger.info(f"Total reviews crawled: {self.reviews_crawled}")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Parse error: {e}")
    
    def extract_review(self, data, product_id):
        """Extract review data"""
        try:
            review_item = ReviewItem()
            
            # Product ID
            review_item['product_id'] = product_id
            
            # User info
            review_item['user_name'] = data.get('created_by', {}).get('name', 'Anonymous')
            
            # Rating and comment
            review_item['rating'] = int(data.get('rating', 0))
            review_item['comment'] = data.get('content', '').strip()
            
            # Images
            images = data.get('images', [])
            review_item['has_images'] = len(images) > 0
            
            # Helpful count
            review_item['helpful_count'] = int(data.get('thank_count', 0))
            
            # Created date
            created_at = data.get('created_at')
            if created_at:
                # Parse datetime string
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    review_item['created_at'] = dt.isoformat()
                except:
                    review_item['created_at'] = datetime.utcnow().isoformat()
            else:
                review_item['created_at'] = datetime.utcnow().isoformat()
            
            # Metadata
            review_item['crawled_at'] = datetime.utcnow().isoformat()
            
            return review_item
            
        except Exception as e:
            logger.error(f"Error extracting review: {e}")
            return None
    
    def closed(self, reason):
        """Called when spider closes"""
        logger.info(f"Spider closed: {reason}. Total reviews: {self.reviews_crawled}")
