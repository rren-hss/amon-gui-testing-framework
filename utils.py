import sys
import logging
from datetime import datetime
from run_context import(
    LOG_PATH,
    initialize_run_directories,
)

def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def setup_logging():
    initialize_run_directories()

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
    logging.getLogger("paramiko").setLevel(
    logging.WARNING
    )

    logging.info("=" * 60)
    logging.info("Test Runner started")
    logging.info("=" * 60)
