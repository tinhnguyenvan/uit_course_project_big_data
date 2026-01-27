"""
Run all consumers in parallel
"""
import multiprocessing
import logging
import sys

from .product_consumer import ProductConsumer
from .review_consumer import ReviewConsumer

logger = logging.getLogger(__name__)


def start_product_consumer():
    """Start product consumer in separate process"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [PRODUCT] - %(levelname)s - %(message)s'
    )
    consumer = ProductConsumer()
    consumer.start()


def start_review_consumer():
    """Start review consumer in separate process"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [REVIEW] - %(levelname)s - %(message)s'
    )
    consumer = ReviewConsumer()
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
        multiprocessing.Process(target=start_review_consumer, name='ReviewConsumer'),
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
