from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logger(log_dir: Path, run_timestamp: str) -> logging.Logger:
    logger = logging.getLogger("job_listings_automation")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    log_file = log_dir / f"job_listings_{run_timestamp}.log"
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
