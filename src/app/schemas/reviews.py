"""
Review schemas
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class ReviewBase(BaseModel):
    """Base review schema"""
    product_id: int = Field(..., description="Product ID")
    user_name: Optional[str] = Field(None, max_length=255, description="Reviewer name")
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5 stars)")
    comment: Optional[str] = Field(None, description="Review comment")
    has_images: bool = Field(False, description="Whether review has images")
    helpful_count: int = Field(0, ge=0, description="Helpful vote count")
    created_at: datetime = Field(..., description="Review creation date")
    
    @validator('rating')
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v
    
    class Config:
        from_attributes = True


class ReviewCreate(ReviewBase):
    """Schema for creating a new review"""
    pass


class ReviewInDB(ReviewBase):
    """Schema for review in database"""
    review_id: int
    crawled_at: datetime
    
    class Config:
        from_attributes = True


class ReviewInKafka(ReviewBase):
    """Schema for review message in Kafka"""
    kafka_timestamp: datetime = Field(default_factory=datetime.utcnow)
    crawled_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewWithSentiment(ReviewInDB):
    """Schema for review with sentiment analysis"""
    sentiment: Optional[str] = Field(None, description="Sentiment (positive, negative, neutral)")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Confidence score")
    
    @validator('sentiment')
    def validate_sentiment(cls, v):
        if v is not None and v not in ['positive', 'negative', 'neutral']:
            raise ValueError('Sentiment must be positive, negative, or neutral')
        return v
