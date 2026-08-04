"""Configuration loading for LoveFrame."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.logging_config import safe_path_label

LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = Path("config/config.local.json")
DEFAULT_PHOTO_FIT = "contain_color"
PHOTO_FIT_MODES = frozenset({DEFAULT_PHOTO_FIT, "contain_blur", "cover"})
DEFAULT_PHOTO_BACKGROUND_COLOR = "#F8DDE3"
DEFAULT_CARD_BACKGROUND_COLOR = "#EFAFBD"
DEFAULT_TEXT_COLOR = "#4A2532"
DEFAULT_CLOCK_COLOR = "#4A2532"
DEFAULT_CARD_OPACITY = 225
DEFAULT_DECORATION_STYLE = "pixel_hearts"
DECORATION_STYLES = frozenset({DEFAULT_DECORATION_STYLE})
DEFAULT_HEART_COLOR = "#D85B7B"
DEFAULT_HEART_HIGHLIGHT_COLOR = "#FFF0F4"
DEFAULT_SPARKLE_COLOR = "#C94F70"
DEFAULT_DECORATION_DENSITY = "medium"
INVALID_DECORATION_DENSITY_FALLBACK = "low"
DECORATION_DENSITIES = frozenset({"low", "medium", "high"})
DEFAULT_CLOCK_FORMAT = "12h"
CLOCK_FORMATS = frozenset({DEFAULT_CLOCK_FORMAT, "24h"})
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class AppConfig:
    """Validated application settings with resource-conscious defaults."""

    width: int = 1024
    height: int = 600
    fullscreen: bool = False
    slideshow_interval_seconds: int = 15
    fade_duration_ms: int = 400
    cursor_hide_seconds: int = 3
    frames_per_second: int = 30
    photo_path: Path = Path("assets/photos")
    max_source_pixels: int = 20_000_000
    photo_fit: str = DEFAULT_PHOTO_FIT
    photo_background_color: str = DEFAULT_PHOTO_BACKGROUND_COLOR
    message_path: Path = Path("data/messages.example.json")
    timezone_name: str = "America/New_York"
    rollover_hour: int = 8
    message_poll_seconds: int = 60
    show_clock: bool = True
    clock_format: str = DEFAULT_CLOCK_FORMAT
    clock_font_size: int = 34
    message_font_size: int = 25
    card_background_color: str = DEFAULT_CARD_BACKGROUND_COLOR
    card_opacity: int = DEFAULT_CARD_OPACITY
    text_color: str = DEFAULT_TEXT_COLOR
    clock_color: str = DEFAULT_CLOCK_COLOR
    show_decorations: bool = True
    decoration_style: str = DEFAULT_DECORATION_STYLE
    heart_color: str = DEFAULT_HEART_COLOR
    heart_highlight_color: str = DEFAULT_HEART_HIGHLIGHT_COLOR
    sparkle_color: str = DEFAULT_SPARKLE_COLOR
    animate_decorations: bool = True
    decoration_density: str = DEFAULT_DECORATION_DENSITY


def _mapping(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _positive_int(value: Any, default: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return default


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and minimum <= value <= maximum
    ):
        return value
    return default


def normalize_photo_fit(value: Any) -> str:
    """Return a supported photo-fit mode or the safe default."""

    return value if isinstance(value, str) and value in PHOTO_FIT_MODES else DEFAULT_PHOTO_FIT


def normalize_clock_format(value: Any) -> str:
    """Return a supported clock format or the safe 12-hour default."""

    return value if isinstance(value, str) and value in CLOCK_FORMATS else DEFAULT_CLOCK_FORMAT


def normalize_decoration_style(value: Any) -> str:
    """Return a supported decoration style or the pixel-heart default."""

    if isinstance(value, str) and value in DECORATION_STYLES:
        return value
    return DEFAULT_DECORATION_STYLE


def normalize_decoration_density(value: Any) -> str:
    """Return a supported decoration density or the safe sparse fallback."""

    if isinstance(value, str) and value in DECORATION_DENSITIES:
        return value
    return INVALID_DECORATION_DENSITY_FALLBACK


def normalize_hex_color(value: Any, default: str) -> str:
    """Return a normalized six-digit hex color or its documented default."""

    if isinstance(value, str) and HEX_COLOR_PATTERN.fullmatch(value):
        return value.upper()
    return default


def hex_color_to_rgb(value: str) -> tuple[int, int, int]:
    """Convert a validated six-digit hex color to an RGB tuple."""

    normalized = normalize_hex_color(value, "#000000")
    return tuple(int(normalized[index : index + 2], 16) for index in (1, 3, 5))


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Load optional local configuration, retaining safe defaults for invalid fields."""

    path = Path(path)
    if not path.exists():
        return AppConfig()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        LOGGER.warning(
            "Could not load configuration from %s: %s",
            safe_path_label(path),
            type(error).__name__,
        )
        return AppConfig()

    if not isinstance(raw, dict):
        LOGGER.warning(
            "Ignoring configuration with a non-object root: %s",
            safe_path_label(path),
        )
        return AppConfig()

    defaults = AppConfig()
    display = _mapping(raw.get("display"))
    slideshow = _mapping(raw.get("slideshow"))
    photos = _mapping(raw.get("photos"))
    messages = _mapping(raw.get("messages"))
    decorations = _mapping(raw.get("decorations"))

    fullscreen_value = display.get("fullscreen", defaults.fullscreen)
    fullscreen = fullscreen_value if isinstance(fullscreen_value, bool) else defaults.fullscreen

    message_path_value = messages.get("path")
    message_path = (
        Path(message_path_value)
        if isinstance(message_path_value, str) and message_path_value.strip()
        else defaults.message_path
    )

    photo_path_value = photos.get("path")
    photo_path = (
        Path(photo_path_value)
        if isinstance(photo_path_value, str) and photo_path_value.strip()
        else defaults.photo_path
    )

    timezone_value = messages.get("timezone")
    timezone_name = defaults.timezone_name
    if isinstance(timezone_value, str) and timezone_value.strip():
        normalized_timezone = timezone_value.strip()
        try:
            ZoneInfo(normalized_timezone)
        except (ZoneInfoNotFoundError, ValueError):
            LOGGER.warning("Ignoring unknown configured timezone")
        else:
            timezone_name = normalized_timezone

    rollover_value = messages.get("rollover_hour", defaults.rollover_hour)
    rollover_hour = (
        rollover_value
        if isinstance(rollover_value, int)
        and not isinstance(rollover_value, bool)
        and 0 <= rollover_value <= 23
        else defaults.rollover_hour
    )
    show_clock_value = messages.get("show_clock", defaults.show_clock)
    show_clock = (
        show_clock_value if isinstance(show_clock_value, bool) else defaults.show_clock
    )
    show_decorations_value = decorations.get(
        "show_decorations", defaults.show_decorations
    )
    show_decorations = (
        show_decorations_value
        if isinstance(show_decorations_value, bool)
        else defaults.show_decorations
    )
    animate_decorations_value = decorations.get(
        "animate_decorations", defaults.animate_decorations
    )
    animate_decorations = (
        animate_decorations_value
        if isinstance(animate_decorations_value, bool)
        else defaults.animate_decorations
    )

    return AppConfig(
        width=_positive_int(display.get("width"), defaults.width),
        height=_positive_int(display.get("height"), defaults.height),
        fullscreen=fullscreen,
        slideshow_interval_seconds=_bounded_int(
            slideshow.get("interval_seconds"),
            defaults.slideshow_interval_seconds,
            10,
            20,
        ),
        fade_duration_ms=_bounded_int(
            slideshow.get("fade_duration_ms"), defaults.fade_duration_ms, 0, 2_000
        ),
        cursor_hide_seconds=_bounded_int(
            display.get("cursor_hide_seconds"), defaults.cursor_hide_seconds, 1, 60
        ),
        frames_per_second=_bounded_int(
            display.get("frames_per_second"), defaults.frames_per_second, 10, 60
        ),
        photo_path=photo_path,
        max_source_pixels=_positive_int(
            photos.get("max_source_pixels"), defaults.max_source_pixels
        ),
        photo_fit=normalize_photo_fit(photos.get("photo_fit")),
        photo_background_color=normalize_hex_color(
            photos.get("photo_background_color"),
            defaults.photo_background_color,
        ),
        message_path=message_path,
        timezone_name=timezone_name,
        rollover_hour=rollover_hour,
        message_poll_seconds=_bounded_int(
            messages.get("poll_seconds"), defaults.message_poll_seconds, 10, 3_600
        ),
        show_clock=show_clock,
        clock_format=normalize_clock_format(messages.get("clock_format")),
        clock_font_size=_bounded_int(
            messages.get("clock_font_size"), defaults.clock_font_size, 10, 96
        ),
        message_font_size=_bounded_int(
            messages.get("message_font_size"), defaults.message_font_size, 16, 72
        ),
        card_background_color=normalize_hex_color(
            messages.get("card_background_color"),
            defaults.card_background_color,
        ),
        card_opacity=_bounded_int(
            messages.get("card_opacity"), defaults.card_opacity, 0, 255
        ),
        text_color=normalize_hex_color(
            messages.get("text_color"), defaults.text_color
        ),
        clock_color=normalize_hex_color(
            messages.get("clock_color"), defaults.clock_color
        ),
        show_decorations=show_decorations,
        decoration_style=normalize_decoration_style(
            decorations.get("decoration_style")
        ),
        heart_color=normalize_hex_color(
            decorations.get("heart_color"), defaults.heart_color
        ),
        heart_highlight_color=normalize_hex_color(
            decorations.get("heart_highlight_color"),
            defaults.heart_highlight_color,
        ),
        sparkle_color=normalize_hex_color(
            decorations.get("sparkle_color"), defaults.sparkle_color
        ),
        animate_decorations=animate_decorations,
        decoration_density=normalize_decoration_density(
            decorations.get("decoration_density")
        ),
    )
