import re
import sys
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_connection

def split_sql(sql: str):
    """Removes SQL comments and splits into executable statements."""
    # Remove single-line comments (-- ...)
    sql = re.sub(r'--[^\n]*', '', sql)
    # Remove multi-line comments (/* ... */)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

    statements = []
    current = []
    for line in sql.splitlines():
        line = line.strip()
        if not line:
            continue
        current.append(line)
        if line.endswith(';'):
            stmt = " ".join(current)
            statements.append(stmt)
            current = []
    if current:
        stmt = " ".join(current)
        if stmt:
            statements.append(stmt)
    return statements

def migrate():
    ddl_path = Path(__file__).resolve().parent.parent / "docs" / "ddl_l4.sql"
    if not ddl_path.exists():
        print(f"Error: {ddl_path} not found.")
        sys.exit(1)

    print(f"Reading DDL from {ddl_path}...")
    sql_content = ddl_path.read_text(encoding="utf-8")
    statements = split_sql(sql_content)

    print("Running migrations...")
    with get_connection() as conn:
        with conn.cursor() as cur:
            for i, stmt in enumerate(statements):
                try:
                    cur.execute(stmt)
                except Exception as e:
                    print(f"Error executing statement {i+1}:\n{stmt}\nError: {e}")
                    sys.exit(1)
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
