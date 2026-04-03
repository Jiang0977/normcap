"""Rendering helpers for the screenshot annotation prototype."""

from __future__ import annotations

import math

from PySide6 import QtCore, QtGui

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


def _draw_stroke_annotation(
    painter: QtGui.QPainter, annotation: StrokeAnnotation
) -> None:
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


def _draw_rectangle_annotation(
    painter: QtGui.QPainter, annotation: RectangleAnnotation
) -> None:
    pen = QtGui.QPen(annotation.color, annotation.width)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    painter.drawRect(annotation.rect.normalized())


def _draw_arrow_annotation(
    painter: QtGui.QPainter, annotation: ArrowAnnotation
) -> None:
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


def _draw_text_annotation(painter: QtGui.QPainter, annotation: TextAnnotation) -> None:
    painter.setPen(annotation.color)
    font = painter.font()
    font.setPointSize(annotation.font_size)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(annotation.position, annotation.text)


def _draw_number_annotation(
    painter: QtGui.QPainter, annotation: NumberAnnotation
) -> None:
    diameter = annotation.radius * 2
    rect = QtCore.QRectF(
        annotation.position.x() - annotation.radius,
        annotation.position.y() - annotation.radius,
        diameter,
        diameter,
    )
    painter.setPen(QtGui.QPen(annotation.color, annotation.width))
    painter.setBrush(QtGui.QBrush(annotation.color))
    painter.drawEllipse(rect)

    painter.setPen(QtGui.QColor("white"))
    font = painter.font()
    font.setPointSize(max(10, annotation.radius))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(
        rect,
        QtCore.Qt.AlignmentFlag.AlignCenter,
        str(annotation.number),
    )


def _draw_effect_outline(painter: QtGui.QPainter, annotation: EffectAnnotation) -> None:
    pen = QtGui.QPen(
        annotation.color,
        annotation.width,
        QtCore.Qt.PenStyle.DashLine,
    )
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    rect = annotation.rect.normalized()
    painter.drawRect(rect)

    font = painter.font()
    font.setPointSize(10)
    font.setBold(True)
    painter.setFont(font)

    label = "BLUR" if annotation.effect == Tool.BLUR else "MOSAIC"
    label_rect = QtCore.QRectF(rect.left(), rect.top() - 20, 90, 18)
    painter.fillRect(label_rect, QtGui.QColor(0, 0, 0, 160))
    painter.setPen(QtGui.QColor("white"))
    painter.drawText(label_rect, QtCore.Qt.AlignmentFlag.AlignCenter, label)


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
        _draw_stroke_annotation(painter, annotation)
        return

    if isinstance(annotation, RectangleAnnotation):
        _draw_rectangle_annotation(painter, annotation)
        return

    if isinstance(annotation, ArrowAnnotation):
        _draw_arrow_annotation(painter, annotation)
        return

    if isinstance(annotation, TextAnnotation):
        _draw_text_annotation(painter, annotation)
        return

    if isinstance(annotation, NumberAnnotation):
        _draw_number_annotation(painter, annotation)
        return

    if isinstance(annotation, EffectAnnotation):
        _draw_effect_outline(painter, annotation)
        return

    raise TypeError(f"Unsupported annotation type: {type(annotation)!r}")


def _normalized_image_rect(
    image: QtGui.QImage, rect: QtCore.QRectF
) -> QtCore.QRect | None:
    qrect = rect.normalized().toAlignedRect().intersected(image.rect())
    if qrect.width() <= 0 or qrect.height() <= 0:
        return None
    return qrect


def apply_effect_annotation(
    image: QtGui.QImage, annotation: EffectAnnotation
) -> QtGui.QImage:
    """Apply an effect annotation directly onto a copy of the given image."""
    result = image.copy()
    _draw_effect_annotation(result, annotation)
    return result


def _draw_effect_annotation(image: QtGui.QImage, annotation: EffectAnnotation) -> None:
    target_rect = _normalized_image_rect(image=image, rect=annotation.rect)
    if target_rect is None:
        return

    source = image.copy(target_rect)
    if source.isNull():
        return

    strength = max(2, annotation.strength)
    if annotation.effect == Tool.MOSAIC:
        sampled = source.scaled(
            max(1, target_rect.width() // strength),
            max(1, target_rect.height() // strength),
            QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
            QtCore.Qt.TransformationMode.FastTransformation,
        )
        processed = sampled.scaled(
            target_rect.size(),
            QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
            QtCore.Qt.TransformationMode.FastTransformation,
        )
    elif annotation.effect == Tool.BLUR:
        processed = source
        for _ in range(2):
            sampled = processed.scaled(
                max(1, target_rect.width() // strength),
                max(1, target_rect.height() // strength),
                QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
            processed = sampled.scaled(
                target_rect.size(),
                QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
    else:
        raise TypeError(f"Unsupported effect annotation: {annotation.effect!r}")

    painter = QtGui.QPainter(image)
    painter.drawImage(target_rect.topLeft(), processed)
    painter.end()


def compose_image(
    base_image: QtGui.QImage, annotations: list[Annotation]
) -> QtGui.QImage:
    """Render all annotations onto a copy of the base image."""
    image = base_image.copy()
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    for annotation in annotations:
        if isinstance(annotation, EffectAnnotation):
            painter.end()
            image = apply_effect_annotation(image=image, annotation=annotation)
            painter = QtGui.QPainter(image)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            continue
        draw_annotation(painter, annotation)
    painter.end()
    return image
