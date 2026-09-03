import base64
import os
import re
import time
from pathlib import Path

import fitz
import httpx
from dotenv import dotenv_values

PROJECT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"

BAIDU_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
BAIDU_GENERAL_LOCATION_URL = (
    "https://aip.baidubce.com/rest/2.0/ocr/v1/general"
)


class OCRConfigurationError(RuntimeError):
    """Raised when a scanned document needs OCR but OCR is not configured."""


class OCRServiceError(RuntimeError):
    """Raised when the configured OCR provider cannot complete recognition."""


def _config_value(name, default=""):
    """Use the canonical project-root OCR config, then process environment."""
    root_value = dotenv_values(PROJECT_ENV_PATH).get(name)
    if root_value is not None and str(root_value).strip():
        return str(root_value).strip()
    current_value = os.getenv(name)
    if current_value is not None and str(current_value).strip():
        return str(current_value).strip()
    return default


def _positive_int_env(name, default):
    raw_value = _config_value(name, str(default))
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = default
    return max(1, value)


def ocr_is_needed(text):
    minimum_chars = _positive_int_env("OCR_MIN_TEXT_CHARS", 20)
    compact_text = re.sub(r"\s+", "", text or "")
    return len(compact_text) < minimum_chars


def get_ocr_max_pages():
    return _positive_int_env("OCR_MAX_PAGES", 50)


class BaiduOCRClient:
    def __init__(self, api_key, secret_key, http_client=None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.http_client = http_client or httpx.Client(
            timeout=float(_config_value("BAIDU_OCR_TIMEOUT_SECONDS", "30"))
        )
        self.endpoint = _config_value(
            "BAIDU_OCR_ENDPOINT",
            BAIDU_GENERAL_LOCATION_URL,
        )
        self._access_token = None
        self._token_expires_at = 0.0

    def _response_json(self, response):
        try:
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OCRServiceError("百度 OCR 网络响应异常，请稍后重试") from exc
        if not isinstance(payload, dict):
            raise OCRServiceError("百度 OCR 返回格式异常，请稍后重试")
        return payload

    def _get_access_token(self):
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        try:
            response = self.http_client.post(
                BAIDU_TOKEN_URL,
                params={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.secret_key,
                },
            )
        except httpx.HTTPError as exc:
            raise OCRServiceError("百度 OCR 鉴权连接失败，请稍后重试") from exc
        payload = self._response_json(response)
        access_token = payload.get("access_token")
        if not access_token:
            raise OCRServiceError("百度 OCR 鉴权失败，请检查 API Key 和 Secret Key")
        try:
            expires_in = max(60, int(payload.get("expires_in", 2592000)))
        except (TypeError, ValueError):
            expires_in = 2592000
        self._access_token = str(access_token)
        self._token_expires_at = time.time() + expires_in - 30
        return self._access_token

    def recognize_image(self, image_bytes, retry_token=True):
        encoded_image = base64.b64encode(image_bytes).decode("ascii")
        if len(encoded_image) > 6 * 1024 * 1024:
            raise OCRServiceError("扫描页图片过大，无法安全提交百度 OCR")
        try:
            response = self.http_client.post(
                self.endpoint,
                params={"access_token": self._get_access_token()},
                data={
                    "image": encoded_image,
                    "language_type": "CHN_ENG",
                    "detect_direction": "true",
                    "paragraph": "true",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.HTTPError as exc:
            raise OCRServiceError("百度 OCR 识别连接失败，请稍后重试") from exc
        payload = self._response_json(response)
        error_code = payload.get("error_code")
        if error_code in {110, 111} and retry_token:
            self._access_token = None
            self._token_expires_at = 0.0
            return self.recognize_image(image_bytes, retry_token=False)
        if error_code is not None:
            raise OCRServiceError(f"百度 OCR 识别失败（错误码 {error_code}）")
        words_result = payload.get("words_result")
        if not isinstance(words_result, list):
            raise OCRServiceError("百度 OCR 返回格式异常，请稍后重试")
        lines = []
        for item in words_result:
            if not isinstance(item, dict):
                continue
            text = str(item.get("words", "")).strip()
            location = item.get("location")
            if not text or not isinstance(location, dict):
                continue
            try:
                box = {
                    "left": float(location["left"]),
                    "top": float(location["top"]),
                    "width": float(location["width"]),
                    "height": float(location["height"]),
                }
            except (KeyError, TypeError, ValueError):
                continue
            lines.append({"text": text, "box": box})
        if words_result and not lines:
            raise OCRServiceError(
                "百度 OCR 未返回文字位置，请确认已开通并使用标准含位置版接口"
            )
        return {
            "text": "\n".join(line["text"] for line in lines),
            "lines": lines,
        }

    def recognize_pdf_page(self, page):
        max_side = max(float(page.rect.width), float(page.rect.height), 1.0)
        zoom = min(2.0, 4096.0 / max_side)
        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(zoom, zoom),
            alpha=False,
        )
        image_bytes = pixmap.tobytes("jpeg", jpg_quality=85)
        result = self.recognize_image(image_bytes)
        image_width = max(float(pixmap.width), 1.0)
        image_height = max(float(pixmap.height), 1.0)
        normalized_lines = []
        for line in result["lines"]:
            box = line["box"]
            left = min(max(box["left"] / image_width, 0.0), 1.0)
            top = min(max(box["top"] / image_height, 0.0), 1.0)
            width = min(max(box["width"] / image_width, 0.0), 1.0 - left)
            height = min(max(box["height"] / image_height, 0.0), 1.0 - top)
            normalized_lines.append(
                {
                    "text": line["text"],
                    "box": {
                        "x": left,
                        "y": top,
                        "width": width,
                        "height": height,
                    },
                }
            )
        return {"text": result["text"], "lines": normalized_lines}


def get_ocr_client():
    provider = _config_value("OCR_PROVIDER", "disabled").lower()
    if provider != "baidu":
        raise OCRConfigurationError(
            "检测到扫描页，但百度 OCR 尚未启用；请设置 OCR_PROVIDER=baidu"
        )
    api_key = _config_value("BAIDU_OCR_API_KEY")
    secret_key = _config_value("BAIDU_OCR_SECRET_KEY")
    if not api_key or not secret_key:
        raise OCRConfigurationError(
            "百度 OCR 凭据未配置，请设置 BAIDU_OCR_API_KEY 和 BAIDU_OCR_SECRET_KEY"
        )
    return BaiduOCRClient(api_key, secret_key)
