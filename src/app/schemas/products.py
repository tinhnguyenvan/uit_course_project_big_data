"""
Product schemas
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ProductBase(BaseModel):
    """Base product schema"""
    product_id: int = Field(..., description="Product ID from Tiki")
    name: str = Field(..., min_length=1, max_length=1000, description="Product name")
    shop_id: int = Field(..., description="Shop ID")
    category_id: Optional[int] = Field(None, description="Category ID")
    url: str = Field(..., description="Product URL")
    image_url: Optional[str] = Field(None, description="Main image URL")
    description: Optional[str] = Field(None, description="Product description")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Average rating (0-5)")
    sold_count: Optional[int] = Field(0, ge=0, description="Number of items sold")
    
    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and (v < 0 or v > 5):
            raise ValueError('Rating must be between 0 and 5')
        return v
    
    class Config:
        from_attributes = True


class ProductCreate(ProductBase):
    """Schema for creating a new product"""
    pass


class ProductInDB(ProductBase):
    """Schema for product in database"""
    first_seen: datetime
    last_updated: datetime
    
    class Config:
        from_attributes = True


class ProductInKafka(ProductBase):
    """Schema for product message in Kafka"""
    kafka_timestamp: datetime = Field(default_factory=datetime.utcnow)
    crawled_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Optional price information
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    discount_percent: Optional[int] = None
    stock_available: Optional[int] = None
