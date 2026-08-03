import json
from pathlib import Path

from app.config import AppConfig, load_config


def test_missing_local_config_uses_defaults(tmp_path: Path) -> None:
    assert load_config(tmp_path / "missing.json") == AppConfig()


def test_valid_local_config_overrides_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "display": {"width": 800, "height": 480, "fullscreen": True},
                "slideshow": {"interval_seconds": 20},
                "messages": {
                    "path": "data/messages.local.json",
                    "timezone": "UTC",
                    "rollover_hour": 9,
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
    assert config.message_path == Path("data/messages.local.json")
    assert config.timezone_name == "UTC"
    assert config.rollover_hour == 9


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
                "slideshow": {"interval_seconds": -1},
                "messages": {
                    "path": "",
                    "timezone": "Not/A_Zone",
                    "rollover_hour": 24,
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
    assert config.message_path == Path("data/messages.example.json")
    assert config.timezone_name == "America/New_York"
    assert config.rollover_hour == 8


def test_non_object_config_uses_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("[]", encoding="utf-8")

    assert load_config(path) == AppConfig()
