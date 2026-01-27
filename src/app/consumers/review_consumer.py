"""
Review consumer - processes reviews from Kafka and saves to PostgreSQL
"""
import logging
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from .base_consumer import BaseConsumer
from ..models import SessionLocal, Review, Product
from ..config import config

logger = logging.getLogger(__name__)


class ReviewConsumer(BaseConsumer):
    """Consumer for review messages"""
    
    def __init__(self):
        super().__init__(
            topics=[config.KAFKA_TOPIC_REVIEWS],
            group_id='review-consumer-group',
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS
        )
        self.db = None
    
    def process_review(self, data: dict) -> bool:
        """
        Process review message and save to database
        
        Args:
            data: Review data from Kafka
            
        Returns:
            True if successful, False otherwise
        """
        self.db = SessionLocal()
        
        try:
            # Verify product exists
            product = self.db.query(Product).filter_by(
                product_id=data['product_id']
            ).first()
            
            if not product:
                logger.warning(f"Product {data['product_id']} not found, skipping review")
                return False
            
            # Parse created_at timestamp
            created_at = data.get('created_at')
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = datetime.utcnow()
            elif not created_at:
                created_at = datetime.utcnow()
            
            # Create review
            review = Review(
                product_id=data['product_id'],
                user_name=data.get('user_name', 'Anonymous'),
                rating=data['rating'],
                comment=data.get('comment', ''),
                has_images=data.get('has_images', False),
                helpful_count=data.get('helpful_count', 0),
                created_at=created_at,
                crawled_at=datetime.utcnow()
            )
            
            self.db.add(review)
            self.db.commit()
            
            logger.info(
                f"Successfully saved review for product {data['product_id']}, "
                f"rating: {data['rating']}"
            )
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error processing review: {e}")
            self.db.rollback()
            return False
        
        except Exception as e:
            logger.error(f"Error processing review: {e}")
            self.db.rollback()
            return False
        
        finally:
            if self.db:
                self.db.close()
    
    def start(self):
        """Start consuming review messages"""
        logger.info("Starting review consumer...")
        self.consume(self.process_review)


# Standalone runner
if __name__ == '__main__':
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        consumer = ReviewConsumer()
        consumer.start()
    except KeyboardInterrupt:
        logger.info("Consumer stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        sys.exit(1)
