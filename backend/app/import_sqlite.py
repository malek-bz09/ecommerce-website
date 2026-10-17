"""Copy everything from the old SQLite database into PostgreSQL (one time only).

    uv run python -m app.import_sqlite [path/to/shop.db]

The PostgreSQL tables must still be empty apart from the first-run data
(the sample products and admin accounts), which is replaced.
"""

import sqlite3
import sys
from pathlib import Path

from .database import connect, init_db

# Parents before children, so every reference already exists when a row is copied
TABLES = ["products", "customers", "orders", "order_items", "admins", "sessions"]


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent / "data" / "shop.db")
    if not path.exists():
        sys.exit(f"No SQLite database at {path}")
    old = sqlite3.connect(path)
    old.row_factory = sqlite3.Row

    init_db()
    with connect() as db, db.transaction():
        if db.execute("SELECT 1 FROM orders LIMIT 1").fetchone():
            sys.exit("PostgreSQL already has orders; not importing over them.")
        db.execute(f"TRUNCATE {', '.join(TABLES)}")
        for table in TABLES:
            new_cols = {r["column_name"] for r in db.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table,)
            )}
            old_cols = [r["name"] for r in old.execute(f"PRAGMA table_info({table})")]
            cols = [c for c in old_cols if c in new_cols]
            rows = [tuple(r[c] for c in cols) for r in old.execute(f"SELECT {', '.join(cols)} FROM {table}")]
            if rows:
                db.cursor().executemany(
                    f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})", rows
                )
            print(f"{table}: {len(rows)} rows")
        # New products and customers get ids after the copied ones
        for table in ("products", "customers"):
            db.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 0) + 1, false) FROM {table}"
            )
    print("Done.")


if __name__ == "__main__":
    main()
