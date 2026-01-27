"""
Review Fetch Consumer - fetches product reviews from Tiki API with pagination
"""
import logging
import requests
import json
from confluent_kafka import Producer

from .base_consumer import BaseConsumer
from ..config import config

logger = logging.getLogger(__name__)


class ReviewFetchConsumer(BaseConsumer):
    """Consumer that fetches reviews from Tiki API and pushes to review detail topic"""
    
    def __init__(self):
        super().__init__(
            topics=[config.KAFKA_TOPIC_REVIEW_FETCH],
            group_id='review-fetch-consumer-group',
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS
        )
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://tiki.vn/'
        })
        self.review_detail_producer = None
        self._init_review_detail_producer()
    
    def _init_review_detail_producer(self):
        """Initialize Kafka producer for review detail topic"""
        try:
            producer_config = {
                'bootstrap.servers': config.KAFKA_BOOTSTRAP_SERVERS,
                'acks': 'all',
                'retries': 3
            }
            self.review_detail_producer = Producer(producer_config)
            logger.info("Review detail producer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize review detail producer: {e}")
            self.review_detail_producer = None
    
    def process_review_fetch(self, data: dict) -> bool:
        """
        Process review fetch message - fetch reviews from API and push to detail topic
        
        Args:
            data: Message containing product_id, spid, seller_id
            
        Returns:
            True if successful, False otherwise
        """
        product_id = data.get('product_id')
        spid = data.get('spid')
        seller_id = data.get('seller_id', 1)
        
        if not product_id:
            logger.error("Missing product_id in message")
            return False
        
        try:
            logger.info(f"Fetching reviews for product {product_id} (spid: {spid})")
            
            # Fetch first page to get total pages
            first_page_data = self._fetch_reviews_page(product_id, spid, seller_id, page=1)
            
            if not first_page_data:
                logger.warning(f"No reviews data for product {product_id}")
                return False
            
            # Process first page reviews
            reviews_processed = self._process_reviews(first_page_data.get('data', []), product_id)
            
            # Get pagination info
            paging = first_page_data.get('paging', {})
            total_pages = paging.get('last_page', 1)
            
            logger.info(f"Product {product_id}: {paging.get('total', 0)} reviews, {total_pages} pages")
            
            # Fetch remaining pages
            for page in range(2, total_pages + 1):
                page_data = self._fetch_reviews_page(product_id, spid, seller_id, page)
                
                if page_data:
                    count = self._process_reviews(page_data.get('data', []), product_id)
                    reviews_processed += count
                    logger.debug(f"Processed page {page}/{total_pages}: {count} reviews")
            
            logger.info(f"Completed fetching {reviews_processed} reviews for product {product_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error fetching reviews for product {product_id}: {e}")
            return False
    
    def _fetch_reviews_page(self, product_id: int, spid: int, seller_id: int, page: int = 1) -> dict:
        """
        Fetch a single page of reviews from Tiki API
        
        Args:
            product_id: Product ID
            spid: Seller product ID
            seller_id: Seller ID
            page: Page number
            
        Returns:
            Reviews data or None
        """
        url = "https://tiki.vn/api/v2/reviews"
        params = {
            'limit': 5,  # Reviews per page
            'include': 'comments,contribute_info,attribute_vote_summary',
            'sort': 'score|desc,id|desc,stars|all',
            'page': page,
            'spid': spid,
            'product_id': product_id,
            'seller_id': seller_id
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                logger.warning(f"Failed to fetch reviews page {page}: HTTP {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Request error fetching reviews page {page}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for reviews page {page}: {e}")
            return None
    
    def _process_reviews(self, reviews: list, product_id: int) -> int:
        """
        Process and push reviews to detail topic
        
        Args:
            reviews: List of review objects
            product_id: Product ID
            
        Returns:
            Number of reviews processed
        """
        if not self.review_detail_producer:
            logger.warning("Review detail producer not available")
            return 0
        
        count = 0
        for review in reviews:
            try:
                # Add product_id to review data
                review['product_id'] = product_id
                
                # Serialize and send
                message_json = json.dumps(review).encode('utf-8')
                
                self.review_detail_producer.produce(
                    config.KAFKA_TOPIC_REVIEW_DETAIL,
                    value=message_json,
                    callback=self._delivery_callback
                )
                
                count += 1
                
            except Exception as e:
                logger.error(f"Failed to push review {review.get('id')} to detail topic: {e}")
        
        # Flush all messages
        self.review_detail_producer.flush()
        
        return count
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery confirmation"""
        if err:
            logger.error(f"Review message delivery failed: {err}")
        else:
            logger.debug(f"Review delivered to {msg.topic()}")
    
    def start(self):
        """Start consuming review fetch messages"""
        logger.info("Starting review fetch consumer...")
        self.consume(self.process_review_fetch)
    
    def close(self):
        """Close connections"""
        if self.session:
            self.session.close()
        if self.review_detail_producer:
            self.review_detail_producer.flush()
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
        consumer = ReviewFetchConsumer()
        consumer.start()
    except KeyboardInterrupt:
        logger.info("Consumer stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        sys.exit(1)
