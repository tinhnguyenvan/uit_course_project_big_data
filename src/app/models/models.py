"""
SQLAlchemy ORM Models - Các mô hình dữ liệu
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Float, 
    Boolean, DateTime, ForeignKey, DECIMAL, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Category(Base):
    """Danh mục sản phẩm"""
    __tablename__ = "categories"
    
    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(255), nullable=False, unique=True)
    parent_id = Column(Integer, ForeignKey("categories.category_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Quan hệ
    products = relationship("Product", back_populates="category")
    parent = relationship("Category", remote_side=[category_id], backref="children")
    
    def __repr__(self):
        return f"<Category(id={self.category_id}, name='{self.category_name}')>"


class Shop(Base):
    """Thông tin shop/người bán"""
    __tablename__ = "shops"
    
    shop_id = Column(BigInteger, primary_key=True)
    shop_name = Column(String(255), nullable=False)
    rating = Column(DECIMAL(3, 2))
    response_rate = Column(Integer)
    follower_count = Column(Integer)
    is_official = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Quan hệ
    products = relationship("Product", back_populates="shop")
    
    def __repr__(self):
        return f"<Shop(id={self.shop_id}, name='{self.shop_name}')>"


class Product(Base):
    """Thông tin sản phẩm"""
    __tablename__ = "products"
    
    product_id = Column(BigInteger, primary_key=True)
    name = Column(Text, nullable=False)
    shop_id = Column(BigInteger, ForeignKey("shops.shop_id"))
    category_id = Column(Integer, ForeignKey("categories.category_id"))
    url = Column(Text, nullable=False)
    image_url = Column(Text)
    description = Column(Text)
    rating = Column(DECIMAL(3, 2))
    sold_count = Column(Integer, default=0)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Các trường chi tiết từ product detail API
    review_count = Column(Integer, default=0)
    discount_rate = Column(Integer, default=0)
    short_description = Column(Text)
    authors = Column(JSONB)
    specifications = Column(JSONB)
    configurable_options = Column(JSONB)
    
    # Quan hệ
    shop = relationship("Shop", back_populates="products")
    category = relationship("Category", back_populates="products")
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")
    prices = relationship("ProductPrice", back_populates="product", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Product(id={self.product_id}, name='{self.name[:30]}...')>"


class ProductPrice(Base):
    """Lịch sử giá sản phẩm (TimescaleDB hypertable)"""
    __tablename__ = "product_prices"
    
    product_id = Column(BigInteger, ForeignKey("products.product_id"), primary_key=True)
    price = Column(DECIMAL(12, 2), nullable=False)
    original_price = Column(DECIMAL(12, 2))
    discount_percent = Column(Integer)
    stock_available = Column(Integer)
    timestamp = Column(DateTime(timezone=True), primary_key=True, server_default=func.now())
    
    # Quan hệ
    product = relationship("Product", back_populates="prices")
    
    def __repr__(self):
        return f"<ProductPrice(product_id={self.product_id}, price={self.price}, timestamp={self.timestamp})>"


class Review(Base):
    """Đánh giá của khách hàng"""
    __tablename__ = "reviews"
    
    review_id = Column(BigInteger, primary_key=True)  # Sử dụng Tiki review ID
    product_id = Column(BigInteger, ForeignKey("products.product_id"), nullable=False)
    user_name = Column(String(255))
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    has_images = Column(Boolean, default=False)
    helpful_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True))
    crawled_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
    )
    
    # Quan hệ
    product = relationship("Product", back_populates="reviews")
    sentiment = relationship("ReviewSentiment", back_populates="review", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Review(id={self.review_id}, product_id={self.product_id}, rating={self.rating})>"


class ReviewSentiment(Base):
    """Kết quả phân tích cảm xúc đánh giá"""
    __tablename__ = "review_sentiment"
    
    sentiment_id = Column(BigInteger, primary_key=True, autoincrement=True)
    review_id = Column(BigInteger, ForeignKey("reviews.review_id"), unique=True, nullable=False)
    sentiment = Column(String(20), nullable=False)
    confidence_score = Column(DECIMAL(5, 4))
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint(
            "sentiment IN ('positive', 'negative', 'neutral')", 
            name='check_sentiment_value'
        ),
    )
    
    # Quan hệ
    review = relationship("Review", back_populates="sentiment")
    
    def __repr__(self):
        return f"<ReviewSentiment(review_id={self.review_id}, sentiment='{self.sentiment}')>"


class Customer(Base):
    """Thông tin khách hàng từ đánh giá"""
    __tablename__ = "customers"
    
    customer_id = Column(BigInteger, primary_key=True)  # Sử dụng Tiki user ID
    customer_name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Quan hệ
    orders = relationship("Order", back_populates="customer")
    
    def __repr__(self):
        return f"<Customer(id={self.customer_id}, name='{self.customer_name}')>"


class Order(Base):
    """Đơn hàng được tạo từ đánh giá (1 đánh giá = 1 đơn hàng)"""
    __tablename__ = "orders"
    
    order_id = Column(BigInteger, primary_key=True, autoincrement=True)
    customer_id = Column(BigInteger, ForeignKey("customers.customer_id"), nullable=False)
    review_id = Column(BigInteger, ForeignKey("reviews.review_id"), unique=True, nullable=False)  # Ngăn chặn đơn hàng trùng lặp
    order_date = Column(DateTime(timezone=True), nullable=False)
    total_amount = Column(DECIMAL(12, 2))
    status = Column(String(50), default='completed')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Quan hệ
    customer = relationship("Customer", back_populates="orders")
    review = relationship("Review")
    order_lines = relationship("OrderLine", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order(id={self.order_id}, customer_id={self.customer_id}, review_id={self.review_id})>"


class OrderLine(Base):
    """Các mục trong đơn hàng"""
    __tablename__ = "order_lines"
    
    order_line_id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(BigInteger, ForeignKey("orders.order_id"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(DECIMAL(12, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Quan hệ
    order = relationship("Order", back_populates="order_lines")
    product = relationship("Product")
    
    def __repr__(self):
        return f"<OrderLine(id={self.order_line_id}, order_id={self.order_id}, product_id={self.product_id})>"


class CrawlLog(Base):
    """Nhật ký thực thi crawler để giám sát"""
    __tablename__ = "crawl_logs"
    
    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    crawler_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    items_crawled = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    
    def __repr__(self):
        return f"<CrawlLog(id={self.log_id}, type='{self.crawler_type}', status='{self.status}')>"
