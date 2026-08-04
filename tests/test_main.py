from pathlib import Path

import app.main as main_module


def test_main_passes_windowed_overrides_to_display(tmp_path: Path, monkeypatch) -> None:
    received = []
    monkeypatch.setattr(main_module, "run_display", lambda config: received.append(config) or 0)

    result = main_module.main(
        [
            "--config",
            str(tmp_path / "missing.json"),
            "--windowed",
            "--photos",
            str(tmp_path / "photos"),
        ]
    )

    assert result == 0
    assert received[0].fullscreen is False
    assert received[0].photo_path == tmp_path / "photos"


def test_main_passes_fullscreen_override_to_display(tmp_path: Path, monkeypatch) -> None:
    received = []
    monkeypatch.setattr(main_module, "run_display", lambda config: received.append(config) or 0)

    result = main_module.main(
        ["--config", str(tmp_path / "missing.json"), "--fullscreen"]
    )

    assert result == 0
    assert received[0].fullscreen is True
