"""
Order consumer - xử lý các message đơn hàng từ Kafka và tạo đơn hàng trong PostgreSQL
"""
import logging
import json
from datetime import datetime
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from .base_consumer import BaseConsumer
from ..models import SessionLocal, Customer, Order, OrderLine, Product, ProductPrice
from ..config import config

logger = logging.getLogger(__name__)


class OrderConsumer(BaseConsumer):
    """Consumer xử lý message đơn hàng từ các đánh giá"""
    
    def __init__(self):
        super().__init__(
            topics=[config.KAFKA_TOPIC_ORDERS],
            group_id='order-consumer-group',
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS
        )
        self.db = None
    
    def _ensure_customer(self, customer_id: int, customer_name: str):
        """
        Đảm bảo khách hàng tồn tại, tạo mới nếu chưa có
        
        Args:
            customer_id: ID người dùng Tiki
            customer_name: Tên khách hàng từ đánh giá
        """
        customer = self.db.query(Customer).filter_by(customer_id=customer_id).first()
        
        if not customer:
            customer = Customer(
                customer_id=customer_id,
                customer_name=customer_name
            )
            self.db.add(customer)
            self.db.flush()
            logger.info(f"Created new customer {customer_id}: {customer_name}")
        else:
            # Cập nhật tên nếu thay đổi
            if customer.customer_name != customer_name:
                customer.customer_name = customer_name
                self.db.flush()
                logger.debug(f"Updated customer {customer_id} name to {customer_name}")
        
        return customer
    
    def _get_product_price(self, product_id: int) -> Decimal:
        """
        Lấy giá sản phẩm mới nhất từ bảng product_prices
        
        Args:
            product_id: ID sản phẩm
            
        Returns:
            Giá mới nhất hoặc None
        """
        latest_price = self.db.query(ProductPrice).filter_by(
            product_id=product_id
        ).order_by(ProductPrice.timestamp.desc()).first()
        
        if latest_price:
            return latest_price.price
        
        return None
    
    def process_order(self, data: dict) -> bool:
        """
        Xử lý message đơn hàng và tạo đơn hàng với các chi tiết
        
        Args:
            data: Dữ liệu đơn hàng từ Kafka (từ ReviewConsumer)
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        self.db = SessionLocal()
        
        try:
            review_id = data.get('review_id')
            product_id = data.get('product_id')
            customer_id = data.get('customer_id')
            customer_name = data.get('customer_name', 'Anonymous')
            
            if not all([review_id, product_id, customer_id]):
                logger.error(f"Missing required fields in order message: {data}")
                return False
            
            # Kiểm tra xem đơn hàng đã tồn tại cho review này chưa (tránh trùng lặp)
            existing_order = self.db.query(Order).filter_by(
                review_id=review_id
            ).first()
            
            if existing_order:
                logger.debug(f"Order for review {review_id} already exists, skipping")
                return True
            
            # Xác minh sản phẩm tồn tại
            product = self.db.query(Product).filter_by(product_id=product_id).first()
            if not product:
                logger.warning(f"Product {product_id} not found, skipping order for review {review_id}")
                return False
            
            # Đảm bảo khách hàng tồn tại
            customer = self._ensure_customer(customer_id, customer_name)
            
            # Parse ngày đặt hàng
            order_date = data.get('order_date')
            if isinstance(order_date, str):
                try:
                    order_date = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                except:
                    order_date = datetime.utcnow()
            else:
                order_date = datetime.utcnow()
            
            # Lấy giá sản phẩm
            unit_price = self._get_product_price(product_id)
            
            # Tính tổng tiền (giả sử số lượng = 1)
            quantity = 1
            total_amount = unit_price * quantity if unit_price else None
            
            # Tạo đơn hàng
            order = Order(
                customer_id=customer_id,
                review_id=review_id,
                order_date=order_date,
                total_amount=total_amount,
                status='completed'  # Có review nghĩa là sản phẩm đã được giao
            )
            
            self.db.add(order)
            self.db.flush()  # Lấy order_id
            
            # Tạo chi tiết đơn hàng
            order_line = OrderLine(
                order_id=order.order_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price
            )
            
            self.db.add(order_line)
            self.db.commit()
            
            logger.info(
                f"Successfully created order {order.order_id} for customer {customer_id}, "
                f"review {review_id}, product {product_id}, total: {total_amount}"
            )
            
            return True
            
        except IntegrityError as e:
            logger.warning(f"Order for review {review_id} already exists (IntegrityError), skipping")
            self.db.rollback()
            return True  # Coi như thành công vì đơn hàng đã tồn tại
            
        except SQLAlchemyError as e:
            logger.error(f"Database error processing order: {e}")
            self.db.rollback()
            return False
        
        except Exception as e:
            logger.error(f"Error processing order: {e}")
            self.db.rollback()
            return False
        
        finally:
            if self.db:
                self.db.close()
    
    def start(self):
        """Bắt đầu consumer các message đơn hàng"""
        logger.info("Starting order consumer...")
        self.consume(self.process_order)


# Standalone runner
if __name__ == '__main__':
    import sys
    
    # Thiết lập logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        consumer = OrderConsumer()
        consumer.start()
    except KeyboardInterrupt:
        logger.info("Consumer stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        sys.exit(1)
