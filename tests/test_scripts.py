import os
import subprocess
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SCRIPT = REPOSITORY_ROOT / "scripts" / "deploy_to_pi.sh"
RUN_PI_SCRIPT = REPOSITORY_ROOT / "scripts" / "run_pi.sh"
SHELL_SCRIPTS = tuple(sorted((REPOSITORY_ROOT / "scripts").glob("*.sh")))


@pytest.mark.parametrize("script", SHELL_SCRIPTS, ids=lambda path: path.name)
def test_shell_script_help_is_available(script: Path) -> None:
    assert os.access(script, os.X_OK)
    result = subprocess.run(
        ["bash", str(script), "--help"],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Usage:" in result.stdout


@pytest.mark.parametrize(
    "unsafe_path",
    ["relative/LoveFrame", "/", "/home", "/home/vic/Other", "/home/../LoveFrame"],
)
def test_deployment_rejects_unsafe_paths_before_ssh(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    marker = tmp_path / "ssh-was-called"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_ssh = fake_bin / "ssh"
    fake_ssh.write_text(
        f"#!/usr/bin/env bash\ntouch {marker!s}\n",
        encoding="utf-8",
    )
    fake_ssh.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = f"{fake_bin}:{environment['PATH']}"

    result = subprocess.run(
        [
            "bash",
            str(DEPLOY_SCRIPT),
            "--project-dir",
            unsafe_path,
            "--validate-only",
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not marker.exists()


def test_deployment_exclusions_are_constructed_without_transfer() -> None:
    result = subprocess.run(
        ["bash", str(DEPLOY_SCRIPT), "--validate-only"],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "no SSH connection or transfer was attempted" in result.stdout
    assert "--exclude=.venv/" in result.stdout
    assert "--exclude=.git/" in result.stdout
    assert "--exclude=__pycache__/" in result.stdout
    assert "--exclude=.ssh/" in result.stdout
    assert "--exclude=.env" in result.stdout
    assert "--exclude=id_*" in result.stdout
    assert "--exclude=credentials*" in result.stdout
    assert "--exclude=/assets/photos/***" in result.stdout
    assert "--exclude=/data/messages.local.json" in result.stdout
    assert "--exclude=/config/config.local.json" in result.stdout
    assert "--delete" not in result.stdout


def test_include_private_plan_warns_and_removes_private_exclusions() -> None:
    result = subprocess.run(
        [
            "bash",
            str(DEPLOY_SCRIPT),
            "--include-private",
            "--validate-only",
        ],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "PRIVACY WARNING" in result.stderr
    assert "--exclude=.venv/" in result.stdout
    assert "--exclude=/assets/photos/***" not in result.stdout
    assert "--exclude=/data/messages.local.json" not in result.stdout
    assert "--exclude=/config/config.local.json" not in result.stdout


def test_connection_values_support_environment_overrides() -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "PI_USER": "frameuser",
            "PI_HOST": "frame.example",
            "PI_PROJECT_DIR": "/srv/frame/LoveFrame",
        }
    )

    result = subprocess.run(
        ["bash", str(DEPLOY_SCRIPT), "--validate-only"],
        cwd=REPOSITORY_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "frameuser@frame.example:/srv/frame/LoveFrame/" in result.stdout


def test_pi_launcher_supports_immediate_documented_restart() -> None:
    launcher = RUN_PI_SCRIPT.read_text(encoding="utf-8")

    assert "export PYTHONUNBUFFERED=1" in launcher
    assert "flock -w 15 9" in launcher
    assert "exec python3 -m app.main" in launcher
