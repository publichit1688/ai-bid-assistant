import httpx
import pytest


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://example.invalid")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("failed", request=request, response=response)

    def json(self):
        return self.payload


class FakeHTTPClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def test_baidu_ocr_gets_token_and_returns_text_without_leaking_credentials():
    from app.services.ocr import BAIDU_TOKEN_URL, BaiduOCRClient

    fake_http = FakeHTTPClient(
        [
            FakeResponse({"access_token": "temporary-token", "expires_in": 3600}),
            FakeResponse(
                {
                    "words_result_num": 2,
                    "words_result": [
                        {
                            "words": "招标公告",
                            "location": {"left": 10, "top": 20, "width": 80, "height": 20},
                        },
                        {
                            "words": "资格审查要求",
                            "location": {"left": 10, "top": 50, "width": 120, "height": 20},
                        },
                    ],
                }
            ),
        ]
    )
    client = BaiduOCRClient("test-api-key", "test-secret", http_client=fake_http)

    result = client.recognize_image(b"fake-jpeg")
    assert result["text"] == "招标公告\n资格审查要求"
    assert result["lines"][1]["box"]["left"] == 10
    assert fake_http.calls[0][0] == BAIDU_TOKEN_URL
    assert fake_http.calls[1][1]["params"]["access_token"] == "temporary-token"
    assert "test-secret" not in str(fake_http.calls[1])


def test_ocr_requires_explicit_baidu_configuration(monkeypatch):
    from app.services import ocr

    monkeypatch.setattr(ocr, "dotenv_values", lambda _path: {})
    monkeypatch.setenv("OCR_PROVIDER", "disabled")
    monkeypatch.setenv("BAIDU_OCR_API_KEY", "should-not-be-used")
    monkeypatch.setenv("BAIDU_OCR_SECRET_KEY", "should-not-be-used")

    with pytest.raises(ocr.OCRConfigurationError, match="尚未启用"):
        ocr.get_ocr_client()


def test_ocr_falls_back_to_project_root_env_when_backend_values_are_empty(
    monkeypatch,
):
    from app.services import ocr

    monkeypatch.setenv("OCR_PROVIDER", "")
    monkeypatch.setenv("BAIDU_OCR_API_KEY", "")
    monkeypatch.setenv("BAIDU_OCR_SECRET_KEY", "")
    monkeypatch.setattr(
        ocr,
        "dotenv_values",
        lambda _path: {
            "OCR_PROVIDER": "baidu",
            "BAIDU_OCR_API_KEY": "root-api-key",
            "BAIDU_OCR_SECRET_KEY": "root-secret-key",
        },
    )

    client = ocr.get_ocr_client()

    assert client.api_key == "root-api-key"
    assert client.secret_key == "root-secret-key"


def test_pdf_uses_ocr_only_for_pages_without_text(monkeypatch):
    from app.services import parser

    class FakeRect:
        width = 595
        height = 842

    class FakePage:
        rect = FakeRect()

        def __init__(self, text, has_image=False):
            self.text = text
            self.has_image = has_image

        def get_text(self):
            return self.text

        def get_images(self, full=False):
            return [(1,)] if self.has_image else []

    class FakeDocument:
        def __init__(self):
            self.pages = [
                FakePage("这是一个包含足够文字内容的电子 PDF 页面，不应调用 OCR。"),
                FakePage("", has_image=True),
            ]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def __iter__(self):
            return iter(self.pages)

        def __getitem__(self, index):
            return self.pages[index]

    class FakeOCRClient:
        def __init__(self):
            self.pages = []

        def recognize_pdf_page(self, page):
            self.pages.append(page)
            return {
                "text": "扫描页识别出的资格审查要求",
                "lines": [
                    {
                        "text": "扫描页识别出的资格审查要求",
                        "box": {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.04},
                    }
                ],
            }

    fake_ocr = FakeOCRClient()
    monkeypatch.setattr(parser, "open_pdf_document", lambda _path: FakeDocument())
    monkeypatch.setattr(parser, "get_ocr_client", lambda: fake_ocr)

    pages = parser.read_pdf("fixture.pdf")

    assert pages[0].get("text_source", "native") == "native"
    assert pages[1]["text"] == "扫描页识别出的资格审查要求"
    assert pages[1]["text_source"] == "baidu_ocr"
    assert pages[1]["ocr_lines"][0]["box"]["x"] == 0.1
    assert len(fake_ocr.pages) == 1


def test_pdf_rejects_ocr_page_count_before_cloud_calls(monkeypatch):
    from app.services import parser

    class FakeDocument:
        pages = [
            type(
                "Page",
                (),
                {
                    "get_text": lambda self: "",
                    "get_images": lambda self, full=False: [(1,)],
                },
            )()
            for _ in range(3)
        ]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def __iter__(self):
            return iter(self.pages)

    monkeypatch.setattr(parser, "open_pdf_document", lambda _path: FakeDocument())
    monkeypatch.setattr(parser, "get_ocr_max_pages", lambda: 2)
    monkeypatch.setattr(
        parser,
        "get_ocr_client",
        lambda: (_ for _ in ()).throw(AssertionError("cloud must not be called")),
    )

    with pytest.raises(parser.DocumentParseError, match="超过单次 OCR 上限"):
        parser.read_pdf("fixture.pdf")


def test_blank_pdf_page_does_not_call_ocr(monkeypatch):
    from app.services import parser

    class FakePage:
        def get_text(self):
            return ""

        def get_images(self, full=False):
            return []

    class FakeDocument:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def __iter__(self):
            return iter([FakePage()])

    monkeypatch.setattr(parser, "open_pdf_document", lambda _path: FakeDocument())
    monkeypatch.setattr(
        parser,
        "get_ocr_client",
        lambda: (_ for _ in ()).throw(AssertionError("blank page must not use OCR")),
    )

    with pytest.raises(parser.DocumentParseError, match="未提取到可分析的文字"):
        parser.read_pdf("blank.pdf")
