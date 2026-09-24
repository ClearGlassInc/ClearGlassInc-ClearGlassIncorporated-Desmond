"""Apply ``migrations/*.sql`` to Postgres, once each, in order.

Why this exists: the Render blueprint boots with ``AUTO_CREATE_TABLES=true``,
and ``Base.metadata.create_all`` creates missing *tables*, never missing
*columns*, indexes on existing tables, or triggers. Nothing else in the repo
applied the SQL files. So:

- a database created before ``008_lead_public_ref.sql`` never gains
  ``leads.public_ref``, and every query on ``Lead`` fails — ``POST
  /revenue/leads`` answers 500 (reproduced against Postgres 16);
- the ``events`` append-only trigger from ``001_init.sql`` is never installed,
  so the audit ledger is append-only by convention only.

Every schema file here is written to be re-runnable (``IF NOT EXISTS``,
guarded ``UPDATE``s, ``CREATE OR REPLACE``), so applying one to a database that
``create_all`` already built is a no-op for what exists and adds what does not.
Seed files (``*_seed.sql``) hold demo rows and are never applied here.

Opt-in with ``RUN_MIGRATIONS=true``; off by default, so nothing changes for a
deployment that does not ask for it. SQLite (dev, tests) is skipped:
``create_all`` is complete there.

    python -m app.migrate            # apply pending migrations
    python -m app.migrate --status   # list applied / pending, change nothing
    python -m app.migrate --check    # exit 1 if a mapped column is missing
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine

logger = logging.getLogger("clearglass.migrate")

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
_FILENAME = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$")
# Arbitrary constant: serialises runners across instances booting at once.
_LOCK_KEY = 7_401_001

_LEDGER_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    VARCHAR(160) PRIMARY KEY,
    sha256      CHAR(64)     NOT NULL,
    applied_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
)
"""


def is_seed(path: Path) -> bool:
    """Demo data, not schema. Never applied to a real database by this runner."""
    return path.stem.endswith("_seed")


def discover(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    """Schema migrations in apply order (the ``NNN_`` prefix), seeds excluded."""
    return sorted(
        path for path in directory.glob("*.sql")
        if _FILENAME.match(path.name) and not is_seed(path)
    )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _applied(conn: Connection) -> set[str]:
    return set(conn.execute(text("SELECT filename FROM schema_migrations")).scalars())


def status(engine: Engine, directory: Path = MIGRATIONS_DIR) -> dict[str, list[str]]:
    """Which schema files are recorded as applied and which are pending."""
    files = [path.name for path in discover(directory)]
    if engine.dialect.name != "postgresql":
        return {"applied": [], "pending": [], "skipped": files}
    with engine.connect() as conn:
        has_ledger = inspect(conn).has_table("schema_migrations")
        applied = _applied(conn) if has_ledger else set()
    return {
        "applied": [name for name in files if name in applied],
        "pending": [name for name in files if name not in applied],
        "skipped": [],
    }


def apply_migrations(engine: Engine, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply every pending schema file; return the names applied.

    All pending files run in one transaction under an advisory lock, so a
    failure leaves the database exactly as it was and a second instance
    booting at the same time waits, then finds nothing left to do. The error
    propagates: a control plane whose schema cannot be brought up to date
    should not start and answer 500s.
    """
    if engine.dialect.name != "postgresql":
        return []
    applied_now: list[str] = []
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _LOCK_KEY})
        conn.execute(text(_LEDGER_DDL))
        done = _applied(conn)
        for path in discover(directory):
            if path.name in done:
                continue
            # No bound parameters, so psycopg sends the file as one simple
            # query: multiple statements and $$-quoted function bodies work.
            conn.exec_driver_sql(path.read_text(encoding="utf-8"))
            conn.execute(
                text("INSERT INTO schema_migrations (filename, sha256) VALUES (:f, :s)"),
                {"f": path.name, "s": _digest(path)},
            )
            applied_now.append(path.name)
    if applied_now:
        logger.info("applied migrations: %s", ", ".join(applied_now))
    return applied_now


def missing_columns(engine: Engine, metadata=None) -> dict[str, list[str]]:
    """ORM-mapped columns the database does not have, per table.

    A missing *table* is reported as all of its columns. Empty means every
    mapped column exists, which is what the routes need to not 500.
    """
    if metadata is None:
        from .models import Base

        metadata = Base.metadata
    with engine.connect() as conn:
        inspector = inspect(conn)
        existing_tables = set(inspector.get_table_names())
        gaps: dict[str, list[str]] = {}
        for table in metadata.sorted_tables:
            wanted = [column.name for column in table.columns]
            if table.name not in existing_tables:
                gaps[table.name] = wanted
                continue
            have = {column["name"] for column in inspector.get_columns(table.name)}
            absent = [name for name in wanted if name not in have]
            if absent:
                gaps[table.name] = absent
    return gaps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.migrate", description=__doc__.split("\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--status", action="store_true", help="list applied/pending; change nothing")
    mode.add_argument("--check", action="store_true", help="exit 1 if a mapped column is missing")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from .db import engine

    if args.status:
        print(json.dumps(status(engine), indent=2))
        return 0
    if args.check:
        gaps = missing_columns(engine)
        print(json.dumps({"missing_columns": gaps}, indent=2))
        return 1 if gaps else 0
    applied = apply_migrations(engine)
    print(json.dumps({"applied": applied, **status(engine)}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
