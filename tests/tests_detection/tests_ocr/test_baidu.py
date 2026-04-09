import json

import pytest
from PySide6 import QtGui

from normcap.detection.ocr import baidu


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")
        self.status = 200

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _mock_urlopen(monkeypatch, responses: list[dict]):
    calls = []

    def _fake_urlopen(req, *_args, **_kwargs):
        calls.append(req)
        return _FakeResponse(responses.pop(0))

    monkeypatch.setattr(baidu.request, "urlopen", _fake_urlopen)
    return calls


def _token_payload(value: str) -> dict:
    return {"access_token": value, "expires_in": 3600}


def _secret_value() -> str:
    return "-".join(["secret", "key"])


def _ocr_payload(*lines: tuple[str, int, int]) -> dict:
    return {
        "words_result_num": len(lines),
        "words_result": [
            {
                "words": words,
                "location": {
                    "left": 10,
                    "top": top,
                    "width": width,
                    "height": 12,
                },
            }
            for words, top, width in lines
        ],
    }


def test_get_ocr_result_fetches_token_and_ocr(monkeypatch):
    baidu.clear_token_cache()
    test_secret = _secret_value()
    calls = _mock_urlopen(
        monkeypatch,
        [
            _token_payload("token-1"),
            _ocr_payload(("hello world", 10, 100), ("second line", 30, 120)),
        ],
    )

    result = baidu.get_ocr_result_from_image(
        image=QtGui.QImage(200, 50, QtGui.QImage.Format.Format_RGB32),
        api_key="api-key",
        secret_key=test_secret,
        language_type="ENG",
    )

    assert len(calls) == 2
    assert result.text == "hello world\nsecond line"
    assert result.tess_args.lang == "eng"
    assert {"text", "conf", "block_num", "par_num", "line_num"} <= (
        result.words[0].keys()
    )


def test_get_ocr_result_reuses_cached_token(monkeypatch):
    baidu.clear_token_cache()
    test_secret = _secret_value()
    calls = _mock_urlopen(
        monkeypatch,
        [
            _token_payload("token-1"),
            _ocr_payload(("first run", 10, 100)),
            _ocr_payload(("second run", 10, 120)),
        ],
    )

    image = QtGui.QImage(200, 50, QtGui.QImage.Format.Format_RGB32)
    baidu.get_ocr_result_from_image(
        image=image,
        api_key="api-key",
        secret_key=test_secret,
        language_type="ENG",
    )
    baidu.get_ocr_result_from_image(
        image=image,
        api_key="api-key",
        secret_key=test_secret,
        language_type="ENG",
    )

    assert len(calls) == 3


def test_get_ocr_result_refreshes_token_once_on_auth_error(monkeypatch):
    baidu.clear_token_cache()
    test_secret = _secret_value()
    calls = _mock_urlopen(
        monkeypatch,
        [
            _token_payload("token-1"),
            {"error_code": 110, "error_msg": "Access token invalid or no longer valid"},
            _token_payload("token-2"),
            _ocr_payload(("refreshed text", 10, 100)),
        ],
    )

    result = baidu.get_ocr_result_from_image(
        image=QtGui.QImage(200, 50, QtGui.QImage.Format.Format_RGB32),
        api_key="api-key",
        secret_key=test_secret,
        language_type="ENG",
    )

    assert len(calls) == 4
    assert result.text == "refreshed text"


def test_get_ocr_result_falls_back_to_general_basic_on_permission_error(monkeypatch):
    baidu.clear_token_cache()
    calls = _mock_urlopen(
        monkeypatch,
        [
            _token_payload("token-1"),
            {"error_code": 6, "error_msg": "No permission to access data"},
            _ocr_payload(("fallback text", 10, 100)),
        ],
    )

    result = baidu.get_ocr_result_from_image(
        image=QtGui.QImage(200, 50, QtGui.QImage.Format.Format_RGB32),
        api_key="api-key",
        secret_key=_secret_value(),
        language_type="ENG",
    )

    assert len(calls) == 3
    assert "/general?" in calls[1].full_url
    assert "/general_basic?" in calls[2].full_url
    assert result.text == "fallback text"


def test_get_ocr_result_raises_on_ocr_error(monkeypatch):
    baidu.clear_token_cache()
    test_secret = _secret_value()
    _ = _mock_urlopen(
        monkeypatch,
        [
            _token_payload("token-1"),
            {"error_code": 17, "error_msg": "Open api daily request limit reached"},
        ],
    )

    with pytest.raises(baidu.BaiduOcrError, match="daily request limit"):
        baidu.get_ocr_result_from_image(
            image=QtGui.QImage(200, 50, QtGui.QImage.Format.Format_RGB32),
            api_key="api-key",
            secret_key=test_secret,
            language_type="ENG",
        )
