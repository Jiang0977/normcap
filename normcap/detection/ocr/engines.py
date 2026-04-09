"""Helpers for OCR engine specific behavior."""

TESSERACT = "tesseract"
BAIDU = "baidu"


def normalize(engine: str | None) -> str:
    if engine == BAIDU:
        return BAIDU
    return TESSERACT


def is_baidu(engine: str | None) -> bool:
    return normalize(engine) == BAIDU


def uses_tesseract_languages(engine: str | None) -> bool:
    return normalize(engine) == TESSERACT


def requires_baidu_credentials(engine: str | None) -> bool:
    return normalize(engine) == BAIDU
