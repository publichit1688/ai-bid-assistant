from pathlib import Path


class UploadValidationError(ValueError):
    def __init__(self, code, message, status_code=415):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


GENERIC_MIME_TYPES = {"", "application/octet-stream"}
ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf", "application/x-pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    },
    ".doc": {"application/msword", "application/vnd.ms-word"},
}


def validate_declared_mime(suffix, content_type):
    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized_type in GENERIC_MIME_TYPES:
        return
    if normalized_type not in ALLOWED_MIME_TYPES.get(suffix, set()):
        raise UploadValidationError(
            "FILE_TYPE_MISMATCH",
            "文件扩展名与声明的内容类型不一致。",
        )


def validate_file_signature(path, suffix):
    header = Path(path).read_bytes()[:8]
    signatures = {
        ".pdf": (b"%PDF-",),
        ".docx": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
        ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    }
    if not any(header.startswith(signature) for signature in signatures[suffix]):
        raise UploadValidationError(
            "FILE_SIGNATURE_MISMATCH",
            "文件内容与扩展名不一致或文件格式无法识别。",
        )
