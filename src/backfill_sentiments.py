"""
Script backfill sentiment analysis cho reviews đã tồn tại
Dùng để phân tích cảm xúc cho các reviews được tạo trước khi có sentiment pipeline
"""
import json
import logging
import argparse
from confluent_kafka import Producer

from app.models import SessionLocal, Review, ReviewSentiment
from app.config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backfill_sentiments(batch_size: int = 1000, limit: int = None, dry_run: bool = False):
    """
    Push các reviews chưa có sentiment analysis vào Kafka topic
    
    Args:
        batch_size: Số lượng reviews xử lý mỗi batch
        limit: Giới hạn tổng số reviews (None = all)
        dry_run: Chỉ đếm, không push
    """
    db = SessionLocal()
    
    try:
        # Query reviews chưa có sentiment
        logger.info("Querying reviews without sentiment...")
        
        subquery = db.query(ReviewSentiment.review_id).subquery()
        query = db.query(Review).filter(
            ~Review.review_id.in_(subquery)
        )
        
        if limit:
            query = query.limit(limit)
        
        total_reviews = query.count()
        logger.info(f"Found {total_reviews:,} reviews without sentiment analysis")
        
        if dry_run:
            logger.info("Dry run mode - no messages will be sent")
            return
        
        # Setup Kafka producer
        producer = Producer({
            'bootstrap.servers': config.KAFKA_BOOTSTRAP_SERVERS,
            'acks': 'all',
            'retries': 3
        })
        
        processed = 0
        failed = 0
        
        # Xử lý theo batch
        while True:
            reviews = query.offset(processed).limit(batch_size).all()
            
            if not reviews:
                break
            
            logger.info(f"Processing batch {processed // batch_size + 1}: {len(reviews)} reviews")
            
            for review in reviews:
                try:
                    message = {
                        'review_id': review.review_id,
                        'product_id': review.product_id,
                        'comment': review.comment or '',
                        'rating': review.rating,
                        'created_at': review.created_at.isoformat() if review.created_at else None
                    }
                    
                    producer.produce(
                        config.KAFKA_TOPIC_SENTIMENT_ANALYSIS,
                        key=str(review.review_id).encode('utf-8'),
                        value=json.dumps(message).encode('utf-8')
                    )
                    
                    processed += 1
                    
                    if processed % 100 == 0:
                        logger.info(f"Progress: {processed:,}/{total_reviews:,} ({processed/total_reviews*100:.1f}%)")
                        producer.flush()
                
                except Exception as e:
                    logger.error(f"Failed to push review {review.review_id}: {e}")
                    failed += 1
            
            # Flush sau mỗi batch
            producer.flush()
        
        logger.info("=" * 60)
        logger.info(f"✅ Backfill completed!")
        logger.info(f"   Total reviews: {total_reviews:,}")
        logger.info(f"   Successfully pushed: {processed:,}")
        logger.info(f"   Failed: {failed:,}")
        logger.info(f"   Topic: {config.KAFKA_TOPIC_SENTIMENT_ANALYSIS}")
        logger.info("=" * 60)
        logger.info(f"⏳ SentimentConsumer sẽ xử lý các messages này")
        logger.info(f"   Ước tính thời gian: ~{processed / 200:.0f} phút (200 reviews/min)")
        
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        raise
    
    finally:
        db.close()


def check_sentiment_coverage():
    """Kiểm tra tỷ lệ reviews đã có sentiment"""
    db = SessionLocal()
    
    try:
        total_reviews = db.query(Review).count()
        total_sentiments = db.query(ReviewSentiment).count()
        
        coverage = (total_sentiments / total_reviews * 100) if total_reviews > 0 else 0
        
        logger.info("=" * 60)
        logger.info("📊 Sentiment Analysis Coverage")
        logger.info("=" * 60)
        logger.info(f"Total reviews: {total_reviews:,}")
        logger.info(f"Reviews with sentiment: {total_sentiments:,}")
        logger.info(f"Reviews without sentiment: {total_reviews - total_sentiments:,}")
        logger.info(f"Coverage: {coverage:.2f}%")
        logger.info("=" * 60)
        
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backfill sentiment analysis cho reviews')
    parser.add_argument('--batch-size', type=int, default=1000, help='Số reviews mỗi batch')
    parser.add_argument('--limit', type=int, help='Giới hạn tổng số reviews')
    parser.add_argument('--dry-run', action='store_true', help='Chỉ đếm, không push')
    parser.add_argument('--check', action='store_true', help='Kiểm tra coverage hiện tại')
    
    args = parser.parse_args()
    
    if args.check:
        check_sentiment_coverage()
    else:
        logger.info("🚀 Starting sentiment backfill...")
        backfill_sentiments(
            batch_size=args.batch_size,
            limit=args.limit,
            dry_run=args.dry_run
        )
