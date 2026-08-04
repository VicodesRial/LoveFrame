import json
import logging
from pathlib import Path

import pytest

from app.config import AppConfig, load_config


@pytest.mark.parametrize(
    "timezone_value",
    [
        "/bad-zone",
        "../UTC",
        "./UTC",
        "America/../UTC",
        "Mars/Olympus",
    ],
)
def test_invalid_timezone_uses_private_safe_default(
    tmp_path: Path,
    caplog,
    timezone_value: str,
) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"messages": {"timezone": timezone_value}}),
        encoding="utf-8",
    )

    with caplog.at_level(logging.WARNING, logger="app.config"):
        config = load_config(path)

    warnings = [record.getMessage() for record in caplog.records if record.name == "app.config"]
    assert config.timezone_name == "America/New_York"
    assert warnings == ["Ignoring unknown configured timezone"]
    assert timezone_value not in caplog.text


@pytest.mark.parametrize("timezone_value", ["", "   "])
def test_empty_timezone_preserves_default_without_warning(
    tmp_path: Path,
    caplog,
    timezone_value: str,
) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"messages": {"timezone": timezone_value}}),
        encoding="utf-8",
    )

    with caplog.at_level(logging.WARNING, logger="app.config"):
        config = load_config(path)

    assert config.timezone_name == "America/New_York"
    assert not [record for record in caplog.records if record.name == "app.config"]


@pytest.mark.parametrize(
    ("timezone_value", "expected"),
    [("UTC", "UTC"), (" America/New_York ", "America/New_York")],
)
def test_valid_timezone_is_normalized(
    tmp_path: Path,
    caplog,
    timezone_value: str,
    expected: str,
) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"messages": {"timezone": timezone_value}}),
        encoding="utf-8",
    )

    with caplog.at_level(logging.WARNING, logger="app.config"):
        config = load_config(path)

    assert config.timezone_name == expected
    assert not [record for record in caplog.records if record.name == "app.config"]


def test_default_theme_values() -> None:
    config = AppConfig()

    assert config.photo_fit == "contain_color"
    assert config.photo_background_color == "#F8DDE3"
    assert config.card_background_color == "#EFAFBD"
    assert config.card_opacity == 225
    assert config.text_color == "#4A2532"
    assert config.clock_color == "#4A2532"
    assert config.show_decorations is True
    assert config.decoration_style == "pixel_hearts"
    assert config.heart_color == "#D85B7B"
    assert config.heart_highlight_color == "#FFF0F4"
    assert config.sparkle_color == "#C94F70"
    assert config.animate_decorations is True
    assert config.decoration_density == "medium"


@pytest.mark.parametrize("opacity", [0, 255])
def test_card_opacity_accepts_inclusive_boundaries(tmp_path: Path, opacity: int) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"messages": {"card_opacity": opacity}}),
        encoding="utf-8",
    )

    assert load_config(path).card_opacity == opacity


@pytest.mark.parametrize("opacity", [-1, 256, "225", True])
def test_invalid_card_opacity_uses_default(tmp_path: Path, opacity) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"messages": {"card_opacity": opacity}}),
        encoding="utf-8",
    )

    assert load_config(path).card_opacity == 225


def test_missing_local_config_uses_defaults(tmp_path: Path) -> None:
    assert load_config(tmp_path / "missing.json") == AppConfig()


def test_valid_local_config_overrides_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "display": {
                    "width": 800,
                    "height": 480,
                    "fullscreen": True,
                    "cursor_hide_seconds": 5,
                    "frames_per_second": 24,
                },
                "slideshow": {"interval_seconds": 20, "fade_duration_ms": 250},
                "photos": {
                    "path": "assets/photos",
                    "max_source_pixels": 12_000_000,
                    "photo_fit": "cover",
                    "photo_background_color": "#a1b2c3",
                },
                "messages": {
                    "path": "data/messages.local.json",
                    "timezone": "UTC",
                    "rollover_hour": 9,
                    "poll_seconds": 120,
                    "show_clock": False,
                    "clock_format": "24h",
                    "clock_font_size": 40,
                    "message_font_size": 22,
                    "card_background_color": "#123456",
                    "card_opacity": 180,
                    "text_color": "#abcdef",
                    "clock_color": "#FEDCBA",
                },
                "decorations": {
                    "show_decorations": False,
                    "decoration_style": "pixel_hearts",
                    "heart_color": "#112233",
                    "heart_highlight_color": "#f0e0d0",
                    "sparkle_color": "#445566",
                    "animate_decorations": False,
                    "decoration_density": "high",
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.width == 800
    assert config.height == 480
    assert config.fullscreen is True
    assert config.slideshow_interval_seconds == 20
    assert config.fade_duration_ms == 250
    assert config.cursor_hide_seconds == 5
    assert config.frames_per_second == 24
    assert config.photo_path == Path("assets/photos")
    assert config.max_source_pixels == 12_000_000
    assert config.photo_fit == "cover"
    assert config.photo_background_color == "#A1B2C3"
    assert config.message_path == Path("data/messages.local.json")
    assert config.timezone_name == "UTC"
    assert config.rollover_hour == 9
    assert config.message_poll_seconds == 120
    assert config.show_clock is False
    assert config.clock_format == "24h"
    assert config.clock_font_size == 40
    assert config.message_font_size == 22
    assert config.card_background_color == "#123456"
    assert config.card_opacity == 180
    assert config.text_color == "#ABCDEF"
    assert config.clock_color == "#FEDCBA"
    assert config.show_decorations is False
    assert config.decoration_style == "pixel_hearts"
    assert config.heart_color == "#112233"
    assert config.heart_highlight_color == "#F0E0D0"
    assert config.sparkle_color == "#445566"
    assert config.animate_decorations is False
    assert config.decoration_density == "high"


def test_malformed_local_config_uses_defaults(tmp_path: Path, caplog) -> None:
    path = tmp_path / "config.json"
    path.write_text("{not json", encoding="utf-8")

    assert load_config(path) == AppConfig()
    assert "Could not load configuration" in caplog.text


def test_invalid_fields_fall_back_individually(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "display": {"width": 0, "height": 720, "fullscreen": "yes"},
                "slideshow": {"interval_seconds": 9, "fade_duration_ms": -1},
                "photos": {
                    "path": "",
                    "max_source_pixels": 0,
                    "photo_fit": "stretch",
                    "photo_background_color": "pink",
                },
                "messages": {
                    "path": "",
                    "timezone": "Not/A_Zone",
                    "rollover_hour": 24,
                    "poll_seconds": 1,
                    "show_clock": "yes",
                    "clock_format": "seconds",
                    "clock_font_size": 9,
                    "message_font_size": 100,
                    "card_background_color": "#12345G",
                    "card_opacity": True,
                    "text_color": "#1234",
                    "clock_color": 123456,
                },
                "decorations": {
                    "show_decorations": "yes",
                    "decoration_style": "confetti",
                    "heart_color": "red",
                    "heart_highlight_color": "#FFFFFG",
                    "sparkle_color": None,
                    "animate_decorations": 1,
                    "decoration_density": "crowded",
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.width == 1024
    assert config.height == 720
    assert config.fullscreen is False
    assert config.slideshow_interval_seconds == 15
    assert config.fade_duration_ms == 400
    assert config.photo_path == Path("assets/photos")
    assert config.max_source_pixels == 20_000_000
    assert config.photo_fit == "contain_color"
    assert config.photo_background_color == "#F8DDE3"
    assert config.message_path == Path("data/messages.example.json")
    assert config.timezone_name == "America/New_York"
    assert config.rollover_hour == 8
    assert config.message_poll_seconds == 60
    assert config.show_clock is True
    assert config.clock_format == "12h"
    assert config.clock_font_size == 34
    assert config.message_font_size == 25
    assert config.card_background_color == "#EFAFBD"
    assert config.card_opacity == 225
    assert config.text_color == "#4A2532"
    assert config.clock_color == "#4A2532"
    assert config.show_decorations is True
    assert config.decoration_style == "pixel_hearts"
    assert config.heart_color == "#D85B7B"
    assert config.heart_highlight_color == "#FFF0F4"
    assert config.sparkle_color == "#C94F70"
    assert config.animate_decorations is True
    assert config.decoration_density == "low"


def test_non_object_config_uses_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("[]", encoding="utf-8")

    assert load_config(path) == AppConfig()
