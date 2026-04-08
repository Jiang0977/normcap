"""Install auxiliary launchers into the Ubuntu system-package build tree."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path

PACKAGE_SEARCH_ROOT = Path("build/normcap/ubuntu")
MAIN_LAUNCHER = Path("usr/bin/normcap")
ANNOTATE_LAUNCHER = Path("usr/bin/normcap-annotate-prototype")


def render_annotate_launcher() -> str:
    """Render a wrapper that starts the packaged annotate prototype."""
    return """#!/usr/bin/env bash
set -euo pipefail

app_root="/usr/lib/normcap/app"
app_packages="/usr/lib/normcap/app_packages"
export PYTHONPATH="${app_root}:${app_packages}${PYTHONPATH:+:${PYTHONPATH}}"

exec /usr/bin/python3 -m normcap.annotate_prototype "$@"
"""


def discover_package_roots(paths: Iterable[Path]) -> list[Path]:
    """Return Ubuntu package roots that already contain the main launcher."""
    discovered: list[Path] = []
    for path in paths:
        candidate = path.resolve()
        if (candidate / MAIN_LAUNCHER).exists():
            discovered.append(candidate)
            continue

        if not candidate.exists():
            continue

        discovered.extend(
            nested.resolve()
            for nested in sorted(candidate.glob("*/normcap-*"))
            if (nested / MAIN_LAUNCHER).exists()
        )

    return discovered


def install_annotate_launcher(package_root: Path) -> Path:
    """Write the annotate launcher into the system package tree."""
    main_launcher = package_root / MAIN_LAUNCHER
    if not main_launcher.exists():
        raise FileNotFoundError(f"Main launcher missing: {main_launcher}")

    launcher_path = package_root / ANNOTATE_LAUNCHER
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text(render_annotate_launcher())
    launcher_path.chmod(0o755)
    return launcher_path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Install auxiliary launchers into Briefcase Ubuntu package trees."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[PACKAGE_SEARCH_ROOT],
        help=(
            "Package roots or parent directories containing Ubuntu system package"
            " trees."
        ),
    )
    return parser.parse_args()


def main() -> int:
    """Patch all discovered Ubuntu system package roots."""
    args = parse_args()
    package_roots = discover_package_roots(args.paths)
    if not package_roots:
        raise SystemExit("No Ubuntu system package roots found.")

    for package_root in package_roots:
        launcher_path = install_annotate_launcher(package_root)
        sys.stdout.write(f"{launcher_path}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
