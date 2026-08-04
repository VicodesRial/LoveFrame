"""Bounded, privacy-conscious application logging for LoveFrame."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, TextIO, Union

LOG_FILENAME = "loveframe.log"
MAX_LOG_BYTES = 1_048_576
LOG_BACKUP_COUNT = 3
LOG_DIRECTORY_ENV = "LOVEFRAME_LOG_DIR"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_MANAGED_HANDLER_ATTRIBUTE = "_loveframe_managed_handler"


def default_log_directory() -> Path:
    """Return the configured log directory or a safe project-local default."""

    configured = os.environ.get(LOG_DIRECTORY_ENV)
    if configured:
        return Path(configured).expanduser()
    return Path.cwd() / "logs"


def safe_path_label(path: Union[Path, str]) -> str:
    """Return only the final path component for privacy-safe status logging."""

    name = Path(path).name
    return name or "<project-root>"


def log_startup_selection(
    logger: logging.Logger,
    *,
    mode: str,
    config_path: Union[Path, str],
    message_path: Union[Path, str],
    photo_path: Union[Path, str],
) -> None:
    """Log startup mode and filename-only content locations."""

    logger.info("Starting LoveFrame in %s mode", mode)
    logger.info(
        "Selected content: config=%s messages=%s photos=%s",
        safe_path_label(config_path),
        safe_path_label(message_path),
        safe_path_label(photo_path),
    )


def _is_managed(handler: logging.Handler, kind: str) -> bool:
    return getattr(handler, _MANAGED_HANDLER_ATTRIBUTE, None) == kind


def _mark_managed(handler: logging.Handler, kind: str) -> None:
    setattr(handler, _MANAGED_HANDLER_ATTRIBUTE, kind)


def configure_application_logging(
    log_directory: Optional[Path] = None,
    *,
    stream: Optional[TextIO] = sys.stderr,
) -> Optional[Path]:
    """Configure one rotating file and optional console handler without failing startup."""

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)
    directory = Path(log_directory) if log_directory is not None else default_log_directory()
    log_path = directory / LOG_FILENAME

    existing_files = [
        handler for handler in root_logger.handlers if _is_managed(handler, "file")
    ]
    matching_file = next(
        (
            handler
            for handler in existing_files
            if Path(getattr(handler, "baseFilename", "")) == log_path.absolute()
        ),
        None,
    )

    if matching_file is None:
        for handler in existing_files:
            root_logger.removeHandler(handler)
            handler.close()
        try:
            directory.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=MAX_LOG_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
        except (OSError, ValueError) as error:
            print(
                "LoveFrame warning: file logging is unavailable "
                f"({type(error).__name__}); continuing without it.",
                file=sys.stderr,
            )
            log_path = None
        else:
            file_handler.setFormatter(formatter)
            _mark_managed(file_handler, "file")
            root_logger.addHandler(file_handler)

    if stream is not None and not any(
        _is_managed(handler, "stream") for handler in root_logger.handlers
    ):
        stream_handler = logging.StreamHandler(stream)
        stream_handler.setFormatter(formatter)
        _mark_managed(stream_handler, "stream")
        root_logger.addHandler(stream_handler)

    return log_path
