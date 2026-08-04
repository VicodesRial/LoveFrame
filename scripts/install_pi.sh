#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
ENABLE_AUTOSTART=false
DRY_RUN=false

show_help() {
    cat <<'EOF'
Usage: scripts/install_pi.sh [options]

Install LoveFrame runtime packages on Raspberry Pi OS. The script does not
copy a Mac virtual environment or change boot, display, touch, or rotation settings.

Options:
  --enable-autostart  Add one user-level labwc autostart entry after installation.
  --dry-run           Print installation and file changes without applying them.
  -h, --help          Show this help text.
EOF
}

print_command() {
    printf 'DRY RUN:'
    printf ' %q' "$@"
    printf '\n'
}

run_command() {
    if [[ "${DRY_RUN}" == true ]]; then
        print_command "$@"
    else
        "$@"
    fi
}

while (($# > 0)); do
    case "$1" in
        --enable-autostart)
            ENABLE_AUTOSTART=true
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            printf 'Error: unknown option: %s\n' "$1" >&2
            show_help >&2
            exit 2
            ;;
    esac
    shift
done

if [[ "$(uname -s)" == "Darwin" ]]; then
    printf '%s\n' 'Error: install_pi.sh refuses to run on macOS.' >&2
    printf '%s\n' 'Run this script on Raspberry Pi OS after deploying the repository.' >&2
    exit 1
fi

MODEL=""
if [[ -r /proc/device-tree/model ]]; then
    MODEL="$(tr -d '\000' </proc/device-tree/model)"
fi
if [[ "${MODEL}" != *"Raspberry Pi"* ]]; then
    printf '%s\n' 'Warning: this device does not appear to be Raspberry Pi hardware.' >&2
    printf '%s\n' 'Review the dry-run output carefully before continuing.' >&2
fi

if ! command -v apt-get >/dev/null 2>&1; then
    printf '%s\n' 'Error: apt-get was not found; Raspberry Pi OS is required.' >&2
    exit 1
fi
if ! command -v sudo >/dev/null 2>&1; then
    printf '%s\n' 'Error: sudo was not found; package installation cannot continue.' >&2
    exit 1
fi

RUNTIME_PACKAGES=(
    python3
    python3-pygame
    python3-pil
    fonts-dejavu-core
    rsync
)

printf '%s\n' 'Installing the minimal LoveFrame runtime packages.'
run_command sudo apt-get update
run_command sudo apt-get install -y "${RUNTIME_PACKAGES[@]}"

STATE_ROOT="${XDG_STATE_HOME:-${HOME}/.local/state}"
STATE_DIRECTORY="${STATE_ROOT}/loveframe"
run_command mkdir -p -- "${STATE_DIRECTORY}"

if [[ "${DRY_RUN}" == false ]]; then
    printf '%s\n' 'Verifying Python, Pygame, Pillow, and zoneinfo.'
    python3 - <<'PY'
import sys
from zoneinfo import ZoneInfo

import pygame
from PIL import Image

ZoneInfo("America/New_York")
print(f"Python: {sys.version.split()[0]}")
print(f"Pygame: {pygame.version.ver}")
print(f"Pillow: {Image.__version__}")
print("zoneinfo: America/New_York available")
PY
    DEJAVU_FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if [[ ! -r "${DEJAVU_FONT}" ]]; then
        printf 'Error: expected DejaVu font was not found at %s\n' "${DEJAVU_FONT}" >&2
        exit 1
    fi
    printf 'DejaVu font: %s\n' "${DEJAVU_FONT}"
else
    printf '%s\n' 'DRY RUN: dependency and font verification would follow installation.'
fi

if [[ "${ENABLE_AUTOSTART}" == true ]]; then
    AUTOSTART_DIRECTORY="${XDG_CONFIG_HOME:-${HOME}/.config}/labwc"
    AUTOSTART_FILE="${AUTOSTART_DIRECTORY}/autostart"
    AUTOSTART_ENTRY="\"${REPOSITORY_ROOT}/scripts/run_pi.sh\" &"

    if [[ -f "${AUTOSTART_FILE}" ]] && grep -Fqx -- "${AUTOSTART_ENTRY}" "${AUTOSTART_FILE}"; then
        printf '%s\n' 'LoveFrame labwc autostart entry is already installed.'
    elif [[ "${DRY_RUN}" == true ]]; then
        print_command mkdir -p -- "${AUTOSTART_DIRECTORY}"
        if [[ -e "${AUTOSTART_FILE}" ]]; then
            printf 'DRY RUN: back up existing %s before changing it.\n' "${AUTOSTART_FILE}"
        fi
        printf 'DRY RUN: append once to %s: %s\n' \
            "${AUTOSTART_FILE}" "${AUTOSTART_ENTRY}"
    else
        mkdir -p -- "${AUTOSTART_DIRECTORY}"
        if [[ -e "${AUTOSTART_FILE}" ]]; then
            TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
            BACKUP_PATH="${AUTOSTART_FILE}.backup-${TIMESTAMP}"
            BACKUP_INDEX=1
            while [[ -e "${BACKUP_PATH}" ]]; do
                BACKUP_PATH="${AUTOSTART_FILE}.backup-${TIMESTAMP}-${BACKUP_INDEX}"
                BACKUP_INDEX=$((BACKUP_INDEX + 1))
            done
            cp -p -- "${AUTOSTART_FILE}" "${BACKUP_PATH}"
            printf 'Backed up existing autostart file to %s\n' "${BACKUP_PATH}"
        fi
        if [[ -s "${AUTOSTART_FILE}" ]] && [[ "$(tail -c 1 "${AUTOSTART_FILE}")" != "" ]]; then
            printf '\n' >>"${AUTOSTART_FILE}"
        fi
        printf '%s\n' "${AUTOSTART_ENTRY}" >>"${AUTOSTART_FILE}"
        printf 'Installed LoveFrame autostart entry in %s\n' "${AUTOSTART_FILE}"
    fi
else
    printf '%s\n' 'Autostart was not changed. Use --enable-autostart when ready.'
fi

printf '%s\n' 'LoveFrame runtime installation completed.'
