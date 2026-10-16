import logging

from src.config.logging_config import configure_logging

configure_logging()

logger = logging.getLogger("rag01.test")

logger.debug("Debug message")
logger.info("Logging configuration works")
logger.warning("This is a test warning")
logger.error("This is a test error")