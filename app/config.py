"""Configuration loading for LoveFrame."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = Path("config/config.local.json")


@dataclass(frozen=True)
class AppConfig:
    """Validated application settings with resource-conscious defaults."""

    width: int = 1024
    height: int = 600
    fullscreen: bool = False
    slideshow_interval_seconds: int = 15
    message_path: Path = Path("data/messages.example.json")
    timezone_name: str = "America/New_York"
    rollover_hour: int = 8


def _mapping(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _positive_int(value: Any, default: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return default


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Load optional local configuration, retaining safe defaults for invalid fields."""

    path = Path(path)
    if not path.exists():
        return AppConfig()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        LOGGER.warning("Could not load configuration from %s: %s", path, type(error).__name__)
        return AppConfig()

    if not isinstance(raw, dict):
        LOGGER.warning("Ignoring configuration with a non-object root: %s", path)
        return AppConfig()

    defaults = AppConfig()
    display = _mapping(raw.get("display"))
    slideshow = _mapping(raw.get("slideshow"))
    messages = _mapping(raw.get("messages"))

    fullscreen_value = display.get("fullscreen", defaults.fullscreen)
    fullscreen = fullscreen_value if isinstance(fullscreen_value, bool) else defaults.fullscreen

    message_path_value = messages.get("path")
    message_path = (
        Path(message_path_value)
        if isinstance(message_path_value, str) and message_path_value.strip()
        else defaults.message_path
    )

    timezone_value = messages.get("timezone")
    timezone_name = defaults.timezone_name
    if isinstance(timezone_value, str) and timezone_value.strip():
        try:
            ZoneInfo(timezone_value)
        except ZoneInfoNotFoundError:
            LOGGER.warning("Ignoring unknown configured timezone")
        else:
            timezone_name = timezone_value

    rollover_value = messages.get("rollover_hour", defaults.rollover_hour)
    rollover_hour = (
        rollover_value
        if isinstance(rollover_value, int)
        and not isinstance(rollover_value, bool)
        and 0 <= rollover_value <= 23
        else defaults.rollover_hour
    )

    return AppConfig(
        width=_positive_int(display.get("width"), defaults.width),
        height=_positive_int(display.get("height"), defaults.height),
        fullscreen=fullscreen,
        slideshow_interval_seconds=_positive_int(
            slideshow.get("interval_seconds"), defaults.slideshow_interval_seconds
        ),
        message_path=message_path,
        timezone_name=timezone_name,
        rollover_hour=rollover_hour,
    )
