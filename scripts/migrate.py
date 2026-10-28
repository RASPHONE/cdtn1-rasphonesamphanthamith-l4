"""Apply database migrations in filename order (db/migrations/NNN_*.sql).

- Builds the schema from an empty database.
- Safe to run again: applied files are recorded in `schema_migrations`
  and skipped; every migration also uses IF NOT EXISTS.
- Each file runs in its own transaction, so a failing file leaves no
  half-applied changes.

Usage:  python scripts/migrate.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import DatabaseUnavailableError, get_connection  # noqa: E402

MIGRATIONS_DIR = ROOT / "db" / "migrations"

CREATE_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename   VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ  NOT NULL DEFAULT now()
)
"""


def list_migration_files():
    return sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))


def migrate() -> int:
    files = list_migration_files()
    if not files:
        print(f"No migration files found in {MIGRATIONS_DIR}")
        return 1

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TRACKING_TABLE)
            cur.execute("SELECT filename FROM schema_migrations")
            applied = {row["filename"] for row in cur.fetchall()}

    newly_applied = 0
    for path in files:
        if path.name in applied:
            print(f"  skip   {path.name} (already applied)")
            continue

        sql = path.read_text(encoding="utf-8")
        # One transaction per file: commit on success, roll back on error.
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (path.name,),
                )
        print(f"  apply  {path.name}")
        newly_applied += 1

    print(f"Migration completed: {newly_applied} applied, {len(files) - newly_applied} already up to date.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(migrate())
    except DatabaseUnavailableError as exc:
        print(f"Error: cannot connect to PostgreSQL ({exc}). Check DB_* values in .env "
              "and that the database exists (see README step 3).")
        sys.exit(1)
