from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_file: str = "product_generator.log", level: int = logging.INFO) -> None:
    """Configure root logging once for file + console output."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
