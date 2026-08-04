from pathlib import Path

import app.main as main_module


def _disable_file_logging(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "configure_application_logging", lambda: None)


def test_main_passes_windowed_overrides_to_display(tmp_path: Path, monkeypatch) -> None:
    _disable_file_logging(monkeypatch)
    received = []
    monkeypatch.setattr(main_module, "run_display", lambda config: received.append(config) or 0)

    result = main_module.main(
        [
            "--config",
            str(tmp_path / "missing.json"),
            "--windowed",
            "--width",
            "1024",
            "--height",
            "600",
            "--photos",
            str(tmp_path / "photos"),
        ]
    )

    assert result == 0
    assert received[0].fullscreen is False
    assert received[0].width == 1024
    assert received[0].height == 600
    assert received[0].photo_path == tmp_path / "photos"


def test_main_passes_fullscreen_override_to_display(tmp_path: Path, monkeypatch) -> None:
    _disable_file_logging(monkeypatch)
    received = []
    monkeypatch.setattr(main_module, "run_display", lambda config: received.append(config) or 0)

    result = main_module.main(
        ["--config", str(tmp_path / "missing.json"), "--fullscreen"]
    )

    assert result == 0
    assert received[0].fullscreen is True


def test_main_unwinds_cleanly_when_termination_is_requested(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    _disable_file_logging(monkeypatch)

    def interrupt_display(config) -> int:
        raise KeyboardInterrupt

    monkeypatch.setattr(main_module, "run_display", interrupt_display)

    result = main_module.main(
        ["--config", str(tmp_path / "missing.json"), "--fullscreen"]
    )

    assert result == 0
    assert "termination requested" in caplog.text
    assert "shutdown complete" in caplog.text
