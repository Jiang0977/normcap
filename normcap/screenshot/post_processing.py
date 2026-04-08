import logging

from PySide6 import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)


def _get_screen_region(
    screen: QtGui.QScreen,
    full_image: QtGui.QImage,
    fallback_ratio: float,
) -> QtCore.QRect:
    geo = screen.geometry()

    device_pixel_ratio = getattr(screen, "devicePixelRatio", lambda: 1.0)()
    width = int(geo.width() * device_pixel_ratio)
    height = int(geo.height() * device_pixel_ratio)
    region = QtCore.QRect(geo.x(), geo.y(), width, height)

    if full_image.rect().contains(region):
        return region

    logger.debug(
        "Fallback to ratio-based split for screen geometry %s and dpr %s",
        geo,
        device_pixel_ratio,
    )
    return QtCore.QRect(
        int(geo.x() * fallback_ratio),
        int(geo.y() * fallback_ratio),
        int(geo.width() * fallback_ratio),
        int(geo.height() * fallback_ratio),
    )


def split_full_desktop_to_screens(full_image: QtGui.QImage) -> list[QtGui.QImage]:
    """Split full desktop image into list of images per screen.

    Also resizes screens according to image:virtual-geometry ratio.
    """
    virtual_geometry = QtWidgets.QApplication.primaryScreen().virtualGeometry()

    ratio = full_image.rect().width() / virtual_geometry.width()

    logger.debug("Virtual geometry width: %s", virtual_geometry.width())
    logger.debug("Image width: %s", full_image.rect().width())
    logger.debug("Resize ratio: %s", ratio)

    images = []
    for screen in QtWidgets.QApplication.screens():
        region = _get_screen_region(
            screen=screen,
            full_image=full_image,
            fallback_ratio=ratio,
        )
        image = full_image.copy(region)
        images.append(image)

    return images
