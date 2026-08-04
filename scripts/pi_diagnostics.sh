#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

show_help() {
    cat <<'EOF'
Usage: scripts/pi_diagnostics.sh

Print read-only Raspberry Pi, display, LoveFrame content, process, and log
diagnostics. Optional tools are reported as unavailable instead of causing failure.
No configuration or system files are changed.
EOF
}

if (($# > 0)); then
    case "$1" in
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
fi

section() {
    printf '\n== %s ==\n' "$1"
}

section "Operating system and kernel"
if [[ -r /etc/os-release ]]; then
    sed -n 's/^PRETTY_NAME=//p' /etc/os-release | tr -d '"' || true
else
    printf '%s\n' '/etc/os-release unavailable'
fi
uname -srmo 2>/dev/null || printf '%s\n' 'Kernel information unavailable'

section "Architecture"
uname -m 2>/dev/null || printf '%s\n' 'Architecture unavailable'

section "Python and libraries"
if command -v python3 >/dev/null 2>&1; then
    python3 --version 2>&1 || true
    python3 - <<'PY' 2>/dev/null || printf '%s\n' 'Pygame or Pillow unavailable'
import pygame
from PIL import Image

print(f"Pygame {pygame.version.ver}")
print(f"Pillow {Image.__version__}")
PY
else
    printf '%s\n' 'python3 unavailable'
fi

section "Memory"
if command -v free >/dev/null 2>&1; then
    free -h || true
elif [[ -r /proc/meminfo ]]; then
    sed -n '1,5p' /proc/meminfo || true
else
    printf '%s\n' 'Memory information unavailable'
fi

section "Project filesystem"
df -h -- "${REPOSITORY_ROOT}" 2>/dev/null || printf '%s\n' 'Disk usage unavailable'

section "Temperature and throttling"
if command -v vcgencmd >/dev/null 2>&1; then
    vcgencmd measure_temp 2>/dev/null || printf '%s\n' 'Temperature unavailable'
    vcgencmd get_throttled 2>/dev/null || printf '%s\n' 'Throttling status unavailable'
else
    printf '%s\n' 'vcgencmd unavailable'
fi

section "Graphical session"
printf 'XDG_SESSION_TYPE=%s\n' "${XDG_SESSION_TYPE:-<unset>}"
printf 'XDG_CURRENT_DESKTOP=%s\n' "${XDG_CURRENT_DESKTOP:-<unset>}"
printf 'WAYLAND_DISPLAY=%s\n' "${WAYLAND_DISPLAY:-<unset>}"
printf 'DISPLAY=%s\n' "${DISPLAY:-<unset>}"
printf 'XDG_RUNTIME_DIR=%s\n' "${XDG_RUNTIME_DIR:-<unset>}"

section "Connected displays"
if command -v wlr-randr >/dev/null 2>&1; then
    wlr-randr 2>/dev/null || printf '%s\n' 'wlr-randr could not query the session'
elif command -v xrandr >/dev/null 2>&1; then
    xrandr --current 2>/dev/null || printf '%s\n' 'xrandr could not query the session'
else
    DISPLAY_STATUS_FOUND=false
    for STATUS_FILE in /sys/class/drm/*/status; do
        [[ -e "${STATUS_FILE}" ]] || continue
        DISPLAY_STATUS_FOUND=true
        printf '%s: ' "$(basename -- "$(dirname -- "${STATUS_FILE}")")"
        tr -d '\n' <"${STATUS_FILE}" || true
        printf '\n'
    done
    if [[ "${DISPLAY_STATUS_FOUND}" == false ]]; then
        printf '%s\n' 'Display query tools and DRM status files unavailable'
    fi
fi

section "Private content presence"
if [[ -f "${REPOSITORY_ROOT}/config/config.local.json" ]]; then
    printf '%s\n' 'Private configuration: present'
else
    printf '%s\n' 'Private configuration: missing'
fi
if [[ -f "${REPOSITORY_ROOT}/data/messages.local.json" ]]; then
    printf '%s\n' 'Private messages: present'
else
    printf '%s\n' 'Private messages: missing'
fi

PHOTO_DIRECTORY="${REPOSITORY_ROOT}/assets/photos"
PHOTO_COUNT="unavailable"
if command -v python3 >/dev/null 2>&1; then
    if COUNT_RESULT="$(python3 - "${PHOTO_DIRECTORY}" <<'PY' 2>/dev/null
from pathlib import Path
import sys

directory = Path(sys.argv[1])
supported = {".jpeg", ".jpg", ".png", ".webp"}
count = 0
try:
    entries = directory.iterdir()
    for path in entries:
        name = path.name.casefold()
        temporary = (
            name.startswith(("~", ".#"))
            or name.endswith("~")
            or ".tmp." in name
            or ".part." in name
        )
        if (
            path.is_file()
            and not name.startswith(".")
            and not temporary
            and path.suffix.casefold() in supported
        ):
            count += 1
except OSError:
    raise SystemExit(1)
print(count)
PY
)"; then
        PHOTO_COUNT="${COUNT_RESULT}"
    fi
fi
printf 'Supported photos: %s\n' "${PHOTO_COUNT}"

section "LoveFrame process"
if command -v pgrep >/dev/null 2>&1; then
    if ! pgrep -af 'python3 .*[-]m app[.]main'; then
        printf '%s\n' 'LoveFrame is not running'
    fi
else
    printf '%s\n' 'pgrep unavailable'
fi

section "Recent LoveFrame log"
printf '%s\n' 'Privacy warning: logs may contain content filenames, but never message text.'
STATE_ROOT="${XDG_STATE_HOME:-${HOME}/.local/state}"
LOG_PATH="${STATE_ROOT}/loveframe/loveframe.log"
if [[ -r "${LOG_PATH}" ]]; then
    tail -n 80 -- "${LOG_PATH}" || true
else
    printf 'No readable log at %s\n' "${LOG_PATH}"
fi
