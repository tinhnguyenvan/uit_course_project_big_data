"""
Review consumer - xử lý các đánh giá từ Kafka và lưu vào PostgreSQL
"""
import logging
import json
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from confluent_kafka import Producer

from .base_consumer import BaseConsumer
from ..models import SessionLocal, Review, Product
from ..config import config

logger = logging.getLogger(__name__)


class ReviewConsumer(BaseConsumer):
    """Consumer xử lý các message chi tiết đánh giá"""
    
    def __init__(self):
        super().__init__(
            topics=[config.KAFKA_TOPIC_REVIEW_DETAIL],
            group_id='review-detail-consumer-group',
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS
        )
        self.db = None
        
        # Kafka producer cho topic đơn hàng
        self.order_producer = Producer({
            'bootstrap.servers': config.KAFKA_BOOTSTRAP_SERVERS,
            'acks': 'all',
            'retries': 3
        })
    
    def process_review(self, data: dict) -> bool:
        """
        Xử lý message chi tiết đánh giá và lưu vào database
        
        Args:
            data: Dữ liệu chi tiết đánh giá từ Kafka (từ Tiki review API)
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        self.db = SessionLocal()
        
        try:
            product_id = data.get('product_id')
            review_id = data.get('id')
            
            if not product_id or not review_id:
                logger.error(f"Missing product_id or review id in message")
                return False
            
            # Xác minh sản phẩm tồn tại
            product = self.db.query(Product).filter_by(product_id=product_id).first()
            
            if not product:
                logger.warning(f"Product {product_id} not found, skipping review {review_id}")
                return False
            
            # Kiểm tra xem đánh giá đã tồn tại chưa
            existing_review = self.db.query(Review).filter_by(
                review_id=review_id
            ).first()
            
            if existing_review:
                logger.debug(f"Review {review_id} already exists, skipping")
                return True
            
            # Parse timestamp created_at (unix timestamp từ API)
            created_at = data.get('created_at')
            if isinstance(created_at, (int, float)):
                created_at = datetime.fromtimestamp(created_at)
            elif isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = datetime.utcnow()
            else:
                created_at = datetime.utcnow()
            
            # Trích xuất thông tin người dùng
            created_by = data.get('created_by', {})
            user_name = created_by.get('full_name') or created_by.get('name', 'Anonymous')
            
            # Trích xuất comment (nội dung)
            comment = data.get('content', '') or data.get('title', '')
            
            # Đếm số lượng hình ảnh
            images = data.get('images', [])
            has_images = len(images) > 0
            
            # Trích xuất số lượt hữu ích (thank_count trong API)
            helpful_count = data.get('thank_count', 0)
            
            # Tạo đánh giá
            review = Review(
                review_id=review_id,
                product_id=product_id,
                user_name=user_name,
                rating=data.get('rating', 0),
                comment=comment,
                has_images=has_images,
                helpful_count=helpful_count,
                created_at=created_at,
                crawled_at=datetime.utcnow()
            )
            
            self.db.add(review)
            self.db.commit()
            
            logger.info(
                f"Successfully saved review {review_id} for product {product_id}, "
                f"rating: {data.get('rating')}"
            )
            
            # Push tới topic đơn hàng để tạo đơn hàng
            order_message = {
                'review_id': review_id,
                'product_id': product_id,
                'customer_id': created_by.get('id'),  # Tiki user ID
                'customer_name': user_name,
                'order_date': created_at.isoformat(),
                'rating': data.get('rating', 0)
            }
            
            self.order_producer.produce(
                config.KAFKA_TOPIC_ORDERS,
                key=str(review_id).encode('utf-8'),
                value=json.dumps(order_message).encode('utf-8'),
                callback=lambda err, msg: logger.error(f"Order message delivery failed: {err}") if err 
                         else logger.debug(f"Order message for review {review_id} delivered")
            )
            self.order_producer.flush()
            
            logger.info(f"Pushed order message for review {review_id} to topic {config.KAFKA_TOPIC_ORDERS}")
            
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
        """Bắt đầu consumer các message đánh giá"""
        logger.info("Starting review consumer...")
        self.consume(self.process_review)


# Standalone runner
if __name__ == '__main__':
    import sys
    
    # Thiết lập logging
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
