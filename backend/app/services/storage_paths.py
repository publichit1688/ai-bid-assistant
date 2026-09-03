from pathlib import Path

from app.config import get_upload_dir


class UnsafeStoragePathError(ValueError):
    """Raised when a stored path escapes the configured upload directory."""


def get_upload_root():
    return get_upload_dir().resolve()


def resolve_upload_file(filepath, require_file=False):
    if not filepath:
        raise UnsafeStoragePathError("文件路径为空")

    upload_root = get_upload_root()
    resolved = Path(filepath).resolve()
    if resolved == upload_root or upload_root not in resolved.parents:
        raise UnsafeStoragePathError("文件路径超出上传目录")
    if require_file and not resolved.is_file():
        raise FileNotFoundError("文件不存在")
    return resolved


def public_upload_path(filepath):
    try:
        resolved = resolve_upload_file(filepath)
    except UnsafeStoragePathError:
        return None
    relative_path = resolved.relative_to(get_upload_root())
    return "/uploads/" + relative_path.as_posix()
