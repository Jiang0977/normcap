from __future__ import annotations

import os
import runpy
from pathlib import Path

MODULE = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "bundle" / "ubuntu_system_launchers.py"),
    run_name="bundle.ubuntu_system_launchers",
)

discover_package_roots = MODULE["discover_package_roots"]
install_annotate_launcher = MODULE["install_annotate_launcher"]


def test_discover_package_roots_from_search_root(tmp_path):
    package_root = tmp_path / "build" / "normcap" / "ubuntu" / "noble" / "normcap-0.6.2"
    launcher = package_root / "usr" / "bin" / "normcap"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("")

    discovered = discover_package_roots([tmp_path / "build" / "normcap" / "ubuntu"])

    assert discovered == [package_root.resolve()]


def test_install_annotate_launcher_writes_executable_wrapper(tmp_path):
    package_root = tmp_path / "noble" / "normcap-0.6.2"
    launcher = package_root / "usr" / "bin" / "normcap"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("")

    annotate_launcher = install_annotate_launcher(package_root)

    assert annotate_launcher == (
        package_root / "usr" / "bin" / "normcap-annotate-prototype"
    )
    assert os.access(annotate_launcher, os.X_OK)

    content = annotate_launcher.read_text()
    assert "/usr/lib/normcap/app" in content
    assert "/usr/lib/normcap/app_packages" in content
    assert 'exec /usr/bin/python3 -m normcap.annotate_prototype "$@"' in content
