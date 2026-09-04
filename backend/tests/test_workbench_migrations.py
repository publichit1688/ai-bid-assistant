import sqlite3

from sqlalchemy import create_engine, inspect, text


def test_workbench_migration_preserves_legacy_data_and_is_idempotent(tmp_path):
    from app.migrations import (
        MATERIAL_MIGRATION,
        WORKBENCH_MIGRATION,
        WORKBENCH_TABLES,
        run_migrations,
    )

    database_path = tmp_path / "legacy.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE bid_files (
                id INTEGER PRIMARY KEY,
                filename VARCHAR,
                filepath VARCHAR,
                project_name VARCHAR,
                score INTEGER,
                risk_count INTEGER,
                analysis TEXT,
                risk TEXT,
                status VARCHAR,
                created_time DATETIME
            )
            """
        )
        connection.execute(
            "INSERT INTO bid_files (id, filename, filepath, project_name) VALUES (1, 'legacy.pdf', 'uploads/legacy.pdf', '旧项目')"
        )

    migration_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    run_migrations(migration_engine)
    run_migrations(migration_engine)

    tables = set(inspect(migration_engine).get_table_names())
    assert WORKBENCH_TABLES <= tables
    assert "schema_migrations" in tables
    with migration_engine.connect() as connection:
        assert connection.execute(text("SELECT project_name FROM bid_files WHERE id = 1")).scalar_one() == "旧项目"
        assert connection.execute(text("SELECT COUNT(*) FROM schema_migrations WHERE version = :version"), {"version": WORKBENCH_MIGRATION}).scalar_one() == 1
        assert connection.execute(text("SELECT COUNT(*) FROM schema_migrations WHERE version = :version"), {"version": MATERIAL_MIGRATION}).scalar_one() == 1
    migration_engine.dispose()


def test_workbench_migration_does_not_depend_on_metadata_create_all():
    from app.migrations import run_migrations

    migration_engine = create_engine("sqlite:///:memory:")
    run_migrations(migration_engine)
    tables = set(inspect(migration_engine).get_table_names())
    assert "bid_workspaces" in tables
    assert "workspace_revisions" in tables
    assert "response_materials" in tables
    migration_engine.dispose()


def test_workbench_migration_rejects_partial_existing_table_without_recording_success(tmp_path):
    from app.migrations import WORKBENCH_MIGRATION, run_migrations

    database_path = tmp_path / "partial.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE bid_workspaces (id INTEGER PRIMARY KEY)")

    migration_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        try:
            run_migrations(migration_engine)
        except RuntimeError as exc:
            assert "bid_workspaces缺少" in str(exc)
        else:
            raise AssertionError("partial schema must not be accepted")

        with migration_engine.connect() as connection:
            recorded = connection.execute(
                text("SELECT COUNT(*) FROM schema_migrations WHERE version = :version"),
                {"version": WORKBENCH_MIGRATION},
            ).scalar_one()
        assert recorded == 0
    finally:
        migration_engine.dispose()


def test_response_material_migration_upgrades_foundation_and_enforces_contract(tmp_path):
    from app.migrations import MATERIAL_MIGRATION, run_migrations

    database_path = tmp_path / "materials-upgrade.db"
    migration_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    run_migrations(migration_engine)
    with migration_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO bid_workspaces "
                "(id, bid_file_id, title, status, revision, created_time, updated_time) "
                "VALUES (1, 1, '保留工作台', 'draft', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(text("DROP TABLE response_materials"))
        connection.execute(
            text("DELETE FROM schema_migrations WHERE version = :version"),
            {"version": MATERIAL_MIGRATION},
        )

    run_migrations(migration_engine)
    run_migrations(migration_engine)
    with migration_engine.connect() as connection:
        assert connection.execute(text("SELECT title FROM bid_workspaces WHERE id = 1")).scalar_one() == "保留工作台"
        assert connection.execute(
            text("SELECT COUNT(*) FROM schema_migrations WHERE version = :version"),
            {"version": MATERIAL_MIGRATION},
        ).scalar_one() == 1
        columns = {
            row["name"]
            for row in connection.execute(
                text('PRAGMA table_info("response_materials")')
            ).mappings()
        }
        assert {"owner_name", "material_status", "criterion_id", "section_id"} <= columns
    migration_engine.dispose()


def test_response_material_partial_table_is_rejected_without_success_record(tmp_path):
    from app.migrations import MATERIAL_MIGRATION, run_migrations

    database_path = tmp_path / "materials-partial.db"
    migration_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    run_migrations(migration_engine)
    with migration_engine.begin() as connection:
        connection.execute(text("DROP TABLE response_materials"))
        connection.execute(text("CREATE TABLE response_materials (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text("DELETE FROM schema_migrations WHERE version = :version"),
            {"version": MATERIAL_MIGRATION},
        )
    try:
        try:
            run_migrations(migration_engine)
        except RuntimeError as exc:
            assert "response_materials缺少" in str(exc)
        else:
            raise AssertionError("partial response material schema must not be accepted")
        with migration_engine.connect() as connection:
            assert connection.execute(
                text("SELECT COUNT(*) FROM schema_migrations WHERE version = :version"),
                {"version": MATERIAL_MIGRATION},
            ).scalar_one() == 0
    finally:
        migration_engine.dispose()
