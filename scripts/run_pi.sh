#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
EXAMPLE_CONTENT=false
FORWARDED_ARGUMENTS=()

show_help() {
    cat <<'EOF'
Usage: scripts/run_pi.sh [--example-content] [LoveFrame options]

Run LoveFrame fullscreen at 1024x600 in the active Wayland/labwc session.
Private config and messages are required unless --example-content is supplied.
Additional arguments are forwarded to python3 -m app.main.

Options:
  --example-content  Explicitly use tracked example configuration and messages.
  -h, --help         Show this help text.
EOF
}

while (($# > 0)); do
    case "$1" in
        --example-content)
            EXAMPLE_CONTENT=true
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            FORWARDED_ARGUMENTS+=("$1")
            ;;
    esac
    shift
done

if [[ -z "${WAYLAND_DISPLAY:-}" || -z "${XDG_RUNTIME_DIR:-}" ]]; then
    printf '%s\n' \
        'Error: run_pi.sh must be started inside an active Wayland/labwc desktop session.' >&2
    printf '%s\n' 'Log in to the desktop first; do not run it from a plain SSH session.' >&2
    exit 1
fi

if ! command -v flock >/dev/null 2>&1; then
    printf '%s\n' 'Error: flock is required for LoveFrame single-instance protection.' >&2
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Error: python3 is not installed. Run scripts/install_pi.sh first.' >&2
    exit 1
fi

CONFIG_PATH="${REPOSITORY_ROOT}/config/config.local.json"
MESSAGE_PATH="${REPOSITORY_ROOT}/data/messages.local.json"
if [[ "${EXAMPLE_CONTENT}" == true ]]; then
    CONFIG_PATH="${REPOSITORY_ROOT}/config/config.example.json"
    MESSAGE_PATH="${REPOSITORY_ROOT}/data/messages.example.json"
else
    if [[ ! -f "${CONFIG_PATH}" ]]; then
        printf 'Error: private configuration is missing: %s\n' "${CONFIG_PATH}" >&2
        printf '%s\n' 'Use --example-content only for a deliberate example-mode test.' >&2
        exit 1
    fi
    if [[ ! -f "${MESSAGE_PATH}" ]]; then
        printf 'Error: private message file is missing: %s\n' "${MESSAGE_PATH}" >&2
        printf '%s\n' 'Deploy it intentionally or use --example-content for testing.' >&2
        exit 1
    fi
fi

PHOTO_PATH="${REPOSITORY_ROOT}/assets/photos"
STATE_ROOT="${XDG_STATE_HOME:-${HOME}/.local/state}"
STATE_DIRECTORY="${STATE_ROOT}/loveframe"
mkdir -p -- "${STATE_DIRECTORY}"
export LOVEFRAME_LOG_DIR="${STATE_DIRECTORY}"
export PYTHONUNBUFFERED=1

LOCK_PATH="${STATE_DIRECTORY}/loveframe.lock"
exec 9>"${LOCK_PATH}"
if ! flock -n 9; then
    printf '%s\n' 'LoveFrame is already running; refusing to start a duplicate instance.' >&2
    exit 1
fi

cd -- "${REPOSITORY_ROOT}"
printf 'LoveFrame mode: fullscreen 1024x600\n'
printf 'Configuration: %s\n' "${CONFIG_PATH}"
printf 'Messages: %s\n' "${MESSAGE_PATH}"
printf 'Photos: %s\n' "${PHOTO_PATH}"

exec python3 -u -m app.main \
    "${FORWARDED_ARGUMENTS[@]}" \
    --fullscreen \
    --width 1024 \
    --height 600 \
    --config "${CONFIG_PATH}" \
    --messages "${MESSAGE_PATH}" \
    --photos "${PHOTO_PATH}"
