"""Rendering helpers for the screenshot annotation prototype."""

from __future__ import annotations

import math

from PySide6 import QtCore, QtGui

from normcap.annotate_prototype.models import (
    Annotation,
    ArrowAnnotation,
    RectangleAnnotation,
    StrokeAnnotation,
    TextAnnotation,
)


def build_arrow_head(
    start: QtCore.QPointF, end: QtCore.QPointF, size: float
) -> QtGui.QPolygonF:
    """Create a triangular arrow head polygon pointing to ``end``."""
    delta_x = end.x() - start.x()
    delta_y = end.y() - start.y()
    length = math.hypot(delta_x, delta_y)

    if length == 0:
        return QtGui.QPolygonF([end, end, end])

    unit_x = delta_x / length
    unit_y = delta_y / length
    perpendicular_x = -unit_y
    perpendicular_y = unit_x

    base_x = end.x() - unit_x * size
    base_y = end.y() - unit_y * size

    left = QtCore.QPointF(
        base_x + perpendicular_x * size * 0.5,
        base_y + perpendicular_y * size * 0.5,
    )
    right = QtCore.QPointF(
        base_x - perpendicular_x * size * 0.5,
        base_y - perpendicular_y * size * 0.5,
    )
    return QtGui.QPolygonF([end, left, right])


def draw_annotation(painter: QtGui.QPainter, annotation: Annotation) -> None:
    """Draw a single annotation onto the painter."""
    if isinstance(annotation, StrokeAnnotation):
        pen = QtGui.QPen(
            annotation.color,
            annotation.width,
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.RoundCap,
            QtCore.Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        if len(annotation.points) == 1:
            painter.drawPoint(annotation.points[0])
            return

        path = QtGui.QPainterPath(annotation.points[0])
        for point in annotation.points[1:]:
            path.lineTo(point)
        painter.drawPath(path)
        return

    if isinstance(annotation, RectangleAnnotation):
        pen = QtGui.QPen(annotation.color, annotation.width)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawRect(annotation.rect.normalized())
        return

    if isinstance(annotation, ArrowAnnotation):
        pen = QtGui.QPen(
            annotation.color,
            annotation.width,
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.RoundCap,
            QtCore.Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        painter.drawLine(annotation.start, annotation.end)

        arrow_size = max(annotation.width * 4, 12)
        arrow_head = build_arrow_head(
            start=annotation.start,
            end=annotation.end,
            size=arrow_size,
        )
        painter.setBrush(annotation.color)
        painter.drawPolygon(arrow_head)
        return

    if isinstance(annotation, TextAnnotation):
        painter.setPen(annotation.color)
        font = painter.font()
        font.setPointSize(annotation.font_size)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(annotation.position, annotation.text)
        return

    raise TypeError(f"Unsupported annotation type: {type(annotation)!r}")


def compose_image(
    base_image: QtGui.QImage, annotations: list[Annotation]
) -> QtGui.QImage:
    """Render all annotations onto a copy of the base image."""
    image = base_image.copy()
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    for annotation in annotations:
        draw_annotation(painter, annotation)
    painter.end()
    return image
