"""
Test script to manually trigger review fetch for a specific product
"""
import sys
import os
import json
from confluent_kafka import Producer

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import config
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_review_fetch(product_id: int, spid: int, seller_id: int = 1):
    """Test triggering review fetch for a product"""
    logger.info(f"Testing review fetch for product {product_id}")
    
    # Create producer
    producer_config = {
        'bootstrap.servers': config.KAFKA_BOOTSTRAP_SERVERS,
        'acks': 'all'
    }
    producer = Producer(producer_config)
    
    # Create message
    message = {
        'product_id': product_id,
        'spid': spid,
        'seller_id': seller_id
    }
    
    # Send to review fetch topic
    message_json = json.dumps(message).encode('utf-8')
    
    producer.produce(
        config.KAFKA_TOPIC_REVIEW_FETCH,
        value=message_json
    )
    
    producer.flush()
    
    logger.info(f"✓ Sent review fetch request for product {product_id} to topic {config.KAFKA_TOPIC_REVIEW_FETCH}")
    logger.info("Check consumer logs for review processing")

if __name__ == '__main__':
    # Test with the product from demo JSON
    test_review_fetch(276388548, 214186190, 1)
