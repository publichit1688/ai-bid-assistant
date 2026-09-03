from pathlib import Path


VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"
APP_VERSION = VERSION_FILE.read_text(encoding="utf-8").strip()

if not APP_VERSION:
    raise RuntimeError("VERSION文件不能为空。")
