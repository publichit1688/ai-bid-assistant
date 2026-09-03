import json
import sqlite3

import pytest


def test_backup_creates_consistent_snapshot_and_manifest(tmp_path):
    from scripts.backup_runtime import create_backup, sha256_file

    database = tmp_path / "source" / "bid.db"
    uploads = tmp_path / "source" / "uploads"
    reports = tmp_path / "source" / "reports"
    database.parent.mkdir()
    uploads.mkdir()
    reports.mkdir()
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('isolated')")
    (uploads / "sample.pdf").write_bytes(b"synthetic-pdf")
    (reports / "sample.docx").write_bytes(b"synthetic-report")

    destination = tmp_path / "snapshot"
    manifest = create_backup(
        destination,
        f"sqlite:///{database.as_posix()}",
        uploads,
        reports,
    )

    with sqlite3.connect(destination / "database" / "bid.db") as connection:
        assert connection.execute("SELECT value FROM sample").fetchone() == (
            "isolated",
        )
    saved_manifest = json.loads(
        (destination / "manifest.json").read_text(encoding="utf-8")
    )
    assert saved_manifest == manifest
    assert manifest["format"] == "ai-bid-assistant-backup-v1"
    assert {item["path"] for item in manifest["files"]} == {
        "database/bid.db",
        "uploads/sample.pdf",
        "reports/sample.docx",
    }
    for item in manifest["files"]:
        assert item["sha256"] == sha256_file(destination / item["path"])


def test_backup_refuses_overwrite_and_symlinks(tmp_path):
    from scripts.backup_runtime import create_backup

    database = tmp_path / "bid.db"
    uploads = tmp_path / "uploads"
    reports = tmp_path / "reports"
    uploads.mkdir()
    reports.mkdir()
    sqlite3.connect(database).close()

    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError, match="拒绝覆盖"):
        create_backup(
            existing,
            f"sqlite:///{database.as_posix()}",
            uploads,
            reports,
        )

    target = tmp_path / "outside.txt"
    target.write_text("outside", encoding="utf-8")
    link = uploads / "linked.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("当前Windows环境不允许创建测试符号链接")

    destination = tmp_path / "rejected"
    with pytest.raises(ValueError, match="符号链接"):
        create_backup(
            destination,
            f"sqlite:///{database.as_posix()}",
            uploads,
            reports,
        )
    assert not destination.exists()
