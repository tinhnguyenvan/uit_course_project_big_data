"""
Kafka consumers to process data from topics and save to PostgreSQL
"""
from .base_consumer import BaseConsumer
from .product_consumer import ProductConsumer
from .review_consumer import ReviewConsumer

__all__ = ['BaseConsumer', 'ProductConsumer', 'ReviewConsumer']
