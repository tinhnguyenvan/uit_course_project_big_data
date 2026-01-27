"""
Logging utilities
"""
import logging
import sys
from pathlib import Path
from ..config import config


def setup_logger(
    name: str,
    log_file: str = None,
    level: str = None,
    console: bool = True
) -> logging.Logger:
    """
    Setup logger with file and console handlers
    
    Args:
        name: Logger name
        log_file: Log file path (relative to logs directory)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console: Whether to add console handler
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    # Set level
    log_level = getattr(logging, level or config.LOG_LEVEL)
    logger.setLevel(log_level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(config.LOG_FORMAT)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(config.LOGS_DIR / log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get existing logger or create new one
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
