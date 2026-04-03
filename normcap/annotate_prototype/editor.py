"""Annotation editor window for the screenshot prototype."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from normcap.annotate_prototype.models import (
    Annotation,
    ArrowAnnotation,
    EffectAnnotation,
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
        self._create_toolbar()
        self.statusBar().showMessage("Select a tool and annotate the screenshot.")

    def _add_tool_action(
        self,
        toolbar: QtWidgets.QToolBar,
        text: str,
        tool: Tool,
        shortcut: str,
    ) -> None:
        action = QtGui.QAction(text, self)
        action.setCheckable(True)
        action.setShortcut(shortcut)
        action.triggered.connect(
            lambda checked, t=tool: checked and self.canvas.set_tool(t)
        )
        toolbar.addAction(action)
        self._tool_actions[tool] = action

    def _create_toolbar(self) -> None:
        toolbar = QtWidgets.QToolBar("Tools")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        action_group = QtGui.QActionGroup(self)
        action_group.setExclusive(True)

        self._add_tool_action(toolbar, "Pen", Tool.PEN, "P")
        self._add_tool_action(toolbar, "Rectangle", Tool.RECTANGLE, "R")
        self._add_tool_action(toolbar, "Arrow", Tool.ARROW, "A")
        self._add_tool_action(toolbar, "Text", Tool.TEXT, "T")
        self._add_tool_action(toolbar, "Blur", Tool.BLUR, "B")
        self._add_tool_action(toolbar, "Mosaic", Tool.MOSAIC, "M")

        for action in self._tool_actions.values():
            action_group.addAction(action)

        self._tool_actions[Tool.PEN].setChecked(True)

        toolbar.addSeparator()

        color_action = QtGui.QAction("Color", self)
        color_action.triggered.connect(self._pick_color)
        toolbar.addAction(color_action)

        undo_action = QtGui.QAction("Undo", self)
        undo_action.setShortcut(QtGui.QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.canvas.undo)
        toolbar.addAction(undo_action)

        copy_action = QtGui.QAction("Copy", self)
        copy_action.setShortcut(QtGui.QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self.copy_image)
        toolbar.addAction(copy_action)

        save_action = QtGui.QAction("Save", self)
        save_action.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_image)
        toolbar.addAction(save_action)

    def _pick_color(self) -> None:
        color = QtWidgets.QColorDialog.getColor(self.canvas.color, self, "Pick Color")
        if color.isValid():
            self.canvas.set_color(color)

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
