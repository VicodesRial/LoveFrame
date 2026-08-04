#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

PI_USER="${PI_USER:-vic}"
PI_HOST="${PI_HOST:-loveframe.local}"
PI_PROJECT_DIR="${PI_PROJECT_DIR:-/home/vic/LoveFrame}"
DRY_RUN=false
INCLUDE_PRIVATE=false
ASSUME_YES=false
RUN_SMOKE_TEST=false
VALIDATE_ONLY=false

show_help() {
    cat <<'EOF'
Usage: scripts/deploy_to_pi.sh [options]

Deploy LoveFrame from macOS with rsync over SSH. Normal deployments preserve
Pi-local photos, messages, and configuration and never use rsync --delete.

Options:
  --user USER          SSH user (default: PI_USER or vic).
  --host HOST          SSH host (default: PI_HOST or loveframe.local).
  --project-dir PATH   Absolute Pi destination ending in LoveFrame.
  --dry-run            Use rsync dry-run; SSH connectivity is still checked.
  --include-private    Also transfer local photos, messages, and configuration.
  --yes                Confirm --include-private without an interactive prompt.
  --smoke-test         Run a read-only remote import/source-compilation check.
  --validate-only      Validate settings and print rsync exclusions without SSH.
  -h, --help           Show this help text.

Environment overrides: PI_USER, PI_HOST, PI_PROJECT_DIR.
EOF
}

die() {
    printf 'Error: %s\n' "$1" >&2
    exit 1
}

require_option_value() {
    if (($# < 2)) || [[ -z "$2" ]]; then
        die "$1 requires a value"
    fi
}

while (($# > 0)); do
    case "$1" in
        --user)
            require_option_value "$@"
            PI_USER="$2"
            shift
            ;;
        --user=*)
            PI_USER="${1#*=}"
            ;;
        --host)
            require_option_value "$@"
            PI_HOST="$2"
            shift
            ;;
        --host=*)
            PI_HOST="${1#*=}"
            ;;
        --project-dir)
            require_option_value "$@"
            PI_PROJECT_DIR="$2"
            shift
            ;;
        --project-dir=*)
            PI_PROJECT_DIR="${1#*=}"
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        --include-private)
            INCLUDE_PRIVATE=true
            ;;
        --yes)
            ASSUME_YES=true
            ;;
        --smoke-test)
            RUN_SMOKE_TEST=true
            ;;
        --validate-only)
            VALIDATE_ONLY=true
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            die "unknown option: $1"
            ;;
    esac
    shift
done

if [[ ! "${PI_USER}" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ ]]; then
    die "PI_USER contains unsupported characters"
fi
if [[ ! "${PI_HOST}" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*$ ]]; then
    die "PI_HOST must be a hostname or IPv4 address without spaces"
fi
if [[ "${PI_PROJECT_DIR}" != /* ]]; then
    die "PI_PROJECT_DIR must be an absolute path"
fi
if [[ "${PI_PROJECT_DIR}" == "/" || "${PI_PROJECT_DIR}" == "/home" ]]; then
    die "PI_PROJECT_DIR cannot target / or /home"
fi
if [[ "${PI_PROJECT_DIR}" != */LoveFrame ]]; then
    die "PI_PROJECT_DIR must end with /LoveFrame"
fi
if [[ ! "${PI_PROJECT_DIR}" =~ ^/[A-Za-z0-9._/-]+$ ]]; then
    die "PI_PROJECT_DIR contains unsupported characters"
fi
case "${PI_PROJECT_DIR}/" in
    *//*|*/../*|*/./*)
        die "PI_PROJECT_DIR must not contain empty, dot, or parent components"
        ;;
esac

COMMON_EXCLUDES=(
    "--exclude=.venv/"
    "--exclude=.git/"
    "--exclude=__pycache__/"
    "--exclude=.pytest_cache/"
    "--exclude=*.pyc"
    "--exclude=logs/"
    "--exclude=*.log"
    "--exclude=.DS_Store"
    "--exclude=*~"
    "--exclude=.#*"
    "--exclude=*.swp"
    "--exclude=*.tmp"
    "--exclude=.ssh/"
    "--exclude=.env"
    "--exclude=.env.*"
    "--exclude=*.pem"
    "--exclude=*.key"
    "--exclude=id_*"
    "--exclude=credentials*"
    "--exclude=secrets*"
)
PRIVATE_EXCLUDES=(
    "--exclude=/assets/photos/***"
    "--exclude=/data/messages.local.json"
    "--exclude=/config/config.local.json"
)
RSYNC_EXCLUDES=("${COMMON_EXCLUDES[@]}")
if [[ "${INCLUDE_PRIVATE}" == false ]]; then
    RSYNC_EXCLUDES+=("${PRIVATE_EXCLUDES[@]}")
fi

printf 'Source: %s/\n' "${REPOSITORY_ROOT}"
printf 'Destination: %s@%s:%s/\n' "${PI_USER}" "${PI_HOST}" "${PI_PROJECT_DIR}"
printf '%s\n' 'Rsync exclusions:'
printf '  %s\n' "${RSYNC_EXCLUDES[@]}"

if [[ "${INCLUDE_PRIVATE}" == true ]]; then
    printf '%s\n' \
        'PRIVACY WARNING: --include-private may overwrite Pi-local photos,' \
        'messages, and configuration with private files from this Mac.' >&2
fi

if [[ "${VALIDATE_ONLY}" == true ]]; then
    printf '%s\n' 'Validation complete; no SSH connection or transfer was attempted.'
    exit 0
fi

if [[ "${INCLUDE_PRIVATE}" == true && "${ASSUME_YES}" == false ]]; then
    if [[ ! -t 0 ]]; then
        die "--include-private requires an interactive confirmation or --yes"
    fi
    read -r -p "Transfer and potentially overwrite private Pi content? [y/N] " REPLY
    if [[ "${REPLY}" != "y" && "${REPLY}" != "Y" ]]; then
        printf '%s\n' 'Private deployment cancelled.'
        exit 1
    fi
fi

command -v ssh >/dev/null 2>&1 || die "ssh was not found"
command -v rsync >/dev/null 2>&1 || die "rsync was not found"

REMOTE_TARGET="${PI_USER}@${PI_HOST}"
printf 'Checking SSH connectivity to %s...\n' "${REMOTE_TARGET}"
ssh -o ConnectTimeout=10 "${REMOTE_TARGET}" true

REMOTE_RESOLVE_COMMAND="resolved=\$(realpath -m -- '${PI_PROJECT_DIR}') && "
REMOTE_RESOLVE_COMMAND+="test \"\${resolved}\" = '${PI_PROJECT_DIR}'"
if ! ssh "${REMOTE_TARGET}" "${REMOTE_RESOLVE_COMMAND}"; then
    die "the remote destination resolves outside the approved project path"
fi

if [[ "${DRY_RUN}" == false ]]; then
    REMOTE_MKDIR_COMMAND="mkdir -p -- '${PI_PROJECT_DIR}'"
    ssh "${REMOTE_TARGET}" "${REMOTE_MKDIR_COMMAND}"
fi

RSYNC_OPTIONS=(-az --human-readable --itemize-changes -e ssh)
if [[ "${DRY_RUN}" == true ]]; then
    RSYNC_OPTIONS+=(--dry-run)
fi

rsync \
    "${RSYNC_OPTIONS[@]}" \
    "${RSYNC_EXCLUDES[@]}" \
    "${REPOSITORY_ROOT}/" \
    "${REMOTE_TARGET}:${PI_PROJECT_DIR}/"

if [[ "${RUN_SMOKE_TEST}" == true ]]; then
    if [[ "${DRY_RUN}" == true ]]; then
        printf '%s\n' 'Dry run: remote smoke test was not executed.'
    else
        printf '%s\n' 'Running non-mutating remote import and source-compilation smoke test.'
        REMOTE_SMOKE_COMMAND="cd -- '${PI_PROJECT_DIR}' && "
        REMOTE_SMOKE_COMMAND+="PYTHONDONTWRITEBYTECODE=1 python3 -c \""
        REMOTE_SMOKE_COMMAND+="import app.config, app.message_scheduler, "
        REMOTE_SMOKE_COMMAND+="app.photo_loader, app.ui; "
        REMOTE_SMOKE_COMMAND+="from pathlib import Path; "
        REMOTE_SMOKE_COMMAND+="[compile(p.read_text(encoding='utf-8'), str(p), 'exec') "
        REMOTE_SMOKE_COMMAND+="for p in Path('app').glob('*.py')]\""
        ssh "${REMOTE_TARGET}" "${REMOTE_SMOKE_COMMAND}"
    fi
fi

printf '%s\n' 'LoveFrame deployment completed.'
