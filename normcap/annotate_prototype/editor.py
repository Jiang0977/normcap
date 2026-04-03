"""Annotation editor window for the screenshot prototype."""

from __future__ import annotations

from collections.abc import Callable

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


def _tool_accent_color(color: QtGui.QColor) -> str:
    highlight = QtGui.QColor(color)
    highlight.setAlpha(220)
    return highlight.name(QtGui.QColor.NameFormat.HexArgb)


def _draw_pen_icon(painter: QtGui.QPainter) -> None:
    painter.drawLine(6, 21, 15, 12)
    painter.drawLine(15, 12, 22, 5)
    painter.drawEllipse(QtCore.QPointF(7, 21), 1.2, 1.2)


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


def _draw_copy_icon(painter: QtGui.QPainter) -> None:
    painter.drawRect(9, 5, 12, 14)
    painter.drawRect(5, 9, 12, 14)


def _draw_save_icon(painter: QtGui.QPainter) -> None:
    painter.drawRect(5, 5, 18, 18)
    painter.drawLine(9, 5, 9, 11)
    painter.drawLine(19, 5, 19, 11)
    painter.drawRect(9, 15, 10, 6)


_ICON_DRAWERS = {
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

        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        self.setFixedSize(self._base_image.size())

    @property
    def base_image(self) -> QtGui.QImage:
        return self._base_image

    def set_tool(self, tool: Tool) -> None:
        self.tool = tool

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
        if self.annotations:
            self.annotations.pop()
            self.update()

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

    def _paint_preview(self, painter: QtGui.QPainter) -> None:
        preview = self.current_preview_annotation()
        if preview is None:
            return

        if isinstance(preview, EffectAnnotation):
            draw_annotation(painter, preview)
            return

        draw_annotation(painter, preview)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.drawImage(0, 0, self.display_image())
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        self._paint_preview(painter)
        painter.end()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        super().mousePressEvent(event)
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        position = event.position()
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

        if self._drag_start is not None:
            self._drag_end = position
            self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        position = event.position()

        if self._stroke_points is not None:
            self._stroke_points.append(position)
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

    def _create_toolbar(self) -> None:
        toolbar = QtWidgets.QToolBar("Tools")
        toolbar.setMovable(False)
        toolbar.setIconSize(QtCore.QSize(24, 24))
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.addToolBar(toolbar)
        self._toolbar = toolbar

        self._add_tool_action(toolbar, "Pen", Tool.PEN, "P")
        self._add_tool_action(toolbar, "Rectangle", Tool.RECTANGLE, "R")
        self._add_tool_action(toolbar, "Arrow", Tool.ARROW, "A")
        self._add_tool_action(toolbar, "Text", Tool.TEXT, "T")
        self._add_tool_action(toolbar, "Number", Tool.NUMBER, "N")
        self._add_tool_action(toolbar, "Blur", Tool.BLUR, "B")
        self._add_tool_action(toolbar, "Mosaic", Tool.MOSAIC, "M")

        toolbar.addSeparator()

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

        undo_action = QtGui.QAction("Undo", self)
        undo_action.setIcon(_build_single_state_icon(_draw_undo_icon))
        undo_action.setShortcut(QtGui.QKeySequence.StandardKey.Undo)
        undo_action.setToolTip("Undo")
        undo_action.triggered.connect(self.canvas.undo)
        toolbar.addAction(undo_action)

        copy_action = QtGui.QAction("Copy", self)
        copy_action.setIcon(_build_single_state_icon(_draw_copy_icon))
        copy_action.setShortcut(QtGui.QKeySequence.StandardKey.Copy)
        copy_action.setToolTip("Copy")
        copy_action.triggered.connect(self.copy_image)
        toolbar.addAction(copy_action)

        save_action = QtGui.QAction("Save", self)
        save_action.setIcon(_build_single_state_icon(_draw_save_icon))
        save_action.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        save_action.setToolTip("Save")
        save_action.triggered.connect(self.save_image)
        toolbar.addAction(save_action)

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
