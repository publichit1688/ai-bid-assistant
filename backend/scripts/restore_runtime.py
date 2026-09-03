import argparse
import json
import shutil
import sqlite3
import sys
from pathlib import Path, PurePosixPath
from uuid import uuid4


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.backup_runtime import sha256_file


BACKUP_FORMAT = "ai-bid-assistant-backup-v1"
ALLOWED_ROOTS = {"database", "uploads", "reports"}


def safe_manifest_path(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("备份清单包含不安全路径。")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or "." in relative.parts:
        raise ValueError("备份清单包含不安全路径。")
    if relative.parts[0] not in ALLOWED_ROOTS:
        raise ValueError("备份清单包含未知目录。")
    if relative.parts[0] == "database" and relative.parts != ("database", "bid.db"):
        raise ValueError("数据库备份路径不符合约定。")
    if len(relative.parts) < 2:
        raise ValueError("备份清单包含无效文件路径。")
    return relative


def load_and_verify_backup(backup_root):
    backup_root = Path(backup_root).resolve()
    if not backup_root.is_dir() or backup_root.is_symlink():
        raise FileNotFoundError("备份目录不存在或不安全。")

    manifest_path = backup_root / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise FileNotFoundError("备份清单不存在或不安全。")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("备份清单无法读取。") from exc

    if manifest.get("format") != BACKUP_FORMAT or not isinstance(
        manifest.get("files"), list
    ):
        raise ValueError("备份格式不受支持。")

    verified = []
    seen = set()
    for item in manifest["files"]:
        if not isinstance(item, dict):
            raise ValueError("备份清单文件条目无效。")
        relative = safe_manifest_path(item.get("path"))
        normalized = relative.as_posix()
        if normalized in seen:
            raise ValueError("备份清单包含重复文件。")
        seen.add(normalized)

        source = backup_root.joinpath(*relative.parts)
        if not source.is_file() or source.is_symlink():
            raise FileNotFoundError("备份文件缺失或不安全。")
        expected_size = item.get("size")
        expected_hash = item.get("sha256")
        if (
            not isinstance(expected_size, int)
            or expected_size < 0
            or not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or source.stat().st_size != expected_size
            or sha256_file(source) != expected_hash.lower()
        ):
            raise ValueError("备份文件校验失败。")
        verified.append((relative, source, expected_size, expected_hash.lower()))

    if "database/bid.db" not in seen:
        raise ValueError("备份缺少SQLite数据库。")

    backup_entries = list(backup_root.rglob("*"))
    if any(path.is_symlink() for path in backup_entries):
        raise ValueError("备份目录包含不安全的符号链接。")
    actual = {
        path.relative_to(backup_root).as_posix()
        for path in backup_entries
        if path.is_file() and path != manifest_path
    }
    if actual != seen:
        raise ValueError("备份目录与清单文件集合不一致。")

    database_path = backup_root / "database" / "bid.db"
    try:
        with sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error as exc:
        raise ValueError("SQLite备份无法打开。") from exc
    if integrity != ("ok",):
        raise ValueError("SQLite备份完整性检查失败。")

    return verified


def restore_backup(backup_root, destination):
    backup_root = Path(backup_root).resolve()
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("恢复目标已存在，拒绝覆盖。")
    if destination == backup_root or backup_root in destination.parents:
        raise ValueError("恢复目标不能位于备份目录内。")

    verified = load_and_verify_backup(backup_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / f".{destination.name}.restore-{uuid4().hex}"
    try:
        staging.mkdir()
        for relative, source, expected_size, expected_hash in verified:
            target = staging.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if (
                target.stat().st_size != expected_size
                or sha256_file(target) != expected_hash
            ):
                raise ValueError("恢复文件复制校验失败。")
        staging.replace(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return len(verified)


def main():
    parser = argparse.ArgumentParser(
        description="Restore a verified snapshot into a new runtime directory."
    )
    parser.add_argument("backup", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    restored = restore_backup(args.backup, args.destination)
    print(f"恢复完成，已校验并复制 {restored} 个文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
