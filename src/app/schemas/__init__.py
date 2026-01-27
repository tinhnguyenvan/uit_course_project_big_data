"""
Pydantic schemas for data validation
"""
from .products import ProductBase, ProductCreate, ProductInDB, ProductInKafka
from .reviews import ReviewBase, ReviewCreate, ReviewInDB, ReviewInKafka, ReviewWithSentiment
from .shops import ShopBase, ShopCreate, ShopInDB
from .categories import CategoryBase, CategoryCreate, CategoryInDB
from .prices import ProductPriceBase, ProductPriceCreate, ProductPriceInDB

__all__ = [
    'ProductBase', 'ProductCreate', 'ProductInDB', 'ProductInKafka',
    'ReviewBase', 'ReviewCreate', 'ReviewInDB', 'ReviewInKafka', 'ReviewWithSentiment',
    'ShopBase', 'ShopCreate', 'ShopInDB',
    'CategoryBase', 'CategoryCreate', 'CategoryInDB',
    'ProductPriceBase', 'ProductPriceCreate', 'ProductPriceInDB'
]
