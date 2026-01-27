"""
Test script to manually trigger product detail fetch for a specific product
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.consumers.product_detail_consumer import ProductDetailConsumer
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_product_detail(product_id: int, spid: int = None):
    """Test fetching and updating product detail"""
    logger.info(f"Testing product detail fetch for product {product_id}")
    
    consumer = ProductDetailConsumer()
    
    # Manually process a product
    data = {
        'product_id': product_id,
        'spid': spid or product_id
    }
    
    success = consumer.process_detail(data)
    
    if success:
        logger.info(f"✓ Successfully fetched and updated product {product_id}")
    else:
        logger.error(f"✗ Failed to fetch product {product_id}")
    
    return success

if __name__ == '__main__':
    # Test with a sample product ID from the database
    test_product_detail(276388548, 214186190)  # Product from the demo JSON
