"""Product endpoints. Routes only translate HTTP ↔ Python; the rules are in
app/services/products.py."""

from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.deps import AdminOnly, DbSession, StaffOrAdmin
from app.schemas.common import Page, page_of
from app.schemas.product import Category, ProductAdmin, ProductCreate, ProductPublic, ProductUpdate
from app.services import products as service

# Shared query parameters for both product lists
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=100, description="Part of the product name")]
InStock = Annotated[bool | None, Query(alias="inStock")]

# ---------- Public: the shop ----------

router = APIRouter(tags=["products"])


@router.get("/products")
def list_products(
    db: DbSession,
    page: PageNumber = 1,
    size: PageSize = 20,
    q: Search = None,
    category: Category | None = None,
    in_stock: InStock = None,
) -> Page[ProductPublic]:
    """Products shown in the shop (hidden products are left out)."""
    items, total = service.list_products(
        db, page=page, size=size, q=q, category=category, in_stock=in_stock, is_available=True
    )
    return page_of(ProductPublic, items, total, page, size)


# Declared before /products/{product_id} so "by-slug" isn't read as an id
@router.get("/products/by-slug/{slug}")
def get_product_by_slug(slug: str, db: DbSession) -> ProductPublic:
    return service.get_product_by_slug(db, slug)


@router.get("/products/{product_id}")
def get_product(product_id: int, db: DbSession) -> ProductPublic:
    return service.get_product(db, product_id)


# ---------- Admin: managing the catalogue ----------
# Every route below needs a signed-in admin or staff member; changing the
# catalogue additionally needs the "admin" role.

admin_router = APIRouter(tags=["products (admin)"], dependencies=[StaffOrAdmin])


@admin_router.get("/admin/products")
def admin_list_products(
    db: DbSession,
    page: PageNumber = 1,
    size: PageSize = 20,
    q: Search = None,
    category: Category | None = None,
    in_stock: InStock = None,
    is_available: Annotated[bool | None, Query(alias="isAvailable")] = None,
) -> Page[ProductAdmin]:
    """Every product, including hidden ones."""
    items, total = service.list_products(
        db, page=page, size=size, q=q, category=category, in_stock=in_stock, is_available=is_available
    )
    return page_of(ProductAdmin, items, total, page, size)


@admin_router.get("/admin/products/{product_id}")
def admin_get_product(product_id: int, db: DbSession) -> ProductAdmin:
    return service.get_product(db, product_id, include_hidden=True)


@admin_router.post("/products", status_code=201, dependencies=[AdminOnly])
def create_product(data: ProductCreate, db: DbSession) -> ProductAdmin:
    return service.create_product(db, data)


@admin_router.patch("/products/{product_id}", dependencies=[AdminOnly])
def update_product(product_id: int, data: ProductUpdate, db: DbSession) -> ProductAdmin:
    return service.update_product(db, product_id, data)


@admin_router.delete("/products/{product_id}", status_code=204, dependencies=[AdminOnly])
def delete_product(product_id: int, db: DbSession) -> Response:
    service.delete_product(db, product_id)
    return Response(status_code=204)
