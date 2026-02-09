import logging
import sys

def get_logger(name: str):
    logger = logging.getLogger(name)

    # Avoid duplicate handlers (Uvicorn already adds one)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Inherit Uvicorn’s log level (prevents mismatch)
    logger.setLevel(logging.getLogger("uvicorn").level or logging.INFO)

    # Prevent double propagation to root handler
    logger.propagate = False

    return logger
