"""
Scrapy middlewares for Tiki crawler
"""
from scrapy import signals
import random
import logging

logger = logging.getLogger(__name__)


class TikiSpiderMiddleware:
    """Spider middleware for Tiki crawler"""
    
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s
    
    def process_spider_input(self, response, spider):
        return None
    
    def process_spider_output(self, response, result, spider):
        for i in result:
            yield i
    
    def process_spider_exception(self, response, exception, spider):
        logger.error(f"Spider exception: {exception}")
    
    def spider_opened(self, spider):
        logger.info(f'Spider opened: {spider.name}')


class TikiDownloaderMiddleware:
    """Downloader middleware for Tiki crawler"""
    
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]
    
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s
    
    def process_request(self, request, spider):
        # Rotate User-Agent
        request.headers['User-Agent'] = random.choice(self.USER_AGENTS)
        return None
    
    def process_response(self, request, response, spider):
        return response
    
    def process_exception(self, request, exception, spider):
        logger.error(f"Download exception: {exception}")
    
    def spider_opened(self, spider):
        logger.info(f'Downloader middleware opened for: {spider.name}')
