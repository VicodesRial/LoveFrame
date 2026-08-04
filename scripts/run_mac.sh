#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

show_help() {
    cat <<'EOF'
Usage: scripts/run_mac.sh [LoveFrame options]

Run LoveFrame in a 1024x600 macOS development window using .venv.
Private local configuration and messages are preferred when present.
All unrecognized arguments are forwarded to python -m app.main.

Examples:
  ./scripts/run_mac.sh
  ./scripts/run_mac.sh --print-message
EOF
}

for argument in "$@"; do
    if [[ "${argument}" == "-h" || "${argument}" == "--help" ]]; then
        show_help
        exit 0
    fi
done

VIRTUAL_ENV_DIR="${REPOSITORY_ROOT}/.venv"
if [[ ! -f "${VIRTUAL_ENV_DIR}/bin/activate" ]]; then
    printf 'Error: macOS virtual environment not found at %s\n' "${VIRTUAL_ENV_DIR}" >&2
    printf 'Create it with: python3 -m venv .venv\n' >&2
    exit 1
fi

CONFIG_PATH="${REPOSITORY_ROOT}/config/config.example.json"
if [[ -f "${REPOSITORY_ROOT}/config/config.local.json" ]]; then
    CONFIG_PATH="${REPOSITORY_ROOT}/config/config.local.json"
fi

MESSAGE_PATH="${REPOSITORY_ROOT}/data/messages.example.json"
if [[ -f "${REPOSITORY_ROOT}/data/messages.local.json" ]]; then
    MESSAGE_PATH="${REPOSITORY_ROOT}/data/messages.local.json"
fi

PHOTO_PATH="${REPOSITORY_ROOT}/assets/photos"
export LOVEFRAME_LOG_DIR="${LOVEFRAME_LOG_DIR:-${REPOSITORY_ROOT}/logs}"

# shellcheck disable=SC1091
source "${VIRTUAL_ENV_DIR}/bin/activate"
cd -- "${REPOSITORY_ROOT}"

printf 'LoveFrame mode: windowed 1024x600\n'
printf 'Configuration: %s\n' "${CONFIG_PATH}"
printf 'Messages: %s\n' "${MESSAGE_PATH}"
printf 'Photos: %s\n' "${PHOTO_PATH}"

exec python -u -m app.main \
    "$@" \
    --windowed \
    --width 1024 \
    --height 600 \
    --config "${CONFIG_PATH}" \
    --messages "${MESSAGE_PATH}" \
    --photos "${PHOTO_PATH}"
