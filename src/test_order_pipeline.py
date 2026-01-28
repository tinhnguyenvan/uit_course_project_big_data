"""
Test script to manually trigger the complete order pipeline

This will:
1. Trigger a product detail fetch (which triggers review fetch)
2. Reviews get saved and push to order topic
3. OrderConsumer creates customers and orders
"""
import json
from confluent_kafka import Producer
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import config

def delivery_report(err, msg):
    """Kafka delivery callback"""
    if err is not None:
        print(f'❌ Message delivery failed: {err}')
    else:
        print(f'✅ Message delivered to {msg.topic()} [{msg.partition()}]')

def trigger_product_detail(product_id: int, spid: int):
    """
    Trigger product detail fetch which starts the complete pipeline:
    ProductDetail → ReviewFetch → ReviewDetail → Order
    """
    producer = Producer({
        'bootstrap.servers': config.KAFKA_BOOTSTRAP_SERVERS,
        'acks': 'all'
    })
    
    message = {
        'product_id': product_id,
        'spid': spid
    }
    
    print(f"\n🚀 Triggering order pipeline for product {product_id}...")
    print(f"Pipeline: ProductDetail → ReviewFetch → ReviewDetail → Order → Database")
    print(f"\nMessage: {json.dumps(message, indent=2)}")
    
    producer.produce(
        config.KAFKA_TOPIC_PRODUCT_DETAIL,
        key=str(product_id).encode('utf-8'),
        value=json.dumps(message).encode('utf-8'),
        callback=delivery_report
    )
    
    producer.flush()
    
    print(f"\n📊 Expected flow:")
    print(f"1. ProductDetailConsumer fetches product details")
    print(f"2. ReviewFetchConsumer fetches reviews with pagination")
    print(f"3. ReviewConsumer saves reviews and pushes to {config.KAFKA_TOPIC_ORDERS}")
    print(f"4. OrderConsumer creates customers and orders")
    print(f"\n⏳ Monitor logs with: docker-compose logs -f consumers | grep -E '\\[ORDER\\]|\\[REVIEW\\]'")

if __name__ == '__main__':
    # Product with good reviews (already tested before)
    product_id = 276388548
    spid = 276388548
    
    trigger_product_detail(product_id, spid)
