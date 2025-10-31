"""
Logging utilities for IBTraderMCP
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from src.config import get_config


class Logger:
    """Centralized logging manager"""
    
    _instance = None
    _logger = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup_logger()
        return cls._instance
    
    def _setup_logger(self):
        """Setup logging configuration"""
        config = get_config()
        self._logger = logging.getLogger("IBTraderMCP")
        self._logger.setLevel(getattr(logging, config.log_level))
        
        # Remove existing handlers
        self._logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.log_level))
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self._logger.addHandler(console_handler)
        
        # File handler
        log_dir = config.log_dir
        log_file = log_dir / f"IBTraderMCP_{datetime.now().strftime('%Y%m%d')}.log"
        if True:  # Always log to file
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(getattr(logging, config.log_level))
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self._logger.addHandler(file_handler)
    
    def debug(self, message: str):
        """Log debug message"""
        self._logger.debug(message)
    
    def info(self, message: str):
        """Log info message"""
        self._logger.info(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self._logger.warning(message)
    
    def error(self, message: str):
        """Log error message"""
        self._logger.error(message)
    
    def critical(self, message: str):
        """Log critical message"""
        self._logger.critical(message)


# Global logger instance
logger = Logger()
