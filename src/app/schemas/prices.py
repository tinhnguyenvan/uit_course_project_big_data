"""
Product price schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ProductPriceBase(BaseModel):
    """Base product price schema"""
    product_id: int = Field(..., description="Product ID")
    price: Decimal = Field(..., ge=0, description="Current price")
    original_price: Optional[Decimal] = Field(None, ge=0, description="Original price")
    discount_percent: Optional[int] = Field(None, ge=0, le=100, description="Discount percentage")
    stock_available: Optional[int] = Field(None, ge=0, description="Stock quantity")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Price timestamp")
    
    class Config:
        from_attributes = True


class ProductPriceCreate(ProductPriceBase):
    """Schema for creating a new price record"""
    pass


class ProductPriceInDB(ProductPriceBase):
    """Schema for price in database"""
    
    class Config:
        from_attributes = True
