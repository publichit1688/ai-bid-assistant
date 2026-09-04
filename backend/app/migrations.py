from sqlalchemy import inspect, text


WORKBENCH_MIGRATION = "20260903_01_workbench_foundation"
MATERIAL_MIGRATION = "20260903_02_response_materials"

FOUNDATION_TABLES = {
    "bid_workspaces",
    "source_references",
    "outline_sections",
    "scoring_criteria",
    "criterion_section_mappings",
    "workspace_revisions",
}
MATERIAL_TABLES = {"response_materials"}
WORKBENCH_TABLES = FOUNDATION_TABLES | MATERIAL_TABLES

EXPECTED_COLUMNS = {
    "bid_workspaces": {"id", "bid_file_id", "title", "status", "revision", "created_time", "updated_time"},
    "source_references": {"id", "bid_file_id", "page", "quote", "locator", "fingerprint"},
    "outline_sections": {"id", "workspace_id", "parent_id", "stable_key", "title", "sort_order", "origin", "review_status", "source_ref_id", "created_time", "updated_time"},
    "scoring_criteria": {"id", "workspace_id", "stable_key", "title", "requirement", "max_score", "review_status", "source_ref_id", "created_time", "updated_time"},
    "criterion_section_mappings": {"id", "criterion_id", "section_id", "coverage_status", "rationale", "origin", "created_time", "updated_time"},
    "workspace_revisions": {"id", "workspace_id", "revision", "action", "snapshot", "created_time"},
    "response_materials": {"id", "workspace_id", "criterion_id", "section_id", "stable_key", "title", "material_status", "owner_name", "notes", "created_time", "updated_time"},
}

MIGRATION_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS bid_workspaces (
        id INTEGER PRIMARY KEY,
        bid_file_id INTEGER NOT NULL UNIQUE REFERENCES bid_files(id),
        title VARCHAR NOT NULL,
        status VARCHAR NOT NULL DEFAULT 'draft',
        revision INTEGER NOT NULL DEFAULT 1,
        created_time DATETIME NOT NULL,
        updated_time DATETIME NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS source_references (
        id INTEGER PRIMARY KEY,
        bid_file_id INTEGER NOT NULL REFERENCES bid_files(id),
        page INTEGER,
        quote TEXT NOT NULL,
        locator TEXT,
        fingerprint VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS outline_sections (
        id INTEGER PRIMARY KEY,
        workspace_id INTEGER NOT NULL REFERENCES bid_workspaces(id),
        parent_id INTEGER REFERENCES outline_sections(id),
        stable_key VARCHAR NOT NULL,
        title VARCHAR NOT NULL,
        sort_order INTEGER NOT NULL,
        origin VARCHAR NOT NULL,
        review_status VARCHAR NOT NULL,
        source_ref_id INTEGER REFERENCES source_references(id),
        created_time DATETIME NOT NULL,
        updated_time DATETIME NOT NULL,
        CONSTRAINT uq_outline_workspace_key UNIQUE (workspace_id, stable_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scoring_criteria (
        id INTEGER PRIMARY KEY,
        workspace_id INTEGER NOT NULL REFERENCES bid_workspaces(id),
        stable_key VARCHAR NOT NULL,
        title VARCHAR NOT NULL,
        requirement TEXT NOT NULL,
        max_score NUMERIC,
        review_status VARCHAR NOT NULL,
        source_ref_id INTEGER NOT NULL REFERENCES source_references(id),
        created_time DATETIME NOT NULL,
        updated_time DATETIME NOT NULL,
        CONSTRAINT uq_criterion_workspace_key UNIQUE (workspace_id, stable_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS criterion_section_mappings (
        id INTEGER PRIMARY KEY,
        criterion_id INTEGER NOT NULL REFERENCES scoring_criteria(id),
        section_id INTEGER NOT NULL REFERENCES outline_sections(id),
        coverage_status VARCHAR NOT NULL,
        rationale TEXT,
        origin VARCHAR NOT NULL,
        created_time DATETIME NOT NULL,
        updated_time DATETIME NOT NULL,
        CONSTRAINT uq_criterion_section UNIQUE (criterion_id, section_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workspace_revisions (
        id INTEGER PRIMARY KEY,
        workspace_id INTEGER NOT NULL REFERENCES bid_workspaces(id),
        revision INTEGER NOT NULL,
        action VARCHAR NOT NULL,
        snapshot TEXT NOT NULL,
        created_time DATETIME NOT NULL,
        CONSTRAINT uq_workspace_revision UNIQUE (workspace_id, revision)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_source_references_bid_file_id ON source_references (bid_file_id)",
    "CREATE INDEX IF NOT EXISTS ix_source_references_fingerprint ON source_references (fingerprint)",
    "CREATE INDEX IF NOT EXISTS ix_outline_sections_workspace_id ON outline_sections (workspace_id)",
    "CREATE INDEX IF NOT EXISTS ix_scoring_criteria_workspace_id ON scoring_criteria (workspace_id)",
    "CREATE INDEX IF NOT EXISTS ix_mapping_criterion_id ON criterion_section_mappings (criterion_id)",
    "CREATE INDEX IF NOT EXISTS ix_mapping_section_id ON criterion_section_mappings (section_id)",
    "CREATE INDEX IF NOT EXISTS ix_workspace_revisions_workspace_id ON workspace_revisions (workspace_id)",
)

MATERIAL_MIGRATION_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS response_materials (
        id INTEGER PRIMARY KEY,
        workspace_id INTEGER NOT NULL REFERENCES bid_workspaces(id),
        criterion_id INTEGER REFERENCES scoring_criteria(id),
        section_id INTEGER REFERENCES outline_sections(id),
        stable_key VARCHAR NOT NULL,
        title VARCHAR NOT NULL,
        material_status VARCHAR NOT NULL DEFAULT 'pending',
        owner_name VARCHAR,
        notes TEXT,
        created_time DATETIME NOT NULL,
        updated_time DATETIME NOT NULL,
        CONSTRAINT uq_material_workspace_key UNIQUE (workspace_id, stable_key),
        CONSTRAINT ck_material_target CHECK (criterion_id IS NOT NULL OR section_id IS NOT NULL),
        CONSTRAINT ck_material_status CHECK (material_status IN ('pending', 'in_progress', 'completed', 'blocked'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_response_materials_workspace_id ON response_materials (workspace_id)",
    "CREATE INDEX IF NOT EXISTS ix_response_materials_criterion_id ON response_materials (criterion_id)",
    "CREATE INDEX IF NOT EXISTS ix_response_materials_section_id ON response_materials (section_id)",
)


def _validate_workbench_columns(connection, table_names):
    invalid = []
    for table_name in table_names:
        expected = EXPECTED_COLUMNS[table_name]
        rows = connection.execute(text(f'PRAGMA table_info("{table_name}")')).mappings()
        actual = {row["name"] for row in rows}
        if not expected <= actual:
            invalid.append(f"{table_name}缺少{','.join(sorted(expected - actual))}")
    if invalid:
        raise RuntimeError("工作台迁移结构不完整: " + "; ".join(invalid))


def _apply_migration(connection, version, statements, table_names):
    applied = connection.execute(
        text("SELECT 1 FROM schema_migrations WHERE version = :version"),
        {"version": version},
    ).first()
    if not applied:
        existing = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            )
        }
        existing_targets = set(table_names) & existing
        if existing_targets:
            _validate_workbench_columns(connection, existing_targets)
        for statement in statements:
            connection.execute(text(statement))
        _validate_workbench_columns(connection, table_names)
        connection.execute(
            text("INSERT INTO schema_migrations (version) VALUES (:version)"),
            {"version": version},
        )
    else:
        _validate_workbench_columns(connection, table_names)


def run_migrations(engine):
    """Apply additive, versioned migrations without replacing existing data."""
    if engine.dialect.name != "sqlite":
        raise RuntimeError("当前迁移仅支持SQLite，请先完成目标数据库迁移适配。")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR PRIMARY KEY,
                    applied_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        _apply_migration(
            connection,
            WORKBENCH_MIGRATION,
            MIGRATION_STATEMENTS,
            FOUNDATION_TABLES,
        )
        _apply_migration(
            connection,
            MATERIAL_MIGRATION,
            MATERIAL_MIGRATION_STATEMENTS,
            MATERIAL_TABLES,
        )

    existing_tables = set(inspect(engine).get_table_names())
    missing_tables = WORKBENCH_TABLES - existing_tables
    if missing_tables:
        raise RuntimeError("工作台迁移不完整: " + ", ".join(sorted(missing_tables)))
