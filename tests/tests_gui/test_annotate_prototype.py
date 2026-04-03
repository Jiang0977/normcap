from __future__ import annotations

from types import SimpleNamespace

from PySide6 import QtCore, QtGui, QtWidgets

from normcap.annotate_prototype import app, editor
from normcap.annotate_prototype.models import (
    ArrowAnnotation,
    EffectAnnotation,
    NumberAnnotation,
    RectangleAnnotation,
    Tool,
)
from normcap.system.models import Rect


def _changed_pixels(
    before: QtGui.QImage,
    after: QtGui.QImage,
    left: int,
    top: int,
    right: int,
    bottom: int,
) -> int:
    changed = 0
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            if before.pixelColor(x, y) != after.pixelColor(x, y):
                changed += 1
    return changed


def _images_differ(left: QtGui.QImage, right: QtGui.QImage) -> bool:
    for y in range(left.height()):
        for x in range(left.width()):
            if left.pixelColor(x, y) != right.pixelColor(x, y):
                return True
    return False


def test_open_annotation_window_is_scheduled(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_close_capture_windows() -> None:
        calls["closed"] = True

    def fake_show_annotation_window(rect: Rect, screen_idx: int) -> None:
        calls["rect"] = rect
        calls["screen_idx"] = screen_idx

    def fake_single_shot(delay: int, callback) -> None:
        calls["delay"] = delay
        calls["callback"] = callback

    fake_app = SimpleNamespace(
        _close_capture_windows=fake_close_capture_windows,
        _show_annotation_window=fake_show_annotation_window,
    )
    monkeypatch.setattr(app.QtCore.QTimer, "singleShot", staticmethod(fake_single_shot))

    rect = Rect(left=1, top=2, right=3, bottom=4)
    app.PrototypeApp._open_annotation_window(fake_app, rect, 7)

    assert calls["closed"] is True
    assert calls["delay"] == 20

    callback = calls["callback"]
    callback()

    assert calls["rect"] == rect
    assert calls["screen_idx"] == 7


def test_annotation_window_emits_closed_signal(qtbot) -> None:
    image = QtGui.QImage(40, 30, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)

    with qtbot.waitSignal(window.com.on_closed, timeout=1000):
        window.close()


def test_blur_tool_creates_effect_annotation(qtbot) -> None:
    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.canvas.set_tool(Tool.BLUR)

    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(10, 10),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(30, 30))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(30, 30),
    )

    assert isinstance(window.canvas.annotations[-1], EffectAnnotation)
    assert window.canvas.annotations[-1].effect == Tool.BLUR


def test_number_tool_creates_sequential_annotations(qtbot) -> None:
    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.canvas.set_tool(Tool.NUMBER)

    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(10, 10),
    )
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(20, 20),
    )

    first = window.canvas.annotations[-2]
    second = window.canvas.annotations[-1]
    assert isinstance(first, NumberAnnotation)
    assert isinstance(second, NumberAnnotation)
    assert first.number == 1
    assert second.number == 2


def test_effect_strength_control_tracks_active_tool(qtbot) -> None:
    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.show()

    window._select_tool(Tool.BLUR)
    window._strength_spinbox.setValue(7)
    assert window.canvas.blur_strength == 7

    window._select_tool(Tool.MOSAIC)
    assert window._strength_spinbox_action.isVisible() is True
    window._strength_spinbox.setValue(13)
    assert window.canvas.mosaic_strength == 13

    window._select_tool(Tool.PEN)
    assert window._strength_spinbox_action.isVisible() is False


def test_effect_preview_changes_display_image(qtbot) -> None:
    image = QtGui.QImage(40, 40, QtGui.QImage.Format.Format_ARGB32)
    for y in range(40):
        for x in range(40):
            color = QtGui.QColor("black") if (x + y) % 2 == 0 else QtGui.QColor("white")
            image.setPixelColor(x, y, color)

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.canvas.set_tool(Tool.MOSAIC)
    window.canvas._drag_start = QtCore.QPointF(8, 8)
    window.canvas._drag_end = QtCore.QPointF(24, 24)

    display = window.canvas.display_image()

    assert _changed_pixels(image, display, 8, 8, 24, 24) > 0


def test_tool_actions_have_icons(qtbot) -> None:
    image = QtGui.QImage(40, 40, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)

    for action in window._tool_actions.values():
        assert action.icon().isNull() is False


def test_toolbar_uses_icon_only_buttons(qtbot) -> None:
    image = QtGui.QImage(40, 40, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)

    assert window._toolbar is not None
    assert (
        window._toolbar.toolButtonStyle()
        == QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly
    )
    labels = window.findChildren(QtWidgets.QLabel)
    assert all(label.text() != "Strength" for label in labels)


def test_tool_icons_have_distinct_checked_and_unchecked_states(qtbot) -> None:
    image = QtGui.QImage(40, 40, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)

    for action in window._tool_actions.values():
        off = action.icon().pixmap(
            24,
            24,
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.Off,
        ).toImage()
        on = action.icon().pixmap(
            24,
            24,
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.On,
        ).toImage()
        assert _images_differ(off, on) is True


def test_status_message_updates_with_tool_selection(qtbot) -> None:
    image = QtGui.QImage(40, 40, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.show()

    window._tool_actions[Tool.NUMBER].trigger()

    assert "Tool: Number" in window.statusBar().currentMessage()


def test_select_tool_moves_existing_rectangle_annotation(qtbot) -> None:
    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.show()

    window._select_tool(Tool.RECTANGLE)
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(10, 10),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(30, 30))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(30, 30),
    )

    window._select_tool(Tool.SELECT)
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(20, 20),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(40, 45))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(40, 45),
    )

    rectangle = window.canvas.annotations[-1]
    assert isinstance(rectangle, RectangleAnnotation)
    assert rectangle.rect.normalized() == QtCore.QRectF(30, 35, 20, 20)


def test_delete_key_removes_selected_annotation(qtbot) -> None:
    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.show()

    window._select_tool(Tool.RECTANGLE)
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(10, 10),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(30, 30))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(30, 30),
    )

    window._select_tool(Tool.SELECT)
    qtbot.mouseClick(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(20, 20),
    )
    qtbot.keyClick(window.canvas, QtCore.Qt.Key.Key_Delete)

    assert window.canvas.annotations == []


def test_select_tool_resizes_rectangle_from_bottom_right_handle(qtbot) -> None:
    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.show()

    window._select_tool(Tool.RECTANGLE)
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(10, 10),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(30, 30))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(30, 30),
    )

    window._select_tool(Tool.SELECT)
    qtbot.mouseClick(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(20, 20),
    )
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(30, 30),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(45, 40))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(45, 40),
    )

    rectangle = window.canvas.annotations[-1]
    assert isinstance(rectangle, RectangleAnnotation)
    assert rectangle.rect.normalized() == QtCore.QRectF(10, 10, 35, 30)


def test_select_tool_moves_existing_blur_region(qtbot) -> None:
    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.show()

    window._select_tool(Tool.BLUR)
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(10, 10),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(30, 30))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(30, 30),
    )

    window._select_tool(Tool.SELECT)
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(20, 20),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(35, 40))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(35, 40),
    )

    effect = window.canvas.annotations[-1]
    assert isinstance(effect, EffectAnnotation)
    assert effect.rect.normalized() == QtCore.QRectF(25, 30, 20, 20)


def test_select_tool_moves_existing_arrow_annotation(qtbot) -> None:
    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.show()

    window._select_tool(Tool.ARROW)
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(10, 10),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(30, 30))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(30, 30),
    )

    window._select_tool(Tool.SELECT)
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(20, 20),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(35, 40))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(35, 40),
    )

    arrow = window.canvas.annotations[-1]
    assert isinstance(arrow, ArrowAnnotation)
    assert arrow.start == QtCore.QPointF(25, 30)
    assert arrow.end == QtCore.QPointF(45, 50)


def test_select_tool_resizes_existing_blur_region(qtbot) -> None:
    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.show()

    window._select_tool(Tool.BLUR)
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(10, 10),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(30, 30))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(30, 30),
    )

    window._select_tool(Tool.SELECT)
    qtbot.mouseClick(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(20, 20),
    )
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(30, 30),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(45, 40))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(45, 40),
    )

    effect = window.canvas.annotations[-1]
    assert isinstance(effect, EffectAnnotation)
    assert effect.rect.normalized() == QtCore.QRectF(10, 10, 35, 30)


def test_select_tool_adjusts_arrow_end_handle(qtbot) -> None:
    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.show()

    window._select_tool(Tool.ARROW)
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(10, 10),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(30, 30))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(30, 30),
    )

    window._select_tool(Tool.SELECT)
    qtbot.mouseClick(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(20, 20),
    )
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(30, 30),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(45, 40))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(45, 40),
    )

    arrow = window.canvas.annotations[-1]
    assert isinstance(arrow, ArrowAnnotation)
    assert arrow.start == QtCore.QPointF(10, 10)
    assert arrow.end == QtCore.QPointF(45, 40)


def test_double_click_text_annotation_updates_text(monkeypatch, qtbot) -> None:
    responses = iter([("Old text", True), ("New text", True)])

    def fake_get_text(*_args, **_kwargs):
        return next(responses)

    monkeypatch.setattr(
        editor.QtWidgets.QInputDialog,
        "getText",
        staticmethod(fake_get_text),
    )

    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.show()

    window._select_tool(Tool.TEXT)
    qtbot.mouseClick(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(15, 25),
    )

    window._select_tool(Tool.SELECT)
    qtbot.mouseDClick(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(15, 25),
    )

    text_annotation = window.canvas.annotations[-1]
    assert text_annotation.text == "New text"


def test_double_click_number_annotation_reorders_numbers(monkeypatch, qtbot) -> None:
    def fake_get_int(*_args, **_kwargs):
        return (1, True)

    monkeypatch.setattr(
        editor.QtWidgets.QInputDialog,
        "getInt",
        staticmethod(fake_get_int),
    )

    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.show()

    window._select_tool(Tool.NUMBER)
    qtbot.mouseClick(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(10, 10),
    )
    qtbot.mouseClick(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(20, 20),
    )

    window._select_tool(Tool.SELECT)
    qtbot.mouseDClick(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(20, 20),
    )

    first = window.canvas.annotations[-2]
    second = window.canvas.annotations[-1]
    assert isinstance(first, NumberAnnotation)
    assert isinstance(second, NumberAnnotation)
    assert first.number == 2
    assert second.number == 1


def test_undo_and_redo_restore_moved_rectangle_annotation(qtbot) -> None:
    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.show()

    window._select_tool(Tool.RECTANGLE)
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(10, 10),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(30, 30))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(30, 30),
    )

    window._select_tool(Tool.SELECT)
    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(20, 20),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(35, 40))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(35, 40),
    )

    moved = window.canvas.annotations[-1]
    assert isinstance(moved, RectangleAnnotation)
    assert moved.rect.normalized() == QtCore.QRectF(25, 30, 20, 20)

    window.canvas.undo()

    restored = window.canvas.annotations[-1]
    assert isinstance(restored, RectangleAnnotation)
    assert restored.rect.normalized() == QtCore.QRectF(10, 10, 20, 20)

    window.canvas.redo()

    redone = window.canvas.annotations[-1]
    assert isinstance(redone, RectangleAnnotation)
    assert redone.rect.normalized() == QtCore.QRectF(25, 30, 20, 20)
