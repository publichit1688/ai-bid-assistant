import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import make_url


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_database_url, get_report_dir, get_upload_dir


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_sqlite_path(database_url):
    url = make_url(database_url)
    if url.drivername != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("当前备份脚本仅支持持久化 SQLite 数据库。")
    return Path(url.database).resolve()


def copy_data_tree(source, destination):
    source = Path(source).resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"备份源目录不存在: {source.name}")
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"备份源包含符号链接，已拒绝: {path.name}")
    shutil.copytree(source, destination)


def manifest_files(snapshot_root):
    files = []
    for path in sorted(snapshot_root.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files.append(
                {
                    "path": path.relative_to(snapshot_root).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return files


def create_backup(destination, database_url, upload_dir, report_dir):
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("备份目标已存在，拒绝覆盖。")

    database_path = resolve_sqlite_path(database_url)
    if not database_path.is_file():
        raise FileNotFoundError("SQLite 数据库文件不存在。")

    destination.mkdir(parents=True)
    try:
        database_copy = destination / "database" / "bid.db"
        database_copy.parent.mkdir()
        with sqlite3.connect(database_path) as source_connection:
            with sqlite3.connect(database_copy) as target_connection:
                source_connection.backup(target_connection)

        copy_data_tree(upload_dir, destination / "uploads")
        copy_data_tree(report_dir, destination / "reports")

        manifest = {
            "format": "ai-bid-assistant-backup-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": manifest_files(destination),
        }
        (destination / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Create a non-overwriting SQLite and file-storage backup."
    )
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    manifest = create_backup(
        args.destination,
        get_database_url(),
        get_upload_dir(),
        get_report_dir(),
    )
    print(f"备份完成，已校验 {len(manifest['files'])} 个文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
