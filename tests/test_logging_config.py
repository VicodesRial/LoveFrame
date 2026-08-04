import io
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

import app.logging_config as logging_config


def _managed_handlers() -> list[logging.Handler]:
    return [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "_loveframe_managed_handler", None) is not None
    ]


def _remove_managed_handlers() -> None:
    root_logger = logging.getLogger()
    for handler in _managed_handlers():
        root_logger.removeHandler(handler)
        handler.close()


@pytest.fixture(autouse=True)
def clean_application_handlers():
    _remove_managed_handlers()
    yield
    _remove_managed_handlers()


def test_rotating_log_configuration_is_bounded_and_not_duplicated(tmp_path: Path) -> None:
    log_path = logging_config.configure_application_logging(tmp_path, stream=None)
    repeated_path = logging_config.configure_application_logging(tmp_path, stream=None)

    file_handlers = [
        handler
        for handler in _managed_handlers()
        if isinstance(handler, RotatingFileHandler)
    ]
    assert log_path == tmp_path / "loveframe.log"
    assert repeated_path == log_path
    assert len(file_handlers) == 1
    assert file_handlers[0].maxBytes == 1_048_576
    assert file_handlers[0].backupCount == 3


def test_log_rotation_keeps_only_configured_backups(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(logging_config, "MAX_LOG_BYTES", 256)
    logging_config.configure_application_logging(tmp_path, stream=None)
    logger = logging.getLogger("app.rotation_test")

    for index in range(40):
        logger.info("bounded entry %02d %s", index, "x" * 48)
    for handler in _managed_handlers():
        handler.flush()

    files = sorted(tmp_path.glob("loveframe.log*"))
    assert tmp_path / "loveframe.log" in files
    assert tmp_path / "loveframe.log.1" in files
    assert len(files) <= logging_config.LOG_BACKUP_COUNT + 1


def test_startup_logging_uses_only_safe_path_labels() -> None:
    output = io.StringIO()
    logger = logging.Logger("privacy-test")
    handler = logging.StreamHandler(output)
    logger.addHandler(handler)

    logging_config.log_startup_selection(
        logger,
        mode="fullscreen",
        config_path="/private/household/config.local.json",
        message_path="/private/romantic/messages.local.json",
        photo_path="/private/family/assets/photos",
    )

    logged = output.getvalue()
    assert "fullscreen" in logged
    assert "config.local.json" in logged
    assert "messages.local.json" in logged
    assert "photos" in logged
    assert "/private/" not in logged
    assert "romantic" not in logged


def test_logging_setup_failure_does_not_escape(tmp_path: Path, monkeypatch, capsys) -> None:
    def fail_to_create(*args, **kwargs) -> None:
        raise PermissionError("generated test failure")

    monkeypatch.setattr(Path, "mkdir", fail_to_create)

    assert logging_config.configure_application_logging(tmp_path, stream=None) is None
    assert "continuing without it" in capsys.readouterr().err


def test_invalid_log_path_does_not_prevent_startup(capsys) -> None:
    invalid_path = Path("invalid\000directory")

    assert logging_config.configure_application_logging(invalid_path, stream=None) is None
    assert "continuing without it" in capsys.readouterr().err
