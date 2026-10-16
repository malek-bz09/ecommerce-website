"""SQLite database: connection, tables, upgrades and first-run data."""

import os
import sqlite3
from pathlib import Path

from .security import hash_password

DB_PATH = Path(os.environ.get("SHOP_DB", Path(__file__).parent.parent / "data" / "shop.db"))
UPLOAD_DIR = DB_PATH.parent / "uploads"

# Keep in sync with `categories` in src/data/products.js
CATEGORIES = {"tops", "bottoms", "hats"}

ORDER_STATUSES = ("pending", "confirmed", "delivered", "returned", "cancelled")

ORDERS_TABLE = f"""
CREATE TABLE IF NOT EXISTS {{name}} (
    id           TEXT PRIMARY KEY,
    status       TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN {ORDER_STATUSES}),
    created_at   TEXT NOT NULL,
    confirmed_at TEXT,
    delivered_at TEXT,
    returned_at  TEXT,
    cancelled_at TEXT,
    customer_id  INTEGER REFERENCES customers (id),
    full_name    TEXT NOT NULL,
    phone        TEXT NOT NULL,
    email        TEXT NOT NULL,
    wilaya       TEXT NOT NULL,
    commune      TEXT NOT NULL,
    address      TEXT NOT NULL,
    notes        TEXT NOT NULL,
    subtotal     INTEGER NOT NULL,
    delivery_fee INTEGER NOT NULL,
    total        INTEGER NOT NULL
);
"""

ORDER_ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS {name} (
    order_id   TEXT NOT NULL REFERENCES orders (id),
    product_id INTEGER NOT NULL REFERENCES products (id),
    name       TEXT NOT NULL,
    price      INTEGER NOT NULL,
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (order_id, product_id)
);
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id               INTEGER PRIMARY KEY,
    slug             TEXT NOT NULL UNIQUE,
    name             TEXT NOT NULL,
    description      TEXT NOT NULL DEFAULT '',
    category         TEXT NOT NULL,
    price            INTEGER NOT NULL,
    compare_at_price INTEGER,
    stock            INTEGER NOT NULL CHECK (stock >= 0),
    image            TEXT NOT NULL,
    rating           REAL NOT NULL DEFAULT 0,
    review_count     INTEGER NOT NULL DEFAULT 0,
    deleted          INTEGER NOT NULL DEFAULT 0  -- 1 = removed from the shop, kept for old orders
);

CREATE TABLE IF NOT EXISTS customers (
    id         INTEGER PRIMARY KEY,
    full_name  TEXT NOT NULL,
    phone      TEXT NOT NULL UNIQUE,
    email      TEXT NOT NULL,
    wilaya     TEXT NOT NULL,
    commune    TEXT NOT NULL,
    address    TEXT NOT NULL,
    created_at TEXT NOT NULL
);

{orders}
{order_items}

CREATE TABLE IF NOT EXISTS admins (
    username      TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    username   TEXT NOT NULL REFERENCES admins (username),
    expires_at TEXT NOT NULL
);
""".replace("{orders}", ORDERS_TABLE.format(name="orders")).replace(
    "{order_items}", ORDER_ITEMS_TABLE.format(name="order_items")
)

# Starting catalogue. Only used to fill an empty database; after that, products
# are managed from Admin → Products.
SEED_PRODUCTS = [
    {"id": 1, "slug": "burberry-check-collar-polo-navy", "name": "Burberry Check Collar Polo",
     "description": "Navy cotton piqué polo with the signature beige check on the collar.",
     "category": "tops", "price": 8500, "compare_at_price": None, "stock": 6, "rating": 4.8, "review_count": 37},
    {"id": 2, "slug": "weekend-offender-zip-polo-navy", "name": "Weekend Offender Check Zip Polo",
     "description": "Navy quarter-zip polo with a house-check collar and woven chest badge.",
     "category": "tops", "price": 6900, "compare_at_price": 7900, "stock": 10, "rating": 4.6, "review_count": 22},
    {"id": 3, "slug": "burberry-check-hood-zip-hoodie-black", "name": "Burberry Check Hood Zip Hoodie – Black",
     "description": "Black cotton zip-up hoodie lined with the classic check inside the hood.",
     "category": "tops", "price": 14500, "compare_at_price": None, "stock": 4, "rating": 4.9, "review_count": 18},
    {"id": 4, "slug": "burberry-check-hood-zip-hoodie-grey", "name": "Burberry Check Hood Zip Hoodie – Grey",
     "description": "Heather grey zip-up hoodie with an embroidered logo and check-lined hood.",
     "category": "tops", "price": 14500, "compare_at_price": None, "stock": 5, "rating": 4.7, "review_count": 15},
    {"id": 5, "slug": "vintage-wash-barrel-jeans", "name": "Vintage Wash Barrel Jeans",
     "description": "Wide barrel-leg jeans in a faded vintage wash with curved knee seams.",
     "category": "bottoms", "price": 7900, "compare_at_price": None, "stock": 12, "rating": 4.5, "review_count": 29},
    {"id": 6, "slug": "levis-light-wash-straight-jeans", "name": "Levi's Light Wash Straight Jeans",
     "description": "Straight, relaxed-fit jeans in a bleached light-blue wash.",
     "category": "bottoms", "price": 7500, "compare_at_price": 8900, "stock": 9, "rating": 4.6, "review_count": 41},
    {"id": 7, "slug": "levis-550-relaxed-jeans", "name": "Levi's 550 Relaxed Fit Jeans",
     "description": "The classic relaxed-fit 550 in a mid-blue stonewash.",
     "category": "bottoms", "price": 7900, "compare_at_price": None, "stock": 8, "rating": 4.7, "review_count": 33},
    {"id": 8, "slug": "the-north-face-bucket-hat-black", "name": "The North Face Bucket Hat",
     "description": "Black nylon bucket hat with a webbing band and adjustable chin cord.",
     "category": "hats", "price": 3900, "compare_at_price": None, "stock": 15, "rating": 4.4, "review_count": 26},
    {"id": 9, "slug": "weekend-offender-check-bucket-hat", "name": "Weekend Offender Check Bucket Hat",
     "description": "Gingham-check bucket hat with a woven logo patch on the front.",
     "category": "hats", "price": 3500, "compare_at_price": None, "stock": 0, "rating": 4.3, "review_count": 12},
]

# Predefined admin accounts, created only when there are none yet.
# Change these passwords (or add people) with: uv run python -m app.create_admin
SEED_ADMINS = [
    ("admin", "Store Admin", "admin123"),
    ("manager", "Store Manager", "manager123"),
]


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row  # rows behave like dicts: row["name"]
    db.execute("PRAGMA foreign_keys = ON")
    return db


def get_db():
    """FastAPI dependency: one connection per request, closed afterwards."""
    db = connect()
    try:
        yield db
    finally:
        db.close()


def columns(db, table: str) -> set[str]:
    return {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}


def upgrade(db) -> None:
    """Brings a database made by an older version of this app up to date, keeping its data."""
    # v2: products got description, prices, ratings and soft delete
    added = {
        "description": "TEXT NOT NULL DEFAULT ''",
        "compare_at_price": "INTEGER",
        "rating": "REAL NOT NULL DEFAULT 0",
        "review_count": "INTEGER NOT NULL DEFAULT 0",
        "deleted": "INTEGER NOT NULL DEFAULT 0",
    }
    missing = [name for name in added if name not in columns(db, "products")]
    for name in missing:
        db.execute(f"ALTER TABLE products ADD COLUMN {name} {added[name]}")
    if missing:
        db.executemany(
            """UPDATE products SET description = :description, compare_at_price = :compare_at_price,
                                   rating = :rating, review_count = :review_count
               WHERE id = :id""",
            SEED_PRODUCTS,
        )

    db.commit()

    # v2: orders got delivered/returned statuses. SQLite can't change a CHECK rule,
    # so the table is rebuilt the way SQLite recommends: make the new table, copy
    # the rows, drop the old one, give the new one its name.
    if "delivered_at" not in columns(db, "orders"):
        kept = ", ".join(sorted(columns(db, "orders")))
        db.execute("PRAGMA foreign_keys = OFF")  # only works outside a transaction
        db.executescript(f"""
            BEGIN;
            {ORDERS_TABLE.format(name="orders_new")}
            INSERT INTO orders_new ({kept}) SELECT {kept} FROM orders;
            DROP TABLE orders;
            ALTER TABLE orders_new RENAME TO orders;
            COMMIT;
        """)
        db.execute("PRAGMA foreign_keys = ON")

    # Repair: an early build of the step above moved the orders into "orders_old"
    # and left order_items pointing there. Move them back and fix order_items.
    if db.execute("SELECT 1 FROM sqlite_master WHERE name = 'orders_old'").fetchone():
        kept = ", ".join(sorted(columns(db, "orders_old") & columns(db, "orders")))
        item_cols = ", ".join(sorted(columns(db, "order_items")))
        db.execute("PRAGMA foreign_keys = OFF")
        db.executescript(f"""
            BEGIN;
            INSERT OR IGNORE INTO orders ({kept}) SELECT {kept} FROM orders_old;
            {ORDER_ITEMS_TABLE.format(name="order_items_new")}
            INSERT INTO order_items_new ({item_cols}) SELECT {item_cols} FROM order_items;
            DROP TABLE order_items;
            ALTER TABLE order_items_new RENAME TO order_items;
            DROP TABLE orders_old;
            COMMIT;
        """)
        db.execute("PRAGMA foreign_keys = ON")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    db = connect()
    db.executescript(SCHEMA)
    upgrade(db)
    with db:
        if not db.execute("SELECT 1 FROM products LIMIT 1").fetchone():
            db.executemany(
                """INSERT INTO products (id, slug, name, description, category, price,
                                         compare_at_price, stock, image, rating, review_count)
                   VALUES (:id, :slug, :name, :description, :category, :price,
                           :compare_at_price, :stock, '/' || :slug || '.jpg', :rating, :review_count)""",
                SEED_PRODUCTS,
            )
        if not db.execute("SELECT 1 FROM admins LIMIT 1").fetchone():
            db.executemany(
                "INSERT INTO admins (username, name, password_hash) VALUES (?, ?, ?)",
                [(u, n, hash_password(p)) for u, n, p in SEED_ADMINS],
            )
    db.close()
