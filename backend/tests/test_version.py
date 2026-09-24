import json
from pathlib import Path


def test_release_version_is_consistent(isolated_app):
    from app.version import APP_VERSION, VERSION_FILE

    project_root = Path(__file__).resolve().parents[2]
    package = json.loads(
        (project_root / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    lock = json.loads(
        (project_root / "frontend" / "package-lock.json").read_text(
            encoding="utf-8"
        )
    )

    assert VERSION_FILE == project_root / "VERSION"
    assert APP_VERSION == "1.5.3"
    assert isolated_app["app"].version == APP_VERSION
    assert package["version"] == APP_VERSION
    assert lock["version"] == APP_VERSION
    assert lock["packages"][""]["version"] == APP_VERSION
