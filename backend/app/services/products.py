"""Product business logic. Routes call these functions; they never touch the
database directly, so the rules live in one place and are easy to test."""

import re
import unicodedata
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate

# The API field names that differ from the database column names
COLUMN_FOR_FIELD = {"stock": "stock_quantity"}


def escape_like(text: str) -> str:
    # In LIKE patterns % and _ are wildcards; a search for "100%" should mean the character
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_products(
    db: Session,
    *,
    page: int,
    size: int,
    q: str | None = None,
    category: str | None = None,
    in_stock: bool | None = None,
    is_available: bool | None = None,
) -> tuple[list[Product], int]:
    """Returns one page of matching products, plus how many match in total."""
    query = select(Product)
    if q:
        # ILIKE: case-insensitive, so "polo" finds "Burberry Check Collar Polo"
        query = query.where(Product.name.ilike(f"%{escape_like(q)}%", escape="\\"))
    if category:
        query = query.where(Product.category == category)
    if in_stock is not None:
        query = query.where(Product.stock_quantity > 0 if in_stock else Product.stock_quantity == 0)
    if is_available is not None:
        query = query.where(Product.is_available == is_available)

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    # id breaks ties so the order is stable and no product appears on two pages
    items = db.scalars(
        query.order_by(Product.created_at.desc(), Product.id.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return list(items), total


def get_product(db: Session, product_id: int, *, include_hidden: bool = False) -> Product:
    product = db.get(Product, product_id)
    # A hidden product is "not found" for shoppers, so they can't tell it exists
    if not product or (not product.is_available and not include_hidden):
        raise AppError(404, "Product not found.")
    return product


def get_product_by_slug(db: Session, slug: str) -> Product:
    product = db.scalar(select(Product).where(Product.slug == slug, Product.is_available))
    if not product:
        raise AppError(404, "Product not found.")
    return product


def slugify(name: str) -> str:
    """"Levi's 550 Jeans" → "levis-550-jeans"."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower().replace("'", "")).strip("-")[:120] or "product"


def unique_slug(db: Session, name: str) -> str:
    """slugify(name), with -2, -3… added if that slug is already taken."""
    base = slugify(name)
    taken = set(
        db.scalars(
            select(Product.slug).where(
                or_(Product.slug == base, Product.slug.like(f"{escape_like(base)}-%", escape="\\"))
            )
        )
    )
    slug, n = base, 2
    while slug in taken:
        slug, n = f"{base}-{n}", n + 1
    return slug


def check_prices(price: Decimal, compare_at_price: Decimal | None) -> None:
    if compare_at_price is not None and compare_at_price <= price:
        raise AppError(
            422,
            "Please fix the highlighted fields.",
            fieldErrors={"compareAtPrice": "The old price must be higher than the price (or left empty)."},
        )


def save(db: Session, product: Product) -> Product:
    """Commits, turning a clash with another product's slug into a clear error."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig.diag, "constraint_name", None) == "uq_products_slug":
            # Two products with the same name created at the same instant
            raise AppError(409, "Another product with this name was just saved. Please try again.") from exc
        raise
    db.refresh(product)  # load values the database filled in (id, created_at, updated_at)
    return product


def create_product(db: Session, data: ProductCreate) -> Product:
    check_prices(data.price, data.compare_at_price)
    product = Product(
        name=data.name,
        slug=unique_slug(db, data.name),
        description=data.description,
        category=data.category,
        price=data.price,
        compare_at_price=data.compare_at_price,
        stock_quantity=data.stock,
        image_url=data.image_url,
        is_available=data.is_available,
    )
    db.add(product)
    return save(db, product)


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
    product = get_product(db, product_id, include_hidden=True)
    # exclude_unset: only the fields the request actually contained
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(product, COLUMN_FOR_FIELD.get(field, field), value)
    # Checked on the combined result: e.g. lowering only the price below the old price
    check_prices(product.price, product.compare_at_price)
    # The slug stays the same when the name changes, so shared links keep working
    return save(db, product)


def delete_product(db: Session, product_id: int) -> None:
    product = get_product(db, product_id, include_hidden=True)
    db.delete(product)
    db.commit()
