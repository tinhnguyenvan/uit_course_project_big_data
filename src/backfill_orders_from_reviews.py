#!/usr/bin/env python3
"""
Backfill orders từ reviews đã có trong database
Chạy một lần để tạo orders từ 58k+ reviews cũ
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.models import SessionLocal, Review, Customer, Order, OrderLine, Product
from sqlalchemy.exc import SQLAlchemyError

def backfill_orders():
    """Tạo orders từ reviews đã có"""
    db = SessionLocal()
    
    try:
        # Lấy tất cả reviews chưa có order
        reviews = db.query(Review).outerjoin(
            Order, Review.review_id == Order.review_id
        ).filter(Order.order_id == None).all()
        
        print(f"🔍 Tìm thấy {len(reviews)} reviews chưa có order")
        
        orders_created = 0
        customers_created = 0
        
        for idx, review in enumerate(reviews, 1):
            try:
                # Lấy product để có giá
                product = db.query(Product).filter_by(
                    product_id=review.product_id
                ).first()
                
                if not product:
                    print(f"  ⚠️  Skip review {review.review_id}: product {review.product_id} not found")
                    continue
                
                # Tạo customer_id từ user_name (hash hoặc đơn giản hóa)
                customer_id = hash(review.user_name) % 1000000000
                
                # Tạo hoặc lấy customer
                customer = db.query(Customer).filter_by(customer_id=customer_id).first()
                
                if not customer:
                    customer = Customer(
                        customer_id=customer_id,
                        customer_name=review.user_name,
                        email=None,
                        phone=None,
                        address=None
                    )
                    db.add(customer)
                    customers_created += 1
                
                # Tạo order
                order = Order(
                    customer_id=customer_id,
                    review_id=review.review_id,
                    order_date=review.created_at,
                    total_amount=0,  # Sẽ update sau
                    status='completed'
                )
                db.add(order)
                db.flush()  # Để có order_id
                
                # Tạo order line
                # Giả sử mỗi review = 1 đơn hàng với 1 sản phẩm
                price = getattr(product, 'price', 0) or 100000  # Default 100k nếu không có price
                
                order_line = OrderLine(
                    order_id=order.order_id,
                    product_id=review.product_id,
                    quantity=1,
                    unit_price=price,
                    subtotal=price
                )
                db.add(order_line)
                
                # Update total amount
                order.total_amount = price
                
                orders_created += 1
                
                if idx % 1000 == 0:
                    db.commit()
                    print(f"  ✅ Processed {idx}/{len(reviews)} reviews...")
                
            except Exception as e:
                print(f"  ❌ Error processing review {review.review_id}: {e}")
                db.rollback()
                continue
        
        # Final commit
        db.commit()
        
        print(f"\n✅ Hoàn thành!")
        print(f"   Customers tạo mới: {customers_created}")
        print(f"   Orders tạo mới: {orders_created}")
        print(f"   Reviews processed: {len(reviews)}")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill orders from existing reviews')
    parser.add_argument('--confirm', action='store_true', help='Confirm to run')
    
    args = parser.parse_args()
    
    if not args.confirm:
        print("⚠️  Script này sẽ tạo orders từ 58k+ reviews hiện có")
        print("   Chạy với --confirm để xác nhận")
        sys.exit(1)
    
    backfill_orders()
