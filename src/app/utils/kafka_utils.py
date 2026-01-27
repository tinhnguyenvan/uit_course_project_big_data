"""
Kafka utilities
"""
import logging
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import KafkaException
from ..config import config

logger = logging.getLogger(__name__)


def check_kafka_connection(bootstrap_servers: str = None) -> bool:
    """
    Check Kafka connection
    
    Args:
        bootstrap_servers: Kafka bootstrap servers
        
    Returns:
        True if connection successful
    """
    try:
        servers = bootstrap_servers or config.KAFKA_BOOTSTRAP_SERVERS
        admin_client = AdminClient({'bootstrap.servers': servers})
        
        # Get cluster metadata
        metadata = admin_client.list_topics(timeout=5)
        
        logger.info(f"Connected to Kafka cluster with {len(metadata.brokers)} broker(s)")
        return True
        
    except KafkaException as e:
        logger.error(f"Failed to connect to Kafka: {e}")
        return False
    except Exception as e:
        logger.error(f"Error checking Kafka connection: {e}")
        return False


def create_topics(
    topics: dict,
    bootstrap_servers: str = None,
    num_partitions: int = 3,
    replication_factor: int = 1
):
    """
    Create Kafka topics if they don't exist
    
    Args:
        topics: Dict of topic names to number of partitions
        bootstrap_servers: Kafka bootstrap servers
        num_partitions: Default number of partitions
        replication_factor: Replication factor
        
    Example:
        create_topics({
            'uit-products': 3,
            'uit-reviews': 3,
            'uit-shops': 1
        })
    """
    try:
        servers = bootstrap_servers or config.KAFKA_BOOTSTRAP_SERVERS
        admin_client = AdminClient({'bootstrap.servers': servers})
        
        # Get existing topics
        metadata = admin_client.list_topics(timeout=5)
        existing_topics = set(metadata.topics.keys())
        
        # Create new topics
        new_topics = []
        for topic_name, partitions in topics.items():
            if topic_name not in existing_topics:
                new_topic = NewTopic(
                    topic_name,
                    num_partitions=partitions or num_partitions,
                    replication_factor=replication_factor
                )
                new_topics.append(new_topic)
                logger.info(f"Will create topic: {topic_name} with {partitions} partitions")
        
        if new_topics:
            # Create topics
            futures = admin_client.create_topics(new_topics)
            
            # Wait for creation
            for topic, future in futures.items():
                try:
                    future.result()
                    logger.info(f"Topic {topic} created successfully")
                except Exception as e:
                    logger.error(f"Failed to create topic {topic}: {e}")
        else:
            logger.info("All topics already exist")
            
    except KafkaException as e:
        logger.error(f"Kafka error creating topics: {e}")
        raise
    except Exception as e:
        logger.error(f"Error creating topics: {e}")
        raise


def get_topic_info(topic_name: str, bootstrap_servers: str = None) -> dict:
    """
    Get information about a Kafka topic
    
    Args:
        topic_name: Topic name
        bootstrap_servers: Kafka bootstrap servers
        
    Returns:
        Topic information dict
    """
    try:
        servers = bootstrap_servers or config.KAFKA_BOOTSTRAP_SERVERS
        admin_client = AdminClient({'bootstrap.servers': servers})
        
        metadata = admin_client.list_topics(topic_name, timeout=5)
        
        if topic_name in metadata.topics:
            topic = metadata.topics[topic_name]
            return {
                'name': topic_name,
                'partitions': len(topic.partitions),
                'partition_details': [
                    {
                        'id': p.id,
                        'leader': p.leader,
                        'replicas': p.replicas,
                        'isrs': p.isrs
                    }
                    for p in topic.partitions.values()
                ]
            }
        else:
            logger.warning(f"Topic {topic_name} not found")
            return None
            
    except Exception as e:
        logger.error(f"Error getting topic info: {e}")
        return None
