"""Annotation editor window for the screenshot prototype."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from PySide6 import QtCore, QtGui, QtWidgets

from normcap.annotate_prototype.models import (
    Annotation,
    ArrowAnnotation,
    EffectAnnotation,
    NumberAnnotation,
    RectangleAnnotation,
    StrokeAnnotation,
    TextAnnotation,
    Tool,
)
from normcap.annotate_prototype.render import (
    apply_effect_annotation,
    compose_image,
    draw_annotation,
)


class Communicate(QtCore.QObject):
    """Annotation window communication bus."""

    on_closed = QtCore.Signal()


_TOOLBAR_STYLE = """
QToolBar {
    spacing: 6px;
    padding: 6px 8px;
    background-color: rgba(248, 245, 250, 0.96);
    border: none;
    border-bottom: 1px solid rgba(53, 33, 63, 0.10);
}
QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
    color: #35213f;
    padding: 8px;
    min-width: 40px;
    min-height: 40px;
}
QToolButton:hover {
    background-color: rgba(53, 33, 63, 0.06);
    border-color: rgba(53, 33, 63, 0.10);
}
QToolButton:checked {
    background-color: %s;
    border: 1px solid rgba(53, 33, 63, 0.12);
    color: white;
}
QToolButton:pressed {
    background-color: rgba(53, 33, 63, 0.12);
}
QSpinBox {
    min-width: 68px;
    padding: 4px 6px;
}
"""

_ICON_SIZE = 28
_ICON_NORMAL_COLOR = QtGui.QColor("#35213f")
_ICON_ACTIVE_COLOR = QtGui.QColor("white")
_ICON_DISABLED_COLOR = QtGui.QColor("#9484a0")
_SELECTION_HANDLE_RADIUS = 8
_SELECTION_HANDLE_SIZE = 8


def _tool_accent_color(color: QtGui.QColor) -> str:
    highlight = QtGui.QColor(color)
    highlight.setAlpha(220)
    return highlight.name(QtGui.QColor.NameFormat.HexArgb)


def _draw_pen_icon(painter: QtGui.QPainter) -> None:
    painter.drawLine(6, 21, 15, 12)
    painter.drawLine(15, 12, 22, 5)
    painter.drawEllipse(QtCore.QPointF(7, 21), 1.2, 1.2)


def _draw_select_icon(painter: QtGui.QPainter) -> None:
    painter.drawLine(6, 4, 6, 24)
    painter.drawLine(6, 4, 20, 14)
    painter.drawLine(20, 14, 13, 14)
    painter.drawLine(20, 14, 16, 20)


def _draw_rectangle_icon(painter: QtGui.QPainter) -> None:
    painter.drawRect(5, 6, 18, 15)


def _draw_arrow_icon(painter: QtGui.QPainter) -> None:
    painter.drawLine(5, 21, 21, 7)
    painter.drawLine(14, 7, 21, 7)
    painter.drawLine(21, 7, 21, 14)


def _draw_text_icon(
    painter: QtGui.QPainter,
    text: str,
    color: QtGui.QColor | None = None,
) -> None:
    if color is not None:
        painter.setPen(color)
    font = painter.font()
    font.setBold(True)
    font.setPointSize(14)
    painter.setFont(font)
    painter.drawText(
        QtCore.QRect(0, 0, 28, 28),
        QtCore.Qt.AlignmentFlag.AlignCenter,
        text,
    )


def _draw_number_icon(painter: QtGui.QPainter) -> None:
    painter.drawEllipse(5, 5, 18, 18)
    _draw_text_icon(painter, "1")


def _draw_blur_icon(painter: QtGui.QPainter) -> None:
    for radius in (4, 7):
        painter.drawEllipse(QtCore.QPointF(14, 14), radius, radius)


def _draw_mosaic_icon(painter: QtGui.QPainter) -> None:
    painter.setBrush(painter.pen().color())
    for row in range(3):
        for col in range(3):
            if (row + col) % 2 == 0:
                painter.drawRect(5 + col * 6, 5 + row * 6, 4, 4)


def _draw_color_icon(painter: QtGui.QPainter, color: QtGui.QColor) -> None:
    painter.setBrush(color)
    painter.drawEllipse(5, 5, 18, 18)


def _draw_undo_icon(painter: QtGui.QPainter) -> None:
    path = QtGui.QPainterPath(QtCore.QPointF(20, 19))
    path.cubicTo(14, 19, 9.5, 18, 8.7, 13.8)
    path.cubicTo(8.1, 10.4, 10.8, 8, 15.2, 8)
    path.lineTo(21, 8)
    painter.drawPath(path)
    painter.drawLine(8.5, 8, 12.8, 4)
    painter.drawLine(8.5, 8, 12.8, 12)


def _draw_redo_icon(painter: QtGui.QPainter) -> None:
    path = QtGui.QPainterPath(QtCore.QPointF(8, 19))
    path.cubicTo(14, 19, 18.5, 18, 19.3, 13.8)
    path.cubicTo(19.9, 10.4, 17.2, 8, 12.8, 8)
    path.lineTo(7, 8)
    painter.drawPath(path)
    painter.drawLine(19.5, 8, 15.2, 4)
    painter.drawLine(19.5, 8, 15.2, 12)


def _draw_copy_icon(painter: QtGui.QPainter) -> None:
    painter.drawRect(9, 5, 12, 14)
    painter.drawRect(5, 9, 12, 14)


def _draw_save_icon(painter: QtGui.QPainter) -> None:
    painter.drawRect(5, 5, 18, 18)
    painter.drawLine(9, 5, 9, 11)
    painter.drawLine(19, 5, 19, 11)
    painter.drawRect(9, 15, 10, 6)


_ICON_DRAWERS = {
    Tool.SELECT: _draw_select_icon,
    Tool.PEN: _draw_pen_icon,
    Tool.RECTANGLE: _draw_rectangle_icon,
    Tool.ARROW: _draw_arrow_icon,
    Tool.TEXT: lambda painter: _draw_text_icon(painter, "T"),
    Tool.NUMBER: _draw_number_icon,
    Tool.BLUR: _draw_blur_icon,
    Tool.MOSAIC: _draw_mosaic_icon,
}

IconDrawer = Callable[[QtGui.QPainter], None]


def _build_icon_pixmap(drawer: IconDrawer, color: QtGui.QColor) -> QtGui.QPixmap:
    pixmap = QtGui.QPixmap(_ICON_SIZE, _ICON_SIZE)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    pen = QtGui.QPen(QtGui.QColor(color), 2)
    pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    drawer(painter)

    painter.end()
    return pixmap


def _build_stateful_icon(drawer: IconDrawer) -> QtGui.QIcon:
    icon = QtGui.QIcon()
    icon.addPixmap(
        _build_icon_pixmap(drawer, _ICON_NORMAL_COLOR),
        QtGui.QIcon.Mode.Normal,
        QtGui.QIcon.State.Off,
    )
    icon.addPixmap(
        _build_icon_pixmap(drawer, _ICON_DISABLED_COLOR),
        QtGui.QIcon.Mode.Disabled,
        QtGui.QIcon.State.Off,
    )
    icon.addPixmap(
        _build_icon_pixmap(drawer, _ICON_ACTIVE_COLOR),
        QtGui.QIcon.Mode.Normal,
        QtGui.QIcon.State.On,
    )
    icon.addPixmap(
        _build_icon_pixmap(drawer, _ICON_ACTIVE_COLOR),
        QtGui.QIcon.Mode.Disabled,
        QtGui.QIcon.State.On,
    )
    return icon


def _build_single_state_icon(drawer: IconDrawer) -> QtGui.QIcon:
    icon = QtGui.QIcon()
    icon.addPixmap(
        _build_icon_pixmap(drawer, _ICON_NORMAL_COLOR),
        QtGui.QIcon.Mode.Normal,
        QtGui.QIcon.State.Off,
    )
    icon.addPixmap(
        _build_icon_pixmap(drawer, _ICON_DISABLED_COLOR),
        QtGui.QIcon.Mode.Disabled,
        QtGui.QIcon.State.Off,
    )
    return icon


def _build_tool_icon(tool: Tool) -> QtGui.QIcon:
    try:
        drawer = _ICON_DRAWERS[tool]
    except KeyError as exc:
        raise TypeError(f"Unsupported tool icon: {tool!r}") from exc
    return _build_stateful_icon(drawer)


def _build_color_action_icon(color: QtGui.QColor) -> QtGui.QIcon:
    return _build_single_state_icon(lambda painter: _draw_color_icon(painter, color))


def _arrow_hit_path(annotation: ArrowAnnotation) -> QtGui.QPainterPath:
    path = QtGui.QPainterPath(annotation.start)
    path.lineTo(annotation.end)
    stroker = QtGui.QPainterPathStroker()
    stroker.setWidth(max(12, annotation.width + 6))
    stroker.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
    stroker.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
    return stroker.createStroke(path)


def _text_annotation_rect(annotation: TextAnnotation) -> QtCore.QRectF:
    font = QtGui.QFont()
    font.setPointSize(annotation.font_size)
    font.setBold(True)
    metrics = QtGui.QFontMetricsF(font)
    rect = metrics.tightBoundingRect(annotation.text)
    rect.translate(annotation.position)
    return rect.adjusted(-4, -4, 4, 4)


def _number_annotation_rect(annotation: NumberAnnotation) -> QtCore.QRectF:
    radius = annotation.radius + 4
    return QtCore.QRectF(
        annotation.position.x() - radius,
        annotation.position.y() - radius,
        radius * 2,
        radius * 2,
    )


def _clone_annotation(annotation: Annotation) -> Annotation:
    if isinstance(annotation, StrokeAnnotation):
        return StrokeAnnotation(
            points=[QtCore.QPointF(point) for point in annotation.points],
            color=QtGui.QColor(annotation.color),
            width=annotation.width,
        )

    if isinstance(annotation, RectangleAnnotation):
        return RectangleAnnotation(
            rect=QtCore.QRectF(annotation.rect),
            color=QtGui.QColor(annotation.color),
            width=annotation.width,
        )

    if isinstance(annotation, ArrowAnnotation):
        return ArrowAnnotation(
            start=QtCore.QPointF(annotation.start),
            end=QtCore.QPointF(annotation.end),
            color=QtGui.QColor(annotation.color),
            width=annotation.width,
        )

    if isinstance(annotation, TextAnnotation):
        return TextAnnotation(
            position=QtCore.QPointF(annotation.position),
            text=annotation.text,
            color=QtGui.QColor(annotation.color),
            font_size=annotation.font_size,
        )

    if isinstance(annotation, NumberAnnotation):
        return NumberAnnotation(
            position=QtCore.QPointF(annotation.position),
            number=annotation.number,
            color=QtGui.QColor(annotation.color),
            radius=annotation.radius,
            width=annotation.width,
        )

    if isinstance(annotation, EffectAnnotation):
        return EffectAnnotation(
            rect=QtCore.QRectF(annotation.rect),
            effect=annotation.effect,
            strength=annotation.strength,
            color=QtGui.QColor(annotation.color),
            width=annotation.width,
        )

    raise TypeError(f"Unsupported annotation type: {type(annotation)!r}")


def _clone_annotations(annotations: list[Annotation]) -> list[Annotation]:
    return [_clone_annotation(annotation) for annotation in annotations]


class AnnotationCanvas(QtWidgets.QWidget):
    """Canvas displaying the cropped screenshot and user annotations."""

    def __init__(self, image: QtGui.QImage) -> None:
        super().__init__()
        self._base_image = image
        self.annotations: list[Annotation] = []
        self.tool = Tool.PEN
        self.color = QtGui.QColor("#ff2e88")
        self.stroke_width = 4
        self.font_size = 24
        self.blur_strength = 10
        self.mosaic_strength = 16

        self._stroke_points: list[QtCore.QPointF] | None = None
        self._drag_start: QtCore.QPointF | None = None
        self._drag_end: QtCore.QPointF | None = None
        self._selected_index: int | None = None
        self._selection_drag_origin: QtCore.QPointF | None = None
        self._selection_origin_annotation: Annotation | None = None
        self._selection_mode: str | None = None
        self._selection_snapshot: list[Annotation] | None = None
        self._selection_history_committed = False
        self._undo_stack: list[list[Annotation]] = []
        self._redo_stack: list[list[Annotation]] = []

        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(self._base_image.size())

    @property
    def base_image(self) -> QtGui.QImage:
        return self._base_image

    def set_tool(self, tool: Tool) -> None:
        self.tool = tool
        if tool != Tool.SELECT:
            self._selected_index = None
            self._selection_drag_origin = None
            self._selection_origin_annotation = None
            self._selection_mode = None
            self._selection_snapshot = None
            self._selection_history_committed = False
            self.update()

    def set_color(self, color: QtGui.QColor) -> None:
        self.color = color
        self.update()

    def current_effect_strength(self) -> int:
        if self.tool == Tool.BLUR:
            return self.blur_strength
        if self.tool == Tool.MOSAIC:
            return self.mosaic_strength
        return self.blur_strength

    def set_current_effect_strength(self, value: int) -> None:
        if self.tool == Tool.MOSAIC:
            self.mosaic_strength = value
        else:
            self.blur_strength = value
        self.update()

    def undo(self) -> None:
        if not self._undo_stack:
            return

        self._redo_stack.append(_clone_annotations(self.annotations))
        self.annotations = _clone_annotations(self._undo_stack.pop())
        self._selected_index = None
        self._selection_drag_origin = None
        self._selection_origin_annotation = None
        self._selection_mode = None
        self._selection_snapshot = None
        self._selection_history_committed = False
        self.update()

    def redo(self) -> None:
        if not self._redo_stack:
            return

        self._undo_stack.append(_clone_annotations(self.annotations))
        self.annotations = _clone_annotations(self._redo_stack.pop())
        self._selected_index = None
        self._selection_drag_origin = None
        self._selection_origin_annotation = None
        self._selection_mode = None
        self._selection_snapshot = None
        self._selection_history_committed = False
        self.update()

    def _record_history(self, snapshot: list[Annotation] | None = None) -> None:
        state = self.annotations if snapshot is None else snapshot
        self._undo_stack.append(_clone_annotations(state))
        self._redo_stack.clear()

    def _record_selection_history_if_needed(self, position: QtCore.QPointF) -> None:
        if (
            self._selection_snapshot is None
            or self._selection_history_committed
            or self._selection_drag_origin is None
        ):
            return

        if QtCore.QLineF(position, self._selection_drag_origin).length() == 0:
            return

        self._record_history(self._selection_snapshot)
        self._selection_history_committed = True

    def rendered_image(self) -> QtGui.QImage:
        return compose_image(self._base_image, self.annotations)

    def current_preview_annotation(self) -> Annotation | None:
        """Build the annotation currently being previewed while dragging."""
        if self._stroke_points:
            return StrokeAnnotation(
                points=self._stroke_points.copy(),
                color=QtGui.QColor(self.color),
                width=self.stroke_width,
            )

        if self._drag_start is None or self._drag_end is None:
            return None

        if self.tool == Tool.RECTANGLE:
            return RectangleAnnotation(
                rect=QtCore.QRectF(self._drag_start, self._drag_end),
                color=QtGui.QColor(self.color),
                width=self.stroke_width,
            )

        if self.tool in {Tool.BLUR, Tool.MOSAIC}:
            strength = (
                self.blur_strength if self.tool == Tool.BLUR else self.mosaic_strength
            )
            return EffectAnnotation(
                rect=QtCore.QRectF(self._drag_start, self._drag_end),
                effect=self.tool,
                strength=strength,
                color=QtGui.QColor(self.color),
                width=max(2, self.stroke_width - 1),
            )

        if self.tool == Tool.ARROW:
            return ArrowAnnotation(
                start=self._drag_start,
                end=self._drag_end,
                color=QtGui.QColor(self.color),
                width=self.stroke_width,
            )

        return None

    def display_image(self) -> QtGui.QImage:
        """Build the image currently shown on the canvas, including effect previews."""
        image = self.rendered_image()
        preview = self.current_preview_annotation()
        if isinstance(preview, EffectAnnotation):
            image = apply_effect_annotation(image=image, annotation=preview)
        return image

    def _annotation_at(self, position: QtCore.QPointF) -> int | None:
        for index in range(len(self.annotations) - 1, -1, -1):
            annotation = self.annotations[index]
            if isinstance(annotation, (RectangleAnnotation, EffectAnnotation)) and (
                annotation.rect.normalized().adjusted(-4, -4, 4, 4).contains(position)
            ):
                return index
            if isinstance(annotation, ArrowAnnotation) and _arrow_hit_path(
                annotation
            ).contains(position):
                return index
            if isinstance(annotation, TextAnnotation) and _text_annotation_rect(
                annotation
            ).contains(position):
                return index
            if isinstance(annotation, NumberAnnotation) and (
                QtCore.QLineF(position, annotation.position).length()
                <= annotation.radius + 4
            ):
                return index
        return None

    def _selection_outline_path(self, annotation: Annotation) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        if isinstance(annotation, (RectangleAnnotation, EffectAnnotation)):
            path.addRect(annotation.rect.normalized().adjusted(-3, -3, 3, 3))
            return path

        if isinstance(annotation, ArrowAnnotation):
            path.moveTo(annotation.start)
            path.lineTo(annotation.end)
            return path

        if isinstance(annotation, TextAnnotation):
            path.addRoundedRect(_text_annotation_rect(annotation), 4, 4)
            return path

        if isinstance(annotation, NumberAnnotation):
            path.addEllipse(_number_annotation_rect(annotation))
            return path

        return path

    def _annotation_handles(self, annotation: Annotation) -> dict[str, QtCore.QPointF]:
        if isinstance(annotation, (RectangleAnnotation, EffectAnnotation)):
            rect = annotation.rect.normalized()
            return {
                "resize_top_left": rect.topLeft(),
                "resize_top_right": rect.topRight(),
                "resize_bottom_left": rect.bottomLeft(),
                "resize_bottom_right": rect.bottomRight(),
            }

        if isinstance(annotation, ArrowAnnotation):
            return {
                "move_start": annotation.start,
                "move_end": annotation.end,
            }

        return {}

    def _selected_handle_at(self, position: QtCore.QPointF) -> str | None:
        if self._selected_index is None:
            return None

        annotation = self.annotations[self._selected_index]
        for handle, point in self._annotation_handles(annotation).items():
            if QtCore.QLineF(position, point).length() <= _SELECTION_HANDLE_RADIUS:
                return handle
        return None

    def _drag_rect_like_annotation(
        self,
        annotation: RectangleAnnotation | EffectAnnotation,
        position: QtCore.QPointF,
        delta: QtCore.QPointF,
    ) -> bool:
        if self._selected_index is None:
            return False

        if self._selection_mode == "move":
            rect = QtCore.QRectF(annotation.rect)
            rect.translate(delta)
            self.annotations[self._selected_index] = replace(annotation, rect=rect)
            self.update()
            return True

        rect = annotation.rect.normalized()
        if self._selection_mode == "resize_top_left":
            rect.setTopLeft(position)
        elif self._selection_mode == "resize_top_right":
            rect.setTopRight(position)
        elif self._selection_mode == "resize_bottom_left":
            rect.setBottomLeft(position)
        elif self._selection_mode == "resize_bottom_right":
            rect.setBottomRight(position)
        else:
            return False

        self.annotations[self._selected_index] = replace(annotation, rect=rect)
        self.update()
        return True

    def _drag_arrow_annotation(
        self,
        annotation: ArrowAnnotation,
        position: QtCore.QPointF,
        delta: QtCore.QPointF,
    ) -> bool:
        if self._selected_index is None:
            return False

        if self._selection_mode == "move":
            self.annotations[self._selected_index] = replace(
                annotation,
                start=annotation.start + delta,
                end=annotation.end + delta,
            )
            self.update()
            return True

        if self._selection_mode == "move_start":
            self.annotations[self._selected_index] = replace(
                annotation,
                start=position,
            )
            self.update()
            return True

        if self._selection_mode == "move_end":
            self.annotations[self._selected_index] = replace(
                annotation,
                end=position,
            )
            self.update()
            return True

        return False

    def _drag_point_annotation(
        self,
        annotation: TextAnnotation | NumberAnnotation,
        delta: QtCore.QPointF,
    ) -> bool:
        if self._selected_index is None or self._selection_mode != "move":
            return False

        self.annotations[self._selected_index] = replace(
            annotation,
            position=annotation.position + delta,
        )
        self.update()
        return True

    def _drag_selected_annotation(self, position: QtCore.QPointF) -> None:
        if (
            self._selected_index is None
            or self._selection_drag_origin is None
            or self._selection_origin_annotation is None
            or self._selection_mode is None
        ):
            return

        annotation = self._selection_origin_annotation
        delta = position - self._selection_drag_origin
        self._record_selection_history_if_needed(position)

        if isinstance(annotation, (RectangleAnnotation, EffectAnnotation)) and (
            self._drag_rect_like_annotation(annotation, position, delta)
        ):
            return

        if isinstance(annotation, ArrowAnnotation) and self._drag_arrow_annotation(
            annotation, position, delta
        ):
            return

        if isinstance(annotation, (TextAnnotation, NumberAnnotation)) and (
            self._drag_point_annotation(annotation, delta)
        ):
            return

        if self._selection_mode is None:
            return

    def _edit_text_annotation(self, index: int, annotation: TextAnnotation) -> None:
        text, accepted = QtWidgets.QInputDialog.getText(
            self,
            "Edit Text",
            "Text:",
            text=annotation.text,
        )
        if accepted and text.strip() and text.strip() != annotation.text:
            self._record_history()
            self.annotations[index] = replace(annotation, text=text.strip())
            self.update()

    def _reorder_number_annotation(self, index: int, target_number: int) -> None:
        number_indices = [
            annotation_index
            for annotation_index, current in enumerate(self.annotations)
            if isinstance(current, NumberAnnotation)
        ]
        if index not in number_indices:
            return

        current_position = number_indices.index(index)
        target_position = max(0, min(len(number_indices) - 1, target_number - 1))
        annotation_index = number_indices.pop(current_position)
        number_indices.insert(target_position, annotation_index)

        for number, annotation_index in enumerate(number_indices, start=1):
            current = self.annotations[annotation_index]
            if not isinstance(current, NumberAnnotation):
                continue
            self.annotations[annotation_index] = replace(current, number=number)

    def _edit_number_annotation(
        self, index: int, annotation: NumberAnnotation
    ) -> None:
        number_count = sum(
            isinstance(current, NumberAnnotation) for current in self.annotations
        )
        target_number, accepted = QtWidgets.QInputDialog.getInt(
            self,
            "Reorder Number",
            "Number:",
            annotation.number,
            1,
            number_count,
        )
        if not accepted:
            return

        if target_number == annotation.number:
            return

        self._record_history()
        self._reorder_number_annotation(index, target_number)
        self.update()

    def _begin_selection_interaction(self, position: QtCore.QPointF) -> bool:
        handle = self._selected_handle_at(position)
        if handle is not None and self._selected_index is not None:
            self._selection_drag_origin = position
            self._selection_origin_annotation = self.annotations[self._selected_index]
            self._selection_mode = handle
            self._selection_snapshot = _clone_annotations(self.annotations)
            self._selection_history_committed = False
            self.update()
            return True

        hit_index = self._annotation_at(position)
        self._selected_index = hit_index
        if hit_index is None:
            self._selection_drag_origin = None
            self._selection_origin_annotation = None
            self._selection_mode = None
            self._selection_snapshot = None
            self._selection_history_committed = False
            self.update()
            return True

        self._selection_drag_origin = position
        self._selection_origin_annotation = self.annotations[hit_index]
        self._selection_mode = "move"
        self._selection_snapshot = _clone_annotations(self.annotations)
        self._selection_history_committed = False
        self.update()
        return True

    def _paint_preview(self, painter: QtGui.QPainter) -> None:
        preview = self.current_preview_annotation()
        if preview is None:
            return

        if isinstance(preview, EffectAnnotation):
            draw_annotation(painter, preview)
            return

        draw_annotation(painter, preview)

    def _paint_selection(self, painter: QtGui.QPainter) -> None:
        if self.tool != Tool.SELECT or self._selected_index is None:
            return

        annotation = self.annotations[self._selected_index]
        highlight = QtGui.QColor(self.color)
        highlight.setAlpha(230)
        pen = QtGui.QPen(
            highlight,
            2,
            QtCore.Qt.PenStyle.DashLine,
            QtCore.Qt.PenCapStyle.RoundCap,
            QtCore.Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawPath(self._selection_outline_path(annotation))

        handle_pen = QtGui.QPen(highlight, 1.5)
        handle_brush = QtGui.QBrush(QtGui.QColor("white"))
        for point in self._annotation_handles(annotation).values():
            handle_rect = QtCore.QRectF(
                point.x() - _SELECTION_HANDLE_SIZE / 2,
                point.y() - _SELECTION_HANDLE_SIZE / 2,
                _SELECTION_HANDLE_SIZE,
                _SELECTION_HANDLE_SIZE,
            )
            painter.setPen(handle_pen)
            painter.setBrush(handle_brush)
            painter.drawRect(handle_rect)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.drawImage(0, 0, self.display_image())
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        self._paint_preview(painter)
        self._paint_selection(painter)
        painter.end()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:  # noqa: N802
        if (
            self.tool == Tool.SELECT
            and self._selected_index is not None
            and event.key()
            in {QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace}
        ):
            self._record_history()
            self.annotations.pop(self._selected_index)
            self._selected_index = None
            self._selection_drag_origin = None
            self._selection_origin_annotation = None
            self._selection_mode = None
            self._selection_snapshot = None
            self._selection_history_committed = False
            self.update()
            event.accept()
            return

        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        super().mouseDoubleClickEvent(event)
        if (
            self.tool != Tool.SELECT
            or event.button() != QtCore.Qt.MouseButton.LeftButton
        ):
            return

        index = self._annotation_at(event.position())
        if index is None:
            return

        self._selected_index = index
        annotation = self.annotations[index]
        if isinstance(annotation, TextAnnotation):
            self._edit_text_annotation(index, annotation)
            return

        if isinstance(annotation, NumberAnnotation):
            self._edit_number_annotation(index, annotation)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        super().mousePressEvent(event)
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
        position = event.position()
        if self.tool == Tool.SELECT and self._begin_selection_interaction(position):
            return

        if self.tool == Tool.PEN:
            self._stroke_points = [position]
            return

        if self.tool == Tool.TEXT:
            text, accepted = QtWidgets.QInputDialog.getText(
                self,
                "Insert Text",
                "Text:",
            )
            if accepted and text.strip():
                self._record_history()
                self.annotations.append(
                    TextAnnotation(
                        position=position,
                        text=text.strip(),
                        color=QtGui.QColor(self.color),
                        font_size=self.font_size,
                    )
                )
                self.update()
            return

        if self.tool == Tool.NUMBER:
            next_number = (
                sum(isinstance(a, NumberAnnotation) for a in self.annotations) + 1
            )
            self._record_history()
            self.annotations.append(
                NumberAnnotation(
                    position=position,
                    number=next_number,
                    color=QtGui.QColor(self.color),
                    radius=18,
                    width=max(2, self.stroke_width - 1),
                )
            )
            self.update()
            return

        self._drag_start = position
        self._drag_end = position

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        super().mouseMoveEvent(event)
        position = event.position()
        if self._stroke_points is not None:
            self._stroke_points.append(position)
            self.update()
            return

        if self.tool == Tool.SELECT:
            self._drag_selected_annotation(position)
            return

        if self._drag_start is not None:
            self._drag_end = position
            self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        position = event.position()

        if self.tool == Tool.SELECT:
            self._drag_selected_annotation(position)
            self._selection_drag_origin = None
            self._selection_origin_annotation = None
            self._selection_mode = None
            self._selection_snapshot = None
            self._selection_history_committed = False
            return

        if self._stroke_points is not None:
            self._stroke_points.append(position)
            self._record_history()
            self.annotations.append(
                StrokeAnnotation(
                    points=self._stroke_points.copy(),
                    color=QtGui.QColor(self.color),
                    width=self.stroke_width,
                )
            )
            self._stroke_points = None
            self.update()
            return

        if self._drag_start is None:
            return

        self._drag_end = position
        if self.tool == Tool.RECTANGLE:
            self._record_history()
            self.annotations.append(
                RectangleAnnotation(
                    rect=QtCore.QRectF(self._drag_start, self._drag_end),
                    color=QtGui.QColor(self.color),
                    width=self.stroke_width,
                )
            )
        elif self.tool in {Tool.BLUR, Tool.MOSAIC}:
            strength = (
                self.blur_strength if self.tool == Tool.BLUR else self.mosaic_strength
            )
            self._record_history()
            self.annotations.append(
                EffectAnnotation(
                    rect=QtCore.QRectF(self._drag_start, self._drag_end),
                    effect=self.tool,
                    strength=strength,
                    color=QtGui.QColor(self.color),
                    width=max(2, self.stroke_width - 1),
                )
            )
        elif self.tool == Tool.ARROW:
            self._record_history()
            self.annotations.append(
                ArrowAnnotation(
                    start=self._drag_start,
                    end=self._drag_end,
                    color=QtGui.QColor(self.color),
                    width=self.stroke_width,
                )
            )

        self._drag_start = None
        self._drag_end = None
        self.update()


class AnnotationWindow(QtWidgets.QMainWindow):
    """Top-level annotation editor window."""

    def __init__(self, image: QtGui.QImage) -> None:
        super().__init__()
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.com = Communicate(parent=self)
        self.setWindowTitle("NormCap Annotate Prototype")
        self.resize(
            min(max(image.width() + 80, 960), 1600),
            min(max(image.height() + 140, 720), 1100),
        )

        self.canvas = AnnotationCanvas(image=image)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setWidgetResizable(False)
        self.setCentralWidget(self.scroll_area)

        self._tool_actions: dict[Tool, QtGui.QAction] = {}
        self._toolbar: QtWidgets.QToolBar | None = None
        self._color_action: QtGui.QAction | None = None
        self._create_toolbar()
        self._apply_toolbar_style()
        self.statusBar().showMessage("Select a tool and annotate the screenshot.")

    def _add_tool_action(
        self,
        toolbar: QtWidgets.QToolBar,
        text: str,
        tool: Tool,
        shortcut: str,
    ) -> None:
        action = QtGui.QAction(text, self)
        action.setObjectName(f"tool_{tool.value}")
        action.setCheckable(True)
        action.setShortcut(shortcut)
        action.setIcon(_build_tool_icon(tool))
        action.setToolTip(f"{text} ({shortcut})")
        action.triggered.connect(lambda _checked, t=tool: self._select_tool(t))
        toolbar.addAction(action)
        self._tool_actions[tool] = action

    def _add_annotation_tool_actions(self, toolbar: QtWidgets.QToolBar) -> None:
        self._add_tool_action(toolbar, "Select", Tool.SELECT, "V")
        self._add_tool_action(toolbar, "Pen", Tool.PEN, "P")
        self._add_tool_action(toolbar, "Rectangle", Tool.RECTANGLE, "R")
        self._add_tool_action(toolbar, "Arrow", Tool.ARROW, "A")
        self._add_tool_action(toolbar, "Text", Tool.TEXT, "T")
        self._add_tool_action(toolbar, "Number", Tool.NUMBER, "N")
        self._add_tool_action(toolbar, "Blur", Tool.BLUR, "B")
        self._add_tool_action(toolbar, "Mosaic", Tool.MOSAIC, "M")

    def _create_toolbar_action(
        self,
        text: str,
        icon_drawer: IconDrawer,
        shortcut: QtGui.QKeySequence.StandardKey | None,
        tooltip: str,
        handler: Callable[[], None],
    ) -> QtGui.QAction:
        action = QtGui.QAction(text, self)
        action.setIcon(_build_single_state_icon(icon_drawer))
        action.setToolTip(tooltip)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(handler)
        return action

    def _add_toolbar_utility_actions(self, toolbar: QtWidgets.QToolBar) -> None:
        color_action = QtGui.QAction("Color", self)
        color_action.setIcon(_build_color_action_icon(self.canvas.color))
        color_action.setToolTip("Color")
        color_action.triggered.connect(self._pick_color)
        toolbar.addAction(color_action)
        self._color_action = color_action

        self._strength_spinbox = QtWidgets.QSpinBox()
        self._strength_spinbox.setObjectName("strength_spinbox")
        self._strength_spinbox.setRange(2, 32)
        self._strength_spinbox.setSingleStep(1)
        self._strength_spinbox.setValue(self.canvas.current_effect_strength())
        self._strength_spinbox.setToolTip("Effect strength")
        self._strength_spinbox.valueChanged.connect(
            self.canvas.set_current_effect_strength
        )
        self._strength_spinbox_action = toolbar.addWidget(self._strength_spinbox)

        toolbar.addAction(
            self._create_toolbar_action(
                text="Undo",
                icon_drawer=_draw_undo_icon,
                shortcut=QtGui.QKeySequence.StandardKey.Undo,
                tooltip="Undo",
                handler=self.canvas.undo,
            )
        )
        toolbar.addAction(
            self._create_toolbar_action(
                text="Redo",
                icon_drawer=_draw_redo_icon,
                shortcut=QtGui.QKeySequence.StandardKey.Redo,
                tooltip="Redo",
                handler=self.canvas.redo,
            )
        )
        toolbar.addAction(
            self._create_toolbar_action(
                text="Copy",
                icon_drawer=_draw_copy_icon,
                shortcut=QtGui.QKeySequence.StandardKey.Copy,
                tooltip="Copy",
                handler=self.copy_image,
            )
        )
        toolbar.addAction(
            self._create_toolbar_action(
                text="Save",
                icon_drawer=_draw_save_icon,
                shortcut=QtGui.QKeySequence.StandardKey.Save,
                tooltip="Save",
                handler=self.save_image,
            )
        )

    def _create_toolbar(self) -> None:
        toolbar = QtWidgets.QToolBar("Tools")
        toolbar.setMovable(False)
        toolbar.setIconSize(QtCore.QSize(24, 24))
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.addToolBar(toolbar)
        self._toolbar = toolbar

        self._add_annotation_tool_actions(toolbar)

        toolbar.addSeparator()
        self._add_toolbar_utility_actions(toolbar)

        self._select_tool(Tool.PEN)

    def _apply_toolbar_style(self) -> None:
        if self._toolbar is None:
            return
        self._toolbar.setStyleSheet(
            _TOOLBAR_STYLE % _tool_accent_color(self.canvas.color)
        )

    def _select_tool(self, tool: Tool) -> None:
        for current_tool, action in self._tool_actions.items():
            action.blockSignals(True)
            action.setChecked(current_tool == tool)
            action.blockSignals(False)
        self.canvas.set_tool(tool)
        self._sync_effect_controls(tool)
        self._update_status(tool)

    def _sync_effect_controls(self, tool: Tool) -> None:
        is_effect_tool = tool in {Tool.BLUR, Tool.MOSAIC}
        self._strength_spinbox_action.setVisible(is_effect_tool)
        self._strength_spinbox.setVisible(is_effect_tool)
        if not is_effect_tool:
            return

        self._strength_spinbox.blockSignals(True)
        self._strength_spinbox.setValue(self.canvas.current_effect_strength())
        self._strength_spinbox.blockSignals(False)

    def _update_status(self, tool: Tool) -> None:
        descriptions = {
            Tool.SELECT: "Select and move annotations",
            Tool.PEN: "Freehand drawing",
            Tool.RECTANGLE: "Draw rectangles",
            Tool.ARROW: "Draw arrows",
            Tool.TEXT: "Insert text",
            Tool.NUMBER: "Place numbered markers",
            Tool.BLUR: "Blur selected areas",
            Tool.MOSAIC: "Pixelate selected areas",
        }
        self.statusBar().showMessage(
            f"Tool: {tool.value.title()} | {descriptions[tool]}", 4000
        )

    def _pick_color(self) -> None:
        color = QtWidgets.QColorDialog.getColor(self.canvas.color, self, "Pick Color")
        if color.isValid():
            self.canvas.set_color(color)
            if self._color_action is not None:
                self._color_action.setIcon(_build_color_action_icon(color))
            self._apply_toolbar_style()

    def copy_image(self) -> None:
        QtGui.QGuiApplication.clipboard().setImage(self.canvas.rendered_image())
        self.statusBar().showMessage("Annotated image copied to clipboard.", 3000)

    def save_image(self) -> None:
        target, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Annotated Screenshot",
            str(QtCore.QDir.homePath() + "/annotated-screenshot.png"),
            "PNG Images (*.png)",
        )
        if not target:
            return

        self.canvas.rendered_image().save(target)
        self.statusBar().showMessage(f"Saved to {target}", 3000)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.com.on_closed.emit()
        super().closeEvent(event)
