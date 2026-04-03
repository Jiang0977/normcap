from PySide6 import QtCore, QtGui

from normcap.annotate_prototype.models import (
    ArrowAnnotation,
    EffectAnnotation,
    NumberAnnotation,
    RectangleAnnotation,
    Tool,
)
from normcap.annotate_prototype.render import build_arrow_head, compose_image


def test_build_arrow_head_uses_end_point_as_tip() -> None:
    start = QtCore.QPointF(10, 10)
    end = QtCore.QPointF(30, 10)

    polygon = build_arrow_head(start=start, end=end, size=12)

    assert polygon.count() == 3
    assert polygon[0] == end


def test_compose_image_keeps_size_and_draws_on_copy() -> None:
    image = QtGui.QImage(40, 30, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    result = compose_image(
        base_image=image,
        annotations=[
            RectangleAnnotation(
                rect=QtCore.QRectF(5, 5, 20, 10),
                color=QtGui.QColor("red"),
                width=2,
            ),
            ArrowAnnotation(
                start=QtCore.QPointF(2, 2),
                end=QtCore.QPointF(30, 20),
                color=QtGui.QColor("blue"),
                width=3,
            ),
        ],
    )

    assert result.size() == image.size()
    assert result.pixelColor(5, 5) != QtGui.QColor("white")


def _make_pattern_image() -> QtGui.QImage:
    image = QtGui.QImage(24, 24, QtGui.QImage.Format.Format_ARGB32)
    for y in range(24):
        for x in range(24):
            color = QtGui.QColor("black") if (x + y) % 2 == 0 else QtGui.QColor("white")
            image.setPixelColor(x, y, color)
    return image


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


def test_compose_image_applies_mosaic_effect() -> None:
    image = _make_pattern_image()

    result = compose_image(
        base_image=image,
        annotations=[
            EffectAnnotation(
                rect=QtCore.QRectF(4, 4, 12, 12),
                effect=Tool.MOSAIC,
                strength=4,
                color=QtGui.QColor("red"),
                width=2,
            )
        ],
    )

    assert _changed_pixels(image, result, 4, 4, 15, 15) > 0


def test_compose_image_applies_blur_effect() -> None:
    image = _make_pattern_image()

    result = compose_image(
        base_image=image,
        annotations=[
            EffectAnnotation(
                rect=QtCore.QRectF(4, 4, 12, 12),
                effect=Tool.BLUR,
                strength=4,
                color=QtGui.QColor("red"),
                width=2,
            )
        ],
    )

    assert _changed_pixels(image, result, 4, 4, 15, 15) > 0


def test_compose_image_draws_number_annotation(qapp) -> None:
    image = QtGui.QImage(40, 40, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    result = compose_image(
        base_image=image,
        annotations=[
            NumberAnnotation(
                position=QtCore.QPointF(20, 20),
                number=3,
                color=QtGui.QColor("red"),
                radius=12,
                width=2,
            )
        ],
    )

    assert result.pixelColor(20, 20) != QtGui.QColor("white")
