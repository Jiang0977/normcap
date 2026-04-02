from PySide6 import QtCore, QtGui

from normcap.annotate_prototype.models import ArrowAnnotation, RectangleAnnotation
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
