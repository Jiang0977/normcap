import subprocess

from PySide6 import QtCore, QtGui

from normcap.screenshot.handlers import gnome_screenshot


class _TemporaryDirectory:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.path.mkdir()
        return str(self.path)

    def __exit__(self, exc_type, exc, tb):
        return False


def test_capture_precreates_target_file(monkeypatch, tmp_path):
    called = {}
    test_image = QtGui.QImage(QtCore.QSize(320, 160), QtGui.QImage.Format.Format_RGB32)
    test_image.fill(QtGui.QColor("white"))

    def mocked_run(args, **kwargs):
        image_path = tmp_path / "capture_dir" / "normcap_gnome_screenshot.png"
        called["path_exists_before_run"] = image_path.exists()
        test_image.save(str(image_path))
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        gnome_screenshot.tempfile,
        "TemporaryDirectory",
        lambda: _TemporaryDirectory(tmp_path / "capture_dir"),
    )
    monkeypatch.setattr(gnome_screenshot.subprocess, "run", mocked_run)
    monkeypatch.setattr(
        gnome_screenshot,
        "split_full_desktop_to_screens",
        lambda full_image: [full_image],
    )

    images = gnome_screenshot.capture()

    assert called["path_exists_before_run"]
    assert len(images) == 1
    assert images[0].size().toTuple() == (320, 160)


def test_capture_uses_written_image_on_non_zero_exit(monkeypatch, tmp_path):
    test_image = QtGui.QImage(QtCore.QSize(320, 160), QtGui.QImage.Format.Format_RGB32)
    test_image.fill(QtGui.QColor("white"))

    def mocked_run(args, **kwargs):
        image_path = tmp_path / "capture_dir" / "normcap_gnome_screenshot.png"
        test_image.save(str(image_path))
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="simulated gnome-screenshot stderr",
        )

    monkeypatch.setattr(
        gnome_screenshot.tempfile,
        "TemporaryDirectory",
        lambda: _TemporaryDirectory(tmp_path / "capture_dir"),
    )
    monkeypatch.setattr(gnome_screenshot.subprocess, "run", mocked_run)
    monkeypatch.setattr(
        gnome_screenshot,
        "split_full_desktop_to_screens",
        lambda full_image: [full_image],
    )

    images = gnome_screenshot.capture()

    assert len(images) == 1
    assert images[0].size().toTuple() == (320, 160)
