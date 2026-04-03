"""Data models used by the screenshot annotation prototype."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from PySide6 import QtCore, QtGui


class Tool(str, Enum):
    """Annotation tools available in the prototype."""

    SELECT = "select"
    PEN = "pen"
    RECTANGLE = "rectangle"
    ARROW = "arrow"
    TEXT = "text"
    NUMBER = "number"
    BLUR = "blur"
    MOSAIC = "mosaic"


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


@dataclass(slots=True)
class NumberAnnotation:
    position: QtCore.QPointF
    number: int
    color: QtGui.QColor
    radius: int
    width: int


@dataclass(slots=True)
class EffectAnnotation:
    rect: QtCore.QRectF
    effect: Tool
    strength: int
    color: QtGui.QColor
    width: int


Annotation = (
    StrokeAnnotation
    | RectangleAnnotation
    | ArrowAnnotation
    | TextAnnotation
    | NumberAnnotation
    | EffectAnnotation
)
