"""
Base Kafka consumer
"""
from confluent_kafka import Consumer, KafkaError
import json
import logging
from typing import Callable, Dict, Any, List

logger = logging.getLogger(__name__)


class BaseConsumer:
    """Base Kafka consumer class"""
    
    def __init__(
        self,
        topics: List[str],
        group_id: str,
        bootstrap_servers: str = 'localhost:9092',
        auto_offset_reset: str = 'earliest'
    ):
        """
        Initialize Kafka consumer
        
        Args:
            topics: List of topics to subscribe to
            group_id: Consumer group ID
            bootstrap_servers: Kafka bootstrap servers
            auto_offset_reset: Where to start reading ('earliest' or 'latest')
        """
        self.topics = topics
        self.config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': auto_offset_reset,
            'enable.auto.commit': False,  # Manual commit for reliability
            'max.poll.interval.ms': 300000,  # 5 minutes
            'session.timeout.ms': 30000,
        }
        
        try:
            self.consumer = Consumer(self.config)
            self.consumer.subscribe(topics)
            logger.info(f"Consumer initialized for topics: {topics}, group: {group_id}")
        except Exception as e:
            logger.error(f"Failed to initialize consumer: {e}")
            raise
    
    def consume(self, process_func: Callable[[Dict[str, Any]], bool], timeout: float = 1.0):
        """
        Start consuming messages
        
        Args:
            process_func: Function to process each message. Should return True on success.
            timeout: Poll timeout in seconds
        """
        messages_processed = 0
        messages_failed = 0
        
        try:
            logger.info("Starting message consumption...")
            
            while True:
                msg = self.consumer.poll(timeout=timeout)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(f'Reached end of partition {msg.partition()}')
                    else:
                        logger.error(f'Consumer error: {msg.error()}')
                    continue
                
                try:
                    # Deserialize message
                    data = json.loads(msg.value().decode('utf-8'))
                    
                    logger.debug(f"Processing message from {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")
                    
                    # Process message
                    if process_func(data):
                        # Commit offset if processing successful
                        self.consumer.commit(msg)
                        messages_processed += 1
                        logger.info(f"Message processed successfully. Total: {messages_processed}")
                    else:
                        messages_failed += 1
                        logger.warning(f"Failed to process message. Total failures: {messages_failed}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    messages_failed += 1
                
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    messages_failed += 1
                
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
        
        finally:
            logger.info(f"Closing consumer. Processed: {messages_processed}, Failed: {messages_failed}")
            self.close()
    
    def close(self):
        """Close consumer connection"""
        try:
            self.consumer.close()
            logger.info("Consumer closed")
        except Exception as e:
            logger.error(f"Error closing consumer: {e}")
