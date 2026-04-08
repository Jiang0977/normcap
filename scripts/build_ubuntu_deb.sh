#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

TARGET_IMAGE="ubuntu:noble"
PACKAGING_FORMAT="deb"
DRY_RUN=0

usage() {
    cat <<'EOF'
Build an Ubuntu .deb package for the current NormCap checkout.

Usage:
  ./scripts/build_ubuntu_deb.sh [options]

Options:
  --target IMAGE     Docker target image. Default: ubuntu:noble
  --dry-run          Print the commands without executing them
  -h, --help         Show this help text
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)
            TARGET_IMAGE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

run_cmd() {
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        printf 'DRY-RUN:'
        printf ' %q' "$@"
        printf '\n'
        return 0
    fi

    "$@"
}

run_shell() {
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        printf 'DRY-RUN SHELL:\n%s\n' "$1"
        return 0
    fi

    bash -lc "$1"
}

ensure_docker() {
    if command -v docker >/dev/null 2>&1 && docker version >/dev/null 2>&1; then
        export PATH
        return 0
    fi

    if ! command -v docker >/dev/null 2>&1; then
        echo "docker is required" >&2
        exit 1
    fi

    if ! sudo docker version >/dev/null 2>&1; then
        echo "docker is installed but not usable, even via sudo" >&2
        exit 1
    fi

    mkdir -p /tmp/codex-docker-wrapper
    cat > /tmp/codex-docker-wrapper/docker <<'EOF'
#!/bin/sh
exec sudo /usr/bin/docker "$@"
EOF
    chmod +x /tmp/codex-docker-wrapper/docker
    export PATH="/tmp/codex-docker-wrapper:${PATH}"
}

patch_briefcase_docker_args() {
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        printf 'DRY-RUN: patch local Briefcase docker.py extra_build_args ordering\n'
        return 0
    fi

    local file
    file="$(uv run python - <<'PY'
import briefcase
from pathlib import Path
print(Path(briefcase.__file__).parent / 'integrations' / 'docker.py')
PY
)"

    local marker="extra_build_args if extra_build_args is not None else []"
    if grep -Fq "${marker}" "${file}"; then
        if python3 - "${file}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
needle = """                            \"--build-arg\",\n                            f\"HOST_GID={self.tools.os.getgid()}\",\n                            Path(\n                                self.app_base_path,\n                                *self.app.sources[0].split(\"/\")[:-1],\n                            ),\n                        ]\n                        + (extra_build_args if extra_build_args is not None else []),"""
replacement = """                            \"--build-arg\",\n                            f\"HOST_GID={self.tools.os.getgid()}\",\n                        ]\n                        + (extra_build_args if extra_build_args is not None else [])\n                        + [\n                            Path(\n                                self.app_base_path,\n                                *self.app.sources[0].split(\"/\")[:-1],\n                            ),\n                        ],"""

if needle in text:
    path.write_text(text.replace(needle, replacement))
PY
        then
            :
        fi
    fi
}

install_auxiliary_launchers() {
    run_cmd uv run python bundle/ubuntu_system_launchers.py build/normcap/ubuntu
}

main() {
    cd "${REPO_ROOT}"

    ensure_docker
    patch_briefcase_docker_args

    run_cmd uv sync --frozen --group dev
    run_cmd rm -rf "build/normcap/ubuntu" "dist/"*.deb

    run_cmd uv run briefcase create linux system \
        --target "${TARGET_IMAGE}" \
        --no-input \
        --Xdocker-build="--network=host"

    run_cmd uv run briefcase build linux system \
        --target "${TARGET_IMAGE}" \
        --no-input \
        --Xdocker-build="--network=host"

    install_auxiliary_launchers

    run_cmd uv run briefcase package linux system \
        --target "${TARGET_IMAGE}" \
        --packaging-format "${PACKAGING_FORMAT}" \
        --no-input \
        --Xdocker-build="--network=host"

    echo "Built packages:"
    run_shell "ls -lh dist/*.deb"
}

main
