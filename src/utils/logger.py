"""
Logging configuration for the application.
"""

import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO", log_file: str = "scanlation_tool.log") -> None:
    """
    Configure application-wide logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
    """
    # Create logs directory if needed
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True)
    
    # Configure root logger
    from logging.handlers import RotatingFileHandler
    
    # 5MB max size, 3 backup files
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    stream_handler = logging.StreamHandler(sys.stdout)
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[file_handler, stream_handler]
    )
    
    # Reduce verbosity of some noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.INFO)
    logging.getLogger("PySide6").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    """
    return logging.getLogger(name)