"""
Run all consumers in parallel
"""
import multiprocessing
import logging
import sys

from .product_consumer import ProductConsumer
from .product_detail_consumer import ProductDetailConsumer
from .review_fetch_consumer import ReviewFetchConsumer
from .review_consumer import ReviewConsumer
from .order_consumer import OrderConsumer

logger = logging.getLogger(__name__)


def start_product_consumer():
    """Start product consumer in separate process"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [PRODUCT] - %(levelname)s - %(message)s'
    )
    consumer = ProductConsumer()
    consumer.start()


def start_product_detail_consumer():
    """Start product detail consumer in separate process"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [PRODUCT-DETAIL] - %(levelname)s - %(message)s'
    )
    consumer = ProductDetailConsumer()
    consumer.start()


def start_review_fetch_consumer():
    """Start review fetch consumer in separate process"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [REVIEW-FETCH] - %(levelname)s - %(message)s'
    )
    consumer = ReviewFetchConsumer()
    consumer.start()


def start_review_consumer():
    """Start review consumer in separate process"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [REVIEW] - %(levelname)s - %(message)s'
    )
    consumer = ReviewConsumer()
    consumer.start()


def start_order_consumer():
    """Start order consumer in separate process"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [ORDER] - %(levelname)s - %(message)s'
    )
    consumer = OrderConsumer()
    consumer.start()


def main():
    """Run all consumers"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting all Kafka consumers...")
    
    # Create processes
    processes = [
        multiprocessing.Process(target=start_product_consumer, name='ProductConsumer'),
        multiprocessing.Process(target=start_product_detail_consumer, name='ProductDetailConsumer'),
        multiprocessing.Process(target=start_review_fetch_consumer, name='ReviewFetchConsumer'),
        multiprocessing.Process(target=start_review_consumer, name='ReviewConsumer'),
        multiprocessing.Process(target=start_order_consumer, name='OrderConsumer'),
    ]
    
    # Start all processes
    for process in processes:
        process.start()
        logger.info(f"Started {process.name}")
    
    try:
        # Wait for all processes
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        logger.info("Stopping all consumers...")
        for process in processes:
            process.terminate()
            process.join()
        logger.info("All consumers stopped")
        sys.exit(0)


if __name__ == '__main__':
    main()
