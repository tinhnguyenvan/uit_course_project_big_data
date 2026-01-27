"""
Category schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CategoryBase(BaseModel):
    """Base category schema"""
    category_name: str = Field(..., min_length=1, max_length=255, description="Category name")
    parent_id: Optional[int] = Field(None, description="Parent category ID")
    
    class Config:
        from_attributes = True


class CategoryCreate(CategoryBase):
    """Schema for creating a new category"""
    pass


class CategoryInDB(CategoryBase):
    """Schema for category in database"""
    category_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
