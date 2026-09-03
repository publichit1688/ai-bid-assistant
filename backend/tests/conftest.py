from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def isolated_app(tmp_path_factory: pytest.TempPathFactory):
    """Import the application only after moving SQLite into a temp directory."""
    runtime_dir = tmp_path_factory.mktemp("ai-bid-assistant-tests")
    (runtime_dir / "uploads").mkdir()
    (runtime_dir / "reports").mkdir()

    previous_dir = Path.cwd()
    try:
        # Production uses sqlite:///./bid.db and uploads/. Importing app.main only
        # after this chdir keeps both paths away from the user's workspace data.
        import os

        os.chdir(runtime_dir)

        from app.database import Base, SessionLocal, engine
        from app.main import app

        yield {
            "app": app,
            "engine": engine,
            "session_factory": SessionLocal,
            "runtime_dir": runtime_dir,
        }
    finally:
        if "engine" in locals():
            Base.metadata.drop_all(bind=engine)
            engine.dispose()
        os.chdir(previous_dir)


@pytest.fixture()
def client(isolated_app):
    with TestClient(isolated_app["app"]) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_isolated_database(isolated_app):
    from app.database import Base

    uploads_dir = isolated_app["runtime_dir"] / "uploads"
    reports_dir = isolated_app["runtime_dir"] / "reports"
    for directory in (uploads_dir, reports_dir):
        for path in directory.iterdir():
            if path.is_file():
                path.unlink()
    Base.metadata.drop_all(bind=isolated_app["engine"])
    Base.metadata.create_all(bind=isolated_app["engine"])
    yield
    for directory in (uploads_dir, reports_dir):
        for path in directory.iterdir():
            if path.is_file():
                path.unlink()
