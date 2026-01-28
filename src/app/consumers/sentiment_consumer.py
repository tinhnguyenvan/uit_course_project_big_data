"""
Sentiment Analysis Consumer - Phân tích cảm xúc đánh giá bằng PhoBERT
"""
import logging
import json
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import warnings

from .base_consumer import BaseConsumer
from ..models import SessionLocal, ReviewSentiment, Review
from ..config import config

# Tắt warnings từ transformers
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    Lớp phân tích cảm xúc sử dụng PhoBERT/ViSoBERT
    
    Model: uitnlp/visobert - Vietnamese Sentiment BERT
    - positive: Tích cực
    - negative: Tiêu cực
    - neutral: Trung lập (nếu có)
    """
    
    def __init__(self, model_name: str = None, device: str = None):
        """
        Khởi tạo model phân tích cảm xúc
        
        Args:
            model_name: Tên model từ HuggingFace (mặc định: uitnlp/visobert)
            device: 'cpu' hoặc 'cuda' (mặc định: cpu)
        """
        self.model_name = model_name or config.SENTIMENT_MODEL_NAME
        self.device = device or config.SENTIMENT_DEVICE
        self.max_length = config.SENTIMENT_MAX_LENGTH
        
        logger.info(f"Loading sentiment model: {self.model_name} on {self.device}")
        
        try:
            # Load tokenizer và model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            
            # Mapping labels
            self.id2label = self.model.config.id2label
            
            # Map model labels to sentiment labels
            # uitnlp/visobert: LABEL_0 = negative, LABEL_1 = positive
            self.label_mapping = {
                'label_0': 'negative',
                'label_1': 'positive',
                'negative': 'negative',
                'positive': 'positive',
                'neutral': 'neutral'
            }
            
            logger.info(f"Model loaded successfully. Labels: {self.id2label}")
            
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise
    
    def analyze(self, text: str) -> dict:
        """
        Phân tích cảm xúc của văn bản
        
        Args:
            text: Văn bản cần phân tích
            
        Returns:
            Dict chứa:
            - sentiment: 'positive', 'negative', hoặc 'neutral'
            - confidence: Độ tin cậy (0-1)
            - scores: Dict với điểm số từng nhãn
        """
        if not text or not text.strip():
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'scores': {}
            }
        
        try:
            # Tokenize
            inputs = self.tokenizer(
                text,
                max_length=self.max_length,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Inference
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                
                # Softmax để có xác suất
                probs = torch.nn.functional.softmax(logits, dim=-1)
                confidence, predicted_class = torch.max(probs, dim=-1)
                
                # Lấy sentiment label
                predicted_label = self.id2label[predicted_class.item()]
                confidence_score = confidence.item()
                
                # Map to standard sentiment labels
                sentiment_label = self.label_mapping.get(
                    predicted_label.lower(), 
                    'neutral'
                )
                
                # Điểm số từng nhãn
                scores = {
                    self.id2label[i]: float(probs[0][i])
                    for i in range(len(self.id2label))
                }
            
            return {
                'sentiment': sentiment_label,  # positive/negative/neutral (mapped)
                'confidence': round(confidence_score, 4),
                'scores': scores
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'scores': {}
            }
    
    def analyze_batch(self, texts: list) -> list:
        """
        Phân tích cảm xúc cho nhiều văn bản (batch processing)
        
        Args:
            texts: Danh sách văn bản
            
        Returns:
            List dict kết quả
        """
        results = []
        batch_size = config.SENTIMENT_BATCH_SIZE
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                inputs = self.tokenizer(
                    batch,
                    max_length=self.max_length,
                    padding='max_length',
                    truncation=True,
                    return_tensors='pt'
                )
                
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits = outputs.logits
                    probs = torch.nn.functional.softmax(logits, dim=-1)
                    confidences, predicted_classes = torch.max(probs, dim=-1)
                
                for idx, (conf, pred_class) in enumerate(zip(confidences, predicted_classes)):
                    predicted_label = self.id2label[pred_class.item()]
                    scores = {
                        self.id2label[j]: float(probs[idx][j])
                        for j in range(len(self.id2label))
                    }
                    
                    results.append({
                        'sentiment': predicted_label.lower(),
                        'confidence': round(conf.item(), 4),
                        'scores': scores
                    })
                    
            except Exception as e:
                logger.error(f"Error in batch analysis: {e}")
                # Fallback cho batch bị lỗi
                results.extend([
                    {'sentiment': 'neutral', 'confidence': 0.0, 'scores': {}}
                    for _ in batch
                ])
        
        return results


class SentimentConsumer(BaseConsumer):
    """Consumer phân tích cảm xúc các đánh giá từ Kafka"""
    
    def __init__(self):
        super().__init__(
            topics=[config.KAFKA_TOPIC_SENTIMENT_ANALYSIS],
            group_id='sentiment-analysis-consumer-group',
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS
        )
        self.db = None
        
        # Khởi tạo sentiment analyzer
        logger.info("Initializing sentiment analyzer...")
        self.analyzer = SentimentAnalyzer()
        logger.info("Sentiment analyzer ready")
    
    def process_sentiment(self, data: dict) -> bool:
        """
        Xử lý message phân tích cảm xúc và lưu vào database
        
        Args:
            data: Dữ liệu review từ Kafka {review_id, product_id, comment, rating}
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        self.db = SessionLocal()
        
        try:
            review_id = data.get('review_id')
            comment = data.get('comment', '')
            rating = data.get('rating', 0)
            
            if not review_id:
                logger.error("Missing review_id in sentiment message")
                return False
            
            # Kiểm tra review tồn tại
            review = self.db.query(Review).filter_by(review_id=review_id).first()
            if not review:
                logger.warning(f"Review {review_id} not found in database, skipping")
                return False
            
            # Kiểm tra đã phân tích chưa
            existing = self.db.query(ReviewSentiment).filter_by(
                review_id=review_id
            ).first()
            
            if existing:
                logger.debug(f"Sentiment for review {review_id} already exists, skipping")
                return True
            
            # Phân tích cảm xúc
            logger.info(f"Analyzing sentiment for review {review_id}")
            result = self.analyzer.analyze(comment)
            
            sentiment_label = result['sentiment']
            confidence = result['confidence']
            
            # Lưu kết quả vào database
            sentiment_record = ReviewSentiment(
                review_id=review_id,
                sentiment=sentiment_label,
                confidence_score=confidence,
                processed_at=datetime.utcnow()
            )
            
            self.db.add(sentiment_record)
            self.db.commit()
            
            logger.info(
                f"Saved sentiment for review {review_id}: {sentiment_label} "
                f"(confidence: {confidence:.4f}, rating: {rating})"
            )
            
            # Log chi tiết nếu có sự không khớp giữa rating và sentiment
            if rating >= 4 and sentiment_label == 'negative':
                logger.warning(
                    f"Mismatch: Review {review_id} has high rating ({rating}) "
                    f"but negative sentiment. Comment: {comment[:100]}"
                )
            elif rating <= 2 and sentiment_label == 'positive':
                logger.warning(
                    f"Mismatch: Review {review_id} has low rating ({rating}) "
                    f"but positive sentiment. Comment: {comment[:100]}"
                )
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error processing sentiment: {e}")
            self.db.rollback()
            return False
        
        except Exception as e:
            logger.error(f"Error processing sentiment: {e}")
            self.db.rollback()
            return False
        
        finally:
            if self.db:
                self.db.close()
    
    def start(self):
        """Bắt đầu consumer phân tích cảm xúc"""
        logger.info("Starting sentiment analysis consumer...")
        self.consume(self.process_sentiment)


# Standalone runner
if __name__ == '__main__':
    import sys
    
    # Thiết lập logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        consumer = SentimentConsumer()
        consumer.start()
    except KeyboardInterrupt:
        logger.info("Consumer stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        sys.exit(1)
