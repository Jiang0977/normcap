"""Data models used by the screenshot annotation prototype."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from PySide6 import QtCore, QtGui


class Tool(str, Enum):
    """Annotation tools available in the prototype."""

    PEN = "pen"
    RECTANGLE = "rectangle"
    ARROW = "arrow"
    TEXT = "text"


@dataclass(slots=True)
class StrokeAnnotation:
    points: list[QtCore.QPointF]
    color: QtGui.QColor
    width: int


@dataclass(slots=True)
class RectangleAnnotation:
    rect: QtCore.QRectF
    color: QtGui.QColor
    width: int


@dataclass(slots=True)
class ArrowAnnotation:
    start: QtCore.QPointF
    end: QtCore.QPointF
    color: QtGui.QColor
    width: int


@dataclass(slots=True)
class TextAnnotation:
    position: QtCore.QPointF
    text: str
    color: QtGui.QColor
    font_size: int


Annotation = StrokeAnnotation | RectangleAnnotation | ArrowAnnotation | TextAnnotation
