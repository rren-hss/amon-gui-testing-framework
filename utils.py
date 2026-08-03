import sys
import os
import logging
from datetime import datetime
from config import LOG_PATH

def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def setup_logging():
    log_directory = os.path.dirname(LOG_PATH)

    if log_directory:
        os.makedirs(log_directory, exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(
                LOG_PATH,
                mode="w",
                encoding="utf-8",
            ),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

    logging.info("=" * 60)
    logging.info("Test Runner started")
    logging.info("=" * 60)
