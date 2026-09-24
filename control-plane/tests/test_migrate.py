"""The migration runner must bring an existing database up to the ORM.

``create_all`` creates missing tables and nothing else. A database built before
``008_lead_public_ref.sql`` never gained ``leads.public_ref``, so on current
code ``POST /revenue/leads`` answered 500 on it (reproduced on Postgres 16), and
no database built by ``create_all`` had the ``events`` append-only trigger.
``app/migrate.py`` applies the SQL files; these pin what it relies on.

The file checks need nothing. The Postgres tests need a throwaway database in
``CONTROL_PLANE_TEST_POSTGRES_URL`` (each test works in its own schema and drops
it) and skip without one: SQLite cannot run the SQL files.
"""
from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

import pytest

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"

try:
    os.environ.setdefault("DATABASE_URL", "sqlite://")
    from sqlalchemy import create_engine, text

    from app import migrate
    from app.models import Base

    _HAS_SQLALCHEMY = True
except ImportError:  # pragma: no cover - minimal env runs pure tests only
    _HAS_SQLALCHEMY = False

needs_sqlalchemy = pytest.mark.skipif(not _HAS_SQLALCHEMY, reason="sqlalchemy not installed")

PG_URL = os.environ.get("CONTROL_PLANE_TEST_POSTGRES_URL", "")
needs_postgres = pytest.mark.skipif(
    not (PG_URL and _HAS_SQLALCHEMY), reason="set CONTROL_PLANE_TEST_POSTGRES_URL to a throwaway database"
)


def _sql_files() -> list[Path]:
    return sorted(MIGRATIONS.glob("*.sql"))


def test_every_sql_file_is_named_so_the_runner_sees_it() -> None:
    # The runner applies NNN_name.sql only. A file named any other way would be
    # skipped without a word, which is the drift this runner exists to end.
    pattern = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$")
    misnamed = [path.name for path in _sql_files() if not pattern.match(path.name)]
    assert not misnamed, f"rename to NNN_lowercase_name.sql: {misnamed}"
    prefixes = [path.name[:3] for path in _sql_files()]
    assert len(prefixes) == len(set(prefixes)), f"duplicate migration numbers: {prefixes}"


def test_schema_files_are_rerunnable() -> None:
    # Applied to databases create_all already built, so every CREATE and every
    # ADD COLUMN must tolerate the object already existing.
    unsafe = []
    for path in _sql_files():
        if path.stem.endswith("_seed"):
            continue
        sql = re.sub(r"--[^\n]*", "", path.read_text(encoding="utf-8"))
        for statement in re.findall(
            r"\b(CREATE\s+(?:UNIQUE\s+)?(?:TABLE|INDEX)\s+(?!IF\s+NOT\s+EXISTS)\S+"
            r"|ADD\s+COLUMN\s+(?!IF\s+NOT\s+EXISTS)\S+)",
            sql,
            flags=re.IGNORECASE,
        ):
            unsafe.append(f"{path.name}: {statement}")
    assert not unsafe, f"add IF NOT EXISTS: {unsafe}"


@needs_sqlalchemy
def test_discover_orders_by_number_and_never_applies_seeds() -> None:
    names = [path.name for path in migrate.discover()]
    assert names == sorted(names)
    assert names[0] == "001_init.sql"
    assert "002_seed.sql" not in names  # demo products must never reach a real database
    assert "008_lead_public_ref.sql" in names


@needs_sqlalchemy
def test_sqlite_is_left_to_create_all() -> None:
    engine = create_engine("sqlite://")
    assert migrate.apply_migrations(engine) == []
    assert migrate.status(engine)["skipped"] == [path.name for path in migrate.discover()]


@needs_sqlalchemy
def test_missing_columns_names_the_gap_the_routes_would_hit() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    assert migrate.missing_columns(engine) == {}
    with engine.begin() as conn:
        # SQLite >= 3.35: the pre-008 shape of the table.
        conn.execute(text("DROP INDEX IF EXISTS ix_leads_public_ref"))
        conn.execute(text("ALTER TABLE leads DROP COLUMN public_ref"))
    assert migrate.missing_columns(engine) == {"leads": ["public_ref"]}


@pytest.fixture
def pg_engine():
    schema = f"migrate_test_{uuid.uuid4().hex[:12]}"
    admin = create_engine(PG_URL)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(PG_URL, connect_args={"options": f"-csearch_path={schema}"})
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@needs_postgres
def test_drifted_database_is_repaired_and_keeps_its_rows(pg_engine) -> None:
    Base.metadata.create_all(pg_engine)
    with pg_engine.begin() as conn:
        conn.execute(text("DROP INDEX IF EXISTS ix_leads_public_ref"))
        conn.execute(text("ALTER TABLE leads DROP COLUMN public_ref"))
        conn.execute(text(
            "INSERT INTO leads (full_name, email, service_interest, primary_goal, current_challenge,"
            " business_context, notes, source, consent_marketing, stage, owner, next_action,"
            " lead_score, score_explanation, created_at, updated_at) VALUES ('Existing Lead',"
            " 'lead@example.com', 'audit', 'goal text', 'challenge text', '', '', 'direct', false,"
            " 'QUALIFIED', 'unassigned', 'Review new lead', 70, 'fit', now(), now())"
        ))
    assert migrate.missing_columns(pg_engine) == {"leads": ["public_ref"]}

    applied = migrate.apply_migrations(pg_engine)

    assert applied == [path.name for path in migrate.discover()]
    assert migrate.missing_columns(pg_engine) == {}
    with pg_engine.connect() as conn:
        row = conn.execute(text("SELECT email, public_ref FROM leads")).one()
    assert row.email == "lead@example.com" and row.public_ref is not None
    assert migrate.apply_migrations(pg_engine) == []  # idempotent: second boot does nothing


@needs_postgres
def test_events_ledger_is_append_only_after_migration(pg_engine) -> None:
    Base.metadata.create_all(pg_engine)
    migrate.apply_migrations(pg_engine)
    with pg_engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO events (ts, actor, action, payload, result, risk_score, risk_tier)"
            " VALUES (now(), 'test', 'probe', '{}', 'ok', 0, 'low')"
        ))
    for statement in ("UPDATE events SET actor = 'tamper'", "DELETE FROM events"):
        with pytest.raises(Exception, match="append-only"), pg_engine.begin() as conn:
            conn.execute(text(statement))


@needs_postgres
def test_a_literal_percent_sign_is_sql_not_a_placeholder(pg_engine, tmp_path) -> None:
    # exec_driver_sql passes an empty parameter tuple and psycopg then rejects
    # '%' as a malformed placeholder; the runner must send the file untouched.
    (tmp_path / "001_pct.sql").write_text(
        "CREATE TABLE IF NOT EXISTS pct_probe (v TEXT);\n"
        "INSERT INTO pct_probe SELECT 'a%b' WHERE NOT EXISTS"
        " (SELECT 1 FROM pct_probe WHERE v LIKE 'a%');\n"
    )
    assert migrate.apply_migrations(pg_engine, tmp_path) == ["001_pct.sql"]
    with pg_engine.connect() as conn:
        assert conn.execute(text("SELECT v FROM pct_probe")).scalar_one() == "a%b"


@needs_postgres
def test_a_failing_migration_changes_nothing(pg_engine, tmp_path) -> None:
    (tmp_path / "001_good.sql").write_text("CREATE TABLE IF NOT EXISTS probe_ok (id INT);")
    (tmp_path / "002_bad.sql").write_text("ALTER TABLE no_such_table ADD COLUMN IF NOT EXISTS x INT;")
    with pytest.raises(Exception):
        migrate.apply_migrations(pg_engine, tmp_path)
    with pg_engine.connect() as conn:
        tables = set(conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()"
        )).scalars())
    assert "probe_ok" not in tables  # one transaction: the good file rolled back too
    assert "schema_migrations" not in tables
