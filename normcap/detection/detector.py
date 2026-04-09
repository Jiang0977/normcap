import logging
import time
from pathlib import Path

from PySide6 import QtGui

from normcap.detection import codes, ocr
from normcap.detection.models import DetectionMode, DetectionResult
from normcap.detection.ocr import engines

logger = logging.getLogger(__name__)


def detect(
    image: QtGui.QImage,
    tesseract_bin_path: Path | None,
    tessdata_path: Path | None,
    language: str,
    detect_mode: DetectionMode,
    parse_text: bool,
    ocr_engine: str = engines.TESSERACT,
    baidu_api_key: str = "",
    baidu_secret_key: str = "",
    baidu_language_type: str = "CHN_ENG",
) -> list[DetectionResult]:
    ocr_result = None
    codes_result = None

    if DetectionMode.CODES in detect_mode:
        start_time = time.time()
        codes_result = codes.detector.detect_codes(image)
        logger.debug("Code detection took %s", f"{time.time() - start_time:.4f}s")

    if codes_result:
        logger.debug("Codes detected, skipping OCR.")
        return codes_result

    if DetectionMode.TEXT in detect_mode:
        start_time = time.time()
        if engines.is_baidu(ocr_engine):
            ocr_result = ocr.baidu.get_text_from_image(
                image=image,
                api_key=baidu_api_key,
                secret_key=baidu_secret_key,
                language_type=baidu_language_type,
                parse_text=parse_text,
            )
        else:
            if tesseract_bin_path is None:
                raise RuntimeError("Tesseract binary path is missing.")
            ocr_result = ocr.recognize.get_text_from_image(
                languages=language,
                image=image,
                tesseract_bin_path=tesseract_bin_path,
                tessdata_path=tessdata_path,
                parse=parse_text,
                resize_factor=2,
                padding_size=80,
            )
        logger.debug("OCR detection took %s s", f"{time.time() - start_time:.4f}.")

    if ocr_result:
        logger.debug("Text detected.")
        return ocr_result

    logger.debug("No codes or text found!")
    return []
