"""LoveFrame command-line entry point."""

from __future__ import annotations

import argparse
import logging
import signal
from dataclasses import replace
from datetime import datetime, time
from pathlib import Path
from typing import Optional, Sequence

from app.config import AppConfig, DEFAULT_CONFIG_PATH, load_config
from app.logging_config import configure_application_logging, log_startup_selection
from app.message_scheduler import get_daily_message

LOGGER = logging.getLogger(__name__)


def run_display(config: AppConfig) -> int:
    """Import Pygame only when launching the visual interface."""

    from app.ui import run_display as start_display

    return start_display(config)


def _positive_dimension(value: str) -> int:
    dimension = int(value)
    if dimension <= 0:
        raise argparse.ArgumentTypeError("display dimensions must be positive")
    return dimension


def _request_clean_shutdown(signum, frame) -> None:
    """Turn a process termination signal into normal Python stack unwinding."""

    raise KeyboardInterrupt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the LoveFrame photo display.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="optional local configuration file",
    )
    parser.add_argument("--messages", type=Path, help="override the configured message file")
    parser.add_argument("--photos", type=Path, help="override the configured photo directory")
    parser.add_argument("--width", type=_positive_dimension, help="override display width")
    parser.add_argument("--height", type=_positive_dimension, help="override display height")
    parser.add_argument(
        "--print-message",
        action="store_true",
        help="print the current message instead of opening the display",
    )
    parser.add_argument(
        "--at",
        type=datetime.fromisoformat,
        help="ISO timestamp used with --print-message",
    )
    display_mode = parser.add_mutually_exclusive_group()
    display_mode.add_argument(
        "--fullscreen",
        action="store_true",
        help="run borderless fullscreen on the Raspberry Pi",
    )
    display_mode.add_argument(
        "--windowed",
        action="store_true",
        help="force windowed development mode",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the display or the message diagnostic command."""

    parser = _parser()
    args = parser.parse_args(argv)
    configure_application_logging()
    config = load_config(args.config)
    config = replace(
        config,
        width=args.width or config.width,
        height=args.height or config.height,
        message_path=args.messages or config.message_path,
        photo_path=args.photos or config.photo_path,
        fullscreen=(
            True if args.fullscreen else False if args.windowed else config.fullscreen
        ),
    )

    mode = "message diagnostic" if args.print_message else (
        "fullscreen" if config.fullscreen else "windowed"
    )
    log_startup_selection(
        LOGGER,
        mode=mode,
        config_path=args.config,
        message_path=config.message_path,
        photo_path=config.photo_path,
    )

    if args.print_message:
        print(
            get_daily_message(
                config.message_path,
                now=args.at,
                timezone_name=config.timezone_name,
                rollover_time=time(config.rollover_hour),
            )
        )
        LOGGER.info("LoveFrame message diagnostic finished")
        return 0
    if args.at is not None:
        parser.error("--at requires --print-message")
    previous_sigterm_handler = signal.signal(signal.SIGTERM, _request_clean_shutdown)
    try:
        exit_status = run_display(config)
    except KeyboardInterrupt:
        LOGGER.info("LoveFrame termination requested")
        exit_status = 0
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm_handler)
    LOGGER.info("LoveFrame shutdown complete (status=%d)", exit_status)
    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
