import json
import sqlite3

import pytest


def build_snapshot(tmp_path):
    from scripts.backup_runtime import create_backup

    source = tmp_path / "source"
    database = source / "bid.db"
    uploads = source / "uploads"
    reports = source / "reports"
    source.mkdir(parents=True)
    uploads.mkdir()
    reports.mkdir()
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('restored')")
    (uploads / "sample.pdf").write_bytes(b"synthetic-pdf")
    (reports / "sample.docx").write_bytes(b"synthetic-report")
    backup = tmp_path / "backup"
    create_backup(
        backup,
        f"sqlite:///{database.as_posix()}",
        uploads,
        reports,
    )
    return backup


def test_restore_verified_snapshot_into_new_directory(tmp_path):
    from scripts.restore_runtime import restore_backup

    backup = build_snapshot(tmp_path)
    destination = tmp_path / "restored"

    assert restore_backup(backup, destination) == 3
    with sqlite3.connect(destination / "database" / "bid.db") as connection:
        assert connection.execute("SELECT value FROM sample").fetchone() == (
            "restored",
        )
    assert (destination / "uploads" / "sample.pdf").read_bytes() == b"synthetic-pdf"
    assert (destination / "reports" / "sample.docx").read_bytes() == (
        b"synthetic-report"
    )


def test_restore_refuses_existing_destination(tmp_path):
    from scripts.restore_runtime import restore_backup

    backup = build_snapshot(tmp_path)
    destination = tmp_path / "existing"
    destination.mkdir()

    with pytest.raises(FileExistsError, match="拒绝覆盖"):
        restore_backup(backup, destination)


def test_restore_rejects_tampering_without_partial_destination(tmp_path):
    from scripts.restore_runtime import restore_backup

    backup = build_snapshot(tmp_path)
    (backup / "uploads" / "sample.pdf").write_bytes(b"tampered")
    destination = tmp_path / "rejected"

    with pytest.raises(ValueError, match="校验失败"):
        restore_backup(backup, destination)
    assert not destination.exists()
    assert list(tmp_path.glob(".rejected.restore-*")) == []


def test_restore_rejects_copy_time_change_and_cleans_staging(tmp_path, monkeypatch):
    import scripts.restore_runtime as restore_module

    backup = build_snapshot(tmp_path)
    destination = tmp_path / "copy-changed"
    original_copy = restore_module.shutil.copy2

    def copy_then_change(source, target):
        result = original_copy(source, target)
        if source.name == "sample.pdf":
            target.write_bytes(b"changed-during-copy")
        return result

    monkeypatch.setattr(restore_module.shutil, "copy2", copy_then_change)
    with pytest.raises(ValueError, match="复制校验失败"):
        restore_module.restore_backup(backup, destination)
    assert not destination.exists()
    assert list(tmp_path.glob(".copy-changed.restore-*")) == []


def test_restore_rejects_invalid_sqlite_even_with_matching_manifest(tmp_path):
    from scripts.backup_runtime import sha256_file
    from scripts.restore_runtime import restore_backup

    backup = build_snapshot(tmp_path)
    database = backup / "database" / "bid.db"
    database.write_bytes(b"not-a-sqlite-database")
    manifest_path = backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    database_item = next(
        item for item in manifest["files"] if item["path"] == "database/bid.db"
    )
    database_item["size"] = database.stat().st_size
    database_item["sha256"] = sha256_file(database)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    destination = tmp_path / "invalid-sqlite"
    with pytest.raises(ValueError, match="SQLite备份无法打开"):
        restore_backup(backup, destination)
    assert not destination.exists()


def test_restore_rejects_path_traversal_and_extra_files(tmp_path):
    from scripts.restore_runtime import restore_backup

    backup = build_snapshot(tmp_path)
    manifest_path = backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../outside.txt"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="不安全路径"):
        restore_backup(backup, tmp_path / "traversal")

    backup = build_snapshot(tmp_path / "second")
    (backup / "uploads" / "unlisted.pdf").write_bytes(b"unlisted")
    with pytest.raises(ValueError, match="文件集合不一致"):
        restore_backup(backup, tmp_path / "extra")
