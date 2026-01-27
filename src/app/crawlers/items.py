"""
Scrapy items definition
"""
import scrapy
from scrapy.item import Item, Field


class ProductItem(scrapy.Item):
    """Product item"""
    item_type = Field(default='product')
    product_id = Field()
    name = Field()
    shop_id = Field()
    category_id = Field()
    url = Field()
    image_url = Field()
    description = Field()
    rating = Field()
    sold_count = Field()
    
    # Price information
    price = Field()
    original_price = Field()
    discount_percent = Field()
    stock_available = Field()
    
    # Metadata
    crawled_at = Field()
    kafka_timestamp = Field()


class ReviewItem(scrapy.Item):
    """Review item"""
    item_type = Field(default='review')
    product_id = Field()
    user_name = Field()
    rating = Field()
    comment = Field()
    has_images = Field()
    helpful_count = Field()
    created_at = Field()
    
    # Metadata
    crawled_at = Field()
    kafka_timestamp = Field()


class ShopItem(scrapy.Item):
    """Shop item"""
    item_type = Field(default='shop')
    shop_id = Field()
    shop_name = Field()
    rating = Field()
    response_rate = Field()
    follower_count = Field()
    is_official = Field()
    
    # Metadata
    crawled_at = Field()
