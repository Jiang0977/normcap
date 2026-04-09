"""Baidu OCR integration."""

from __future__ import annotations

import json
import logging
import ssl
import time
from dataclasses import dataclass
from urllib import parse, request

from PySide6 import QtCore, QtGui

from normcap.detection.models import DetectionResult
from normcap.detection.ocr import enhance, recognize
from normcap.detection.ocr.models import OEM, PSM, OcrResult, TessArgs

logger = logging.getLogger(__name__)

TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"  # noqa: S105
OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general"
OCR_BASIC_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
AUTH_ERROR_CODES = {110, 111}
FALLBACK_TO_BASIC_ERROR_CODES = {6}


class BaiduOcrError(RuntimeError):
    """Raised when Baidu OCR cannot complete a request."""


@dataclass
class _TokenCacheEntry:
    access_token: str
    expires_at: float


_token_cache: dict[tuple[str, str], _TokenCacheEntry] = {}


def clear_token_cache() -> None:
    _token_cache.clear()


def get_text_from_image(
    image: QtGui.QImage,
    api_key: str,
    secret_key: str,
    language_type: str = "CHN_ENG",
    parse_text: bool = True,
    timeout: float = 8.0,
) -> list[DetectionResult]:
    ocr_result = get_ocr_result_from_image(
        image=image,
        api_key=api_key,
        secret_key=secret_key,
        language_type=language_type,
        timeout=timeout,
    )
    return recognize.to_detection_results(ocr_result=ocr_result, parse=parse_text)


def get_ocr_result_from_image(
    image: QtGui.QImage,
    api_key: str,
    secret_key: str,
    language_type: str = "CHN_ENG",
    timeout: float = 8.0,
) -> OcrResult:
    if not api_key or not secret_key:
        raise BaiduOcrError("Baidu OCR credentials are missing.")

    image = enhance.preprocess(image, resize_factor=None, padding=None)
    encoded_image = _image_to_base64(image)

    response = _perform_ocr_request(
        api_key=api_key,
        secret_key=secret_key,
        image_base64=encoded_image,
        language_type=language_type,
        timeout=timeout,
    )
    words = _normalize_words(response.get("words_result", []))
    return OcrResult(
        tess_args=TessArgs(
            tessdata_path=None,
            lang=_language_type_to_tess_lang(language_type),
            oem=OEM.DEFAULT,
            psm=PSM.AUTO,
        ),
        words=words,
        image=image,
    )


def _perform_ocr_request(
    api_key: str,
    secret_key: str,
    image_base64: str,
    language_type: str,
    timeout: float,
) -> dict:
    access_token = _get_access_token(
        api_key=api_key, secret_key=secret_key, timeout=timeout
    )
    response = _request_ocr_with_refresh(
        access_token=access_token,
        image_base64=image_base64,
        language_type=language_type,
        timeout=timeout,
        endpoint_url=OCR_URL,
        api_key=api_key,
        secret_key=secret_key,
    )

    if int(response.get("error_code", 0)) in FALLBACK_TO_BASIC_ERROR_CODES:
        logger.info(
            "Baidu OCR general endpoint unavailable, falling back to general_basic."
        )
        response = _request_ocr_with_refresh(
            access_token=access_token,
            image_base64=image_base64,
            language_type=language_type,
            timeout=timeout,
            endpoint_url=OCR_BASIC_URL,
            api_key=api_key,
            secret_key=secret_key,
        )

    _raise_on_baidu_error(response)
    return response


def _get_access_token(
    api_key: str,
    secret_key: str,
    timeout: float,
    force_refresh: bool = False,
) -> str:
    cache_key = (api_key, secret_key)
    if (
        not force_refresh
        and (entry := _token_cache.get(cache_key))
        and entry.expires_at > time.time()
    ):
        return entry.access_token

    payload = parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": secret_key,
        }
    ).encode("utf-8")
    response = _request_json(
        url=TOKEN_URL,
        data=payload,
        timeout=timeout,
    )
    _raise_on_baidu_error(response)

    access_token = response.get("access_token")
    if not access_token:
        raise BaiduOcrError("Baidu OCR token response does not contain access_token.")

    expires_in = int(response.get("expires_in", 0) or 0)
    _token_cache[cache_key] = _TokenCacheEntry(
        access_token=access_token,
        expires_at=time.time() + max(expires_in - 60, 0),
    )
    return access_token


def _request_ocr(
    access_token: str,
    image_base64: str,
    language_type: str,
    timeout: float,
    endpoint_url: str,
) -> dict:
    payload = parse.urlencode(
        {
            "image": image_base64,
            "language_type": language_type,
        }
    ).encode("utf-8")
    return _request_json(
        url=f"{endpoint_url}?access_token={access_token}",
        data=payload,
        timeout=timeout,
    )


def _request_ocr_with_refresh(
    access_token: str,
    image_base64: str,
    language_type: str,
    timeout: float,
    endpoint_url: str,
    api_key: str,
    secret_key: str,
) -> dict:
    response = _request_ocr(
        access_token=access_token,
        image_base64=image_base64,
        language_type=language_type,
        timeout=timeout,
        endpoint_url=endpoint_url,
    )
    if int(response.get("error_code", 0)) not in AUTH_ERROR_CODES:
        return response

    logger.info("Baidu OCR token expired or invalid, refreshing once.")
    clear_token_cache()
    refreshed_token = _get_access_token(
        api_key=api_key,
        secret_key=secret_key,
        timeout=timeout,
        force_refresh=True,
    )
    return _request_ocr(
        access_token=refreshed_token,
        image_base64=image_base64,
        language_type=language_type,
        timeout=timeout,
        endpoint_url=endpoint_url,
    )


def _request_json(url: str, data: bytes, timeout: float) -> dict:
    context = ssl.create_default_context()
    req = request.Request(url, data=data)  # noqa: S310
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with request.urlopen(req, context=context, timeout=timeout) as response:  # noqa: S310
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def _image_to_base64(image: QtGui.QImage) -> str:
    byte_array = QtCore.QByteArray()
    buffer = QtCore.QBuffer(byte_array)
    buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(byte_array.toBase64()).decode("ascii")


def _language_type_to_tess_lang(language_type: str) -> str:
    return {
        "CHN_ENG": "chi_sim+eng",
        "ENG": "eng",
        "JAP": "jpn",
        "KOR": "kor",
        "FRE": "fra",
        "SPA": "spa",
        "POR": "por",
        "GER": "deu",
        "ITA": "ita",
        "RUS": "rus",
    }.get(language_type.upper(), "eng")


def _normalize_words(words_result: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    sorted_lines = sorted(
        words_result,
        key=lambda item: (
            item.get("location", {}).get("top", 0),
            item.get("location", {}).get("left", 0),
        ),
    )

    block_num = 1
    par_num = 1
    previous_top: int | None = None
    previous_height = 0

    for line_index, item in enumerate(sorted_lines, start=1):
        line_text = str(item.get("words", "")).strip()
        if not line_text:
            continue

        location = item.get("location", {})
        top = int(location.get("top", 0))
        left = int(location.get("left", 0))
        width = int(location.get("width", 0))
        height = int(location.get("height", 0))
        if previous_top is not None and top - previous_top > max(
            previous_height * 2, 24
        ):
            par_num += 1

        probability = item.get("probability", {})
        confidence = probability.get("average")
        if confidence is None:
            confidence = 0
        confidence_value = (
            float(confidence) * 100 if float(confidence) <= 1 else confidence
        )

        tokens = line_text.split() or [line_text]
        normalized.extend(
            [
                {
                    "text": token,
                    "conf": confidence_value,
                    "block_num": block_num,
                    "par_num": par_num,
                    "line_num": line_index,
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height,
                }
                for token in tokens
            ]
        )

        previous_top = top
        previous_height = height

    return normalized


def _raise_on_baidu_error(response: dict) -> None:
    if error_code := int(response.get("error_code", 0) or 0):
        raise BaiduOcrError(str(response.get("error_msg", error_code)))
