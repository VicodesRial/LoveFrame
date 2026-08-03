"""Temporary message-only command-line entry point for Phases A and B."""

from __future__ import annotations

import argparse
from datetime import datetime, time
from pathlib import Path
from typing import Optional, Sequence

from app.config import DEFAULT_CONFIG_PATH, load_config
from app.message_scheduler import get_daily_message


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print the current LoveFrame daily message.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="optional local configuration file",
    )
    parser.add_argument("--messages", type=Path, help="override the configured message file")
    parser.add_argument("--at", type=datetime.fromisoformat, help="ISO timestamp for testing")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the Phase A/B message CLI."""

    args = _parser().parse_args(argv)
    config = load_config(args.config)
    message_path = args.messages or config.message_path
    print(
        get_daily_message(
            message_path,
            now=args.at,
            timezone_name=config.timezone_name,
            rollover_time=time(config.rollover_hour),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
