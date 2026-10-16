"""Products: the public catalogue for the shop, and create/edit/delete for admins."""

import re
import secrets
import sqlite3
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from .admin import require_admin
from .database import CATEGORIES, UPLOAD_DIR, get_db

router = APIRouter(prefix="/api")
admin_router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


def to_json(row) -> dict:
    """Database row → the shape the React app uses (same as src/data/products.js had)."""
    return {
        "id": row["id"],
        "slug": row["slug"],
        "name": row["name"],
        "description": row["description"],
        "category": row["category"],
        "price": row["price"],
        "compareAtPrice": row["compare_at_price"],
        "stock": row["stock"],
        "images": [row["image"]],
        "rating": row["rating"],
        "reviewCount": row["review_count"],
    }


@router.get("/products")
def list_products(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM products WHERE deleted = 0 ORDER BY id")
    return [to_json(row) for row in rows]


# ---------- Admin ----------

class ProductIn(BaseModel):
    # Numbers are optional here so a missing one gets our friendly message below
    # instead of FastAPI's technical one
    name: str
    description: str = ""
    category: str
    price: int | None = None
    compareAtPrice: int | None = None
    stock: int | None = None
    image: str


def validate_product(p: ProductIn) -> dict[str, str]:
    errors = {}
    if not 2 <= len(p.name.strip()) <= 120:
        errors["name"] = "Name must be between 2 and 120 characters."
    if len(p.description.strip()) > 1000:
        errors["description"] = "Description must be under 1000 characters."
    if p.category not in CATEGORIES:
        errors["category"] = "Please choose a category."
    if p.price is None or p.price < 1:
        errors["price"] = "Price must be at least 1 DZD."
    if p.compareAtPrice is not None and (p.price is None or p.compareAtPrice <= p.price):
        errors["compareAtPrice"] = "The old price must be higher than the price (or left empty)."
    if p.stock is None or p.stock < 0:
        errors["stock"] = "Quantity can't be negative."
    if not p.image.startswith("/"):
        errors["image"] = "Please add a product photo."
    return errors


def check(p: ProductIn):
    errors = validate_product(p)
    if errors:
        raise HTTPException(422, detail={"message": "Please fix the highlighted fields.", "fieldErrors": errors})


def make_slug(db, name: str) -> str:
    """"Levi's 550 Jeans" → "levis-550-jeans", with -2, -3… added if already taken."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower().replace("'", "")).strip("-") or "product"
    slug, n = base, 2
    while db.execute("SELECT 1 FROM products WHERE slug = ?", (slug,)).fetchone():
        slug, n = f"{base}-{n}", n + 1
    return slug


def get_product(db, product_id: int):
    row = db.execute("SELECT * FROM products WHERE id = ? AND deleted = 0", (product_id,)).fetchone()
    if not row:
        raise HTTPException(404, detail={"message": "Product not found."})
    return row


@admin_router.get("/products")
def admin_list_products(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM products WHERE deleted = 0 ORDER BY id DESC")
    return [to_json(row) for row in rows]


@admin_router.get("/products/{product_id}")
def admin_get_product(product_id: int, db: sqlite3.Connection = Depends(get_db)):
    return to_json(get_product(db, product_id))


@admin_router.post("/products", status_code=201)
def create_product(p: ProductIn, db: sqlite3.Connection = Depends(get_db)):
    check(p)
    with db:
        cursor = db.execute(
            """INSERT INTO products (slug, name, description, category, price, compare_at_price, stock, image)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (make_slug(db, p.name), p.name.strip(), p.description.strip(), p.category,
             p.price, p.compareAtPrice, p.stock, p.image),
        )
    return to_json(get_product(db, cursor.lastrowid))


@admin_router.put("/products/{product_id}")
def update_product(product_id: int, p: ProductIn, db: sqlite3.Connection = Depends(get_db)):
    get_product(db, product_id)
    check(p)
    # The slug (the product's web address) stays the same so shared links keep working
    with db:
        db.execute(
            """UPDATE products SET name = ?, description = ?, category = ?, price = ?,
                                   compare_at_price = ?, stock = ?, image = ?
               WHERE id = ?""",
            (p.name.strip(), p.description.strip(), p.category, p.price,
             p.compareAtPrice, p.stock, p.image, product_id),
        )
    return to_json(get_product(db, product_id))


@admin_router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: sqlite3.Connection = Depends(get_db)):
    get_product(db, product_id)
    # "Soft delete": hidden everywhere, but the row stays so past orders still make sense
    with db:
        db.execute("UPDATE products SET deleted = 1 WHERE id = ?", (product_id,))


# Checked by the file's first bytes, not its name: anyone can rename virus.exe to photo.jpg
IMAGE_TYPES = {b"\xff\xd8\xff": ".jpg", b"\x89PNG": ".png", b"RIFF": ".webp"}
MAX_UPLOAD = 5 * 1024 * 1024


@admin_router.post("/uploads", status_code=201)
async def upload_image(file: UploadFile):
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, detail={"message": "The photo must be smaller than 5 MB."})
    ext = next((e for magic, e in IMAGE_TYPES.items() if data.startswith(magic)), None)
    if ext == ".webp" and data[8:12] != b"WEBP":
        ext = None
    if not ext:
        raise HTTPException(415, detail={"message": "Please upload a JPG, PNG or WebP photo."})
    name = f"{secrets.token_hex(8)}{ext}"  # random name: no clashes, no tricks with "../"
    (UPLOAD_DIR / name).write_bytes(data)
    return {"url": f"/api/uploads/{name}"}
