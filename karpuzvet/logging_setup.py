from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from karpuzvet.database import DEFAULT_APP_DIR


DEFAULT_LOG_DIR = DEFAULT_APP_DIR / "logs"


def get_log_paths(log_dir: Path | str = DEFAULT_LOG_DIR) -> tuple[Path, Path]:
    base_dir = Path(log_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    return base_dir / f"app-{stamp}.log", base_dir / f"errors-{stamp}.log"


def configure_logging(log_dir: Path | str = DEFAULT_LOG_DIR) -> tuple[Path, Path]:
    app_log, error_log = get_log_paths(log_dir)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    info_handler = logging.FileHandler(app_log, encoding="utf-8")
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    error_handler = logging.FileHandler(error_log, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    root_logger.addHandler(info_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(stream_handler)
    return app_log, error_log
