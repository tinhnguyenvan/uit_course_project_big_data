"""
Shop schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ShopBase(BaseModel):
    """Base shop schema"""
    shop_id: int = Field(..., description="Shop ID from Tiki")
    shop_name: str = Field(..., min_length=1, max_length=255, description="Shop name")
    rating: Optional[Decimal] = Field(None, ge=0, le=5, description="Shop rating")
    response_rate: Optional[int] = Field(None, ge=0, le=100, description="Response rate %")
    follower_count: Optional[int] = Field(None, ge=0, description="Number of followers")
    is_official: bool = Field(False, description="Is official Tiki shop")
    
    class Config:
        from_attributes = True


class ShopCreate(ShopBase):
    """Schema for creating a new shop"""
    pass


class ShopInDB(ShopBase):
    """Schema for shop in database"""
    created_at: datetime
    last_updated: datetime
    
    class Config:
        from_attributes = True
