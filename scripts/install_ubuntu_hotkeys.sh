#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

INSTALL_TARGET="${REPO_ROOT}"
OCR_LANGUAGES="chi_sim eng"
ANNOTATE_BINDING="<Ctrl><Alt>a"
OCR_BINDING="<Ctrl><Alt>o"
SKIP_DEPS=0
SKIP_SHORTCUTS=0
DRY_RUN=0

usage() {
    cat <<'EOF'
Ubuntu one-click installer for the current NormCap checkout plus GNOME hotkeys.

Usage:
  ./scripts/install_ubuntu_hotkeys.sh [options]

Options:
  --install-target PATH_OR_URL   Install from this local directory, wheel/tarball, or URL.
                                 Defaults to the current repository root.
  --ocr-languages "LANGS"        Space-separated OCR languages for the OCR shortcut.
                                 Default: "chi_sim eng"
  --annotate-binding BINDING     GNOME binding for annotate prototype.
                                 Default: "<Ctrl><Alt>a"
  --ocr-binding BINDING          GNOME binding for OCR mode.
                                 Default: "<Ctrl><Alt>o"
  --skip-deps                    Skip apt dependency installation.
  --skip-shortcuts               Install NormCap only, don't configure GNOME shortcuts.
  --dry-run                      Print the commands without executing them.
  -h, --help                     Show this help text.

Examples:
  ./scripts/install_ubuntu_hotkeys.sh
  ./scripts/install_ubuntu_hotkeys.sh --install-target dist/normcap-0.6.0-py3-none-any.whl
  ./scripts/install_ubuntu_hotkeys.sh --ocr-languages "eng deu"
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --install-target)
            INSTALL_TARGET="$2"
            shift 2
            ;;
        --ocr-languages)
            OCR_LANGUAGES="$2"
            shift 2
            ;;
        --annotate-binding)
            ANNOTATE_BINDING="$2"
            shift 2
            ;;
        --ocr-binding)
            OCR_BINDING="$2"
            shift 2
            ;;
        --skip-deps)
            SKIP_DEPS=1
            shift
            ;;
        --skip-shortcuts)
            SKIP_SHORTCUTS=1
            shift
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

ensure_apt_packages() {
    run_cmd sudo apt-get update
    run_cmd sudo apt-get install -y \
        curl \
        gnome-screenshot \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-chi-sim \
        wl-clipboard \
        xclip
}

ensure_uv() {
    if command -v uv >/dev/null 2>&1; then
        return 0
    fi

    run_shell 'curl -LsSf https://astral.sh/uv/install.sh | sh'
    export PATH="${HOME}/.local/bin:${PATH}"
}

install_normcap() {
    local target="$1"

    if [[ -d "${target}" ]]; then
        run_cmd uv tool install --editable --force "${target}"
        return 0
    fi

    run_cmd uv tool install --force "${target}"
}

write_wrapper_scripts() {
    local normcap_bin="$1"
    local annotate_bin="$2"

    mkdir -p "${HOME}/.local/bin"

    local -a ocr_lang_array
    # shellcheck disable=SC2206
    ocr_lang_array=(${OCR_LANGUAGES})

    local ocr_lang_literal=""
    local lang
    for lang in "${ocr_lang_array[@]}"; do
        ocr_lang_literal+="$(printf "'%s' " "${lang}")"
    done

    local annotate_wrapper="${HOME}/.local/bin/normcap-annotate-hotkey"
    local ocr_wrapper="${HOME}/.local/bin/normcap-ocr-hotkey"

    if [[ "${DRY_RUN}" -eq 1 ]]; then
        printf 'DRY-RUN: write %s and %s\n' "${annotate_wrapper}" "${ocr_wrapper}"
        return 0
    fi

    cat > "${annotate_wrapper}" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "${annotate_bin}" "\$@"
EOF

    cat > "${ocr_wrapper}" <<EOF
#!/usr/bin/env bash
set -euo pipefail

clipboard_handler="wlclipboard"
if [[ "\${XDG_SESSION_TYPE:-wayland}" != "wayland" ]]; then
    clipboard_handler="xclip"
fi

exec "${normcap_bin}" -l ${ocr_lang_literal} --screenshot-handler gnome_screenshot --clipboard-handler "\${clipboard_handler}" "\$@"
EOF

    chmod +x "${annotate_wrapper}" "${ocr_wrapper}"
}

configure_gnome_shortcuts() {
    local annotate_wrapper="$1"
    local ocr_wrapper="$2"

    if ! command -v gsettings >/dev/null 2>&1; then
        echo "gsettings not found; skipping GNOME shortcut configuration." >&2
        return 0
    fi

    if ! gsettings list-schemas | rg -q '^org\.gnome\.settings-daemon\.plugins\.media-keys$'; then
        echo "GNOME media keys schema not found; skipping shortcut configuration." >&2
        return 0
    fi

    local python_script
    read -r -d '' python_script <<'PY' || true
import ast
import subprocess
import sys

root = "org.gnome.settings-daemon.plugins.media-keys"
item = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"

annotate_name, annotate_cmd, annotate_binding, ocr_name, ocr_cmd, ocr_binding = sys.argv[1:]

raw = subprocess.check_output(["gsettings", "get", root, "custom-keybindings"], text=True).strip()
paths = ast.literal_eval(raw)


def get_value(path: str, key: str) -> str:
    try:
        value = subprocess.check_output(
            ["gsettings", "get", f"{item}:{path}", key],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return ""
    return value.strip("'")


def set_value(path: str, key: str, value: str) -> None:
    subprocess.check_call(
        ["gsettings", "set", f"{item}:{path}", key, value]
    )


def write_paths() -> None:
    literal = "[" + ", ".join(f"'{path}'" for path in paths) + "]"
    subprocess.check_call(["gsettings", "set", root, "custom-keybindings", literal])


def allocate_path() -> str:
    numbers = []
    for path in paths:
        stem = path.rstrip("/").split("custom")[-1]
        if stem.isdigit():
            numbers.append(int(stem))
    next_number = max(numbers, default=-1) + 1
    return f"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom{next_number}/"


def ensure_shortcut(name: str, command: str, binding: str) -> str:
    for path in paths:
        if get_value(path, "name") == name:
            target = path
            break
    else:
        for path in paths:
            if get_value(path, "binding") == binding:
                target = path
                break
        else:
            target = allocate_path()
            paths.append(target)
            write_paths()

    set_value(target, "name", repr(name))
    set_value(target, "command", repr(command))
    set_value(target, "binding", repr(binding))
    return target


ensure_shortcut(annotate_name, annotate_cmd, annotate_binding)
ensure_shortcut(ocr_name, ocr_cmd, ocr_binding)
write_paths()
PY

    if [[ "${DRY_RUN}" -eq 1 ]]; then
        printf 'DRY-RUN PYTHON SHORTCUT CONFIG:\n%s\n' "${python_script}"
        return 0
    fi

    python3 -c "${python_script}" \
        "NormCap Annotate" "${annotate_wrapper}" "${ANNOTATE_BINDING}" \
        "NormCap OCR" "${ocr_wrapper}" "${OCR_BINDING}"
}

main() {
    local resolved_target="${INSTALL_TARGET}"
    if [[ "${INSTALL_TARGET}" == /* ]] || [[ "${INSTALL_TARGET}" == *://* ]]; then
        resolved_target="${INSTALL_TARGET}"
    elif [[ -e "${INSTALL_TARGET}" ]]; then
        resolved_target="$(realpath "${INSTALL_TARGET}")"
    fi

    if [[ "${SKIP_DEPS}" -eq 0 ]]; then
        ensure_apt_packages
    fi

    ensure_uv
    install_normcap "${resolved_target}"

    local normcap_bin annotate_bin
    normcap_bin="$(command -v normcap)"
    annotate_bin="$(command -v normcap-annotate-prototype)"

    if [[ -z "${normcap_bin}" || -z "${annotate_bin}" ]]; then
        echo "NormCap commands were not installed correctly." >&2
        exit 1
    fi

    write_wrapper_scripts "${normcap_bin}" "${annotate_bin}"

    if [[ "${SKIP_SHORTCUTS}" -eq 0 ]]; then
        configure_gnome_shortcuts \
            "${HOME}/.local/bin/normcap-annotate-hotkey" \
            "${HOME}/.local/bin/normcap-ocr-hotkey"
    fi

    cat <<EOF
Done.

Installed commands:
- ${normcap_bin}
- ${annotate_bin}

Wrapper commands:
- ${HOME}/.local/bin/normcap-annotate-hotkey
- ${HOME}/.local/bin/normcap-ocr-hotkey

Shortcut targets:
- Annotate: ${ANNOTATE_BINDING}
- OCR: ${OCR_BINDING}
EOF
}

main
