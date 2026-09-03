from pathlib import Path

import pytest

from app.services.upload_validation import (
    UploadValidationError,
    validate_declared_mime,
    validate_file_signature,
)


@pytest.mark.parametrize(
    ("suffix", "content_type"),
    [
        (".pdf", "application/pdf"),
        (".pdf", "application/octet-stream"),
        (
            ".docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (".docx", "application/zip; charset=binary"),
        (".doc", "application/msword"),
        (".doc", ""),
    ],
)
def test_supported_declared_mime_types(suffix, content_type):
    validate_declared_mime(suffix, content_type)


@pytest.mark.parametrize(
    ("suffix", "content"),
    [
        (".pdf", b"%PDF-1.7\n"),
        (".docx", b"PK\x03\x04zip-content"),
        (".doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1ole-content"),
    ],
)
def test_supported_file_signatures(tmp_path, suffix, content):
    path = Path(tmp_path) / f"fixture{suffix}"
    path.write_bytes(content)

    validate_file_signature(path, suffix)


def test_known_wrong_mime_is_rejected():
    with pytest.raises(UploadValidationError) as exc_info:
        validate_declared_mime(".docx", "application/pdf")

    assert exc_info.value.code == "FILE_TYPE_MISMATCH"
