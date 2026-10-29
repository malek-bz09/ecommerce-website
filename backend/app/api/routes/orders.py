"""Order endpoints: checkout for shoppers, management for admins and staff.

There is deliberately no public "get an order" endpoint: the confirmation page
shows the response of POST /orders, so customer details are never readable by
anyone who merely knows (or guesses) an order number.
"""

import uuid
from datetime import date
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response

from app.api.deps import DbSession, StaffOrAdmin
from app.core.config import get_settings
from app.core.rate_limit import RateLimiter
from app.schemas.common import Page, page_of
from app.schemas.order import (
    CustomerSummary,
    OrderCreate,
    OrderDetail,
    OrderPage,
    OrderPlaced,
    OrderStatus,
    OrderSummary,
    StatusChange,
)
from app.services import orders as service

order_limit = RateLimiter("orders", lambda: get_settings().order_rate_limit)

# ---------- Public: checkout ----------

router = APIRouter(tags=["orders"])


@router.post("/orders", status_code=201, dependencies=[Depends(order_limit)])
def place_order(
    data: OrderCreate,
    db: DbSession,
    response: Response,
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=100,
            pattern=r"^[A-Za-z0-9-]+$",
            description="A random id made once per checkout. Sending it again returns the same order.",
        ),
    ] = None,
) -> OrderPlaced:
    order, created = service.place_order(db, data, idempotency_key)
    if not created:
        response.status_code = 200  # nothing new was created
    return OrderPlaced.of(order)


# ---------- Admin and staff ----------

admin_router = APIRouter(prefix="/admin", tags=["orders (admin)"], dependencies=[StaffOrAdmin])

PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=100)]


@admin_router.get("/orders")
def list_orders(
    db: DbSession,
    page: PageNumber = 1,
    size: PageSize = 20,
    status: OrderStatus | None = None,
    q: Annotated[str | None, Query(max_length=100, description="Order number, name, phone or email")] = None,
    date_from: Annotated[date | None, Query(alias="dateFrom", description="YYYY-MM-DD, shop time")] = None,
    date_to: Annotated[date | None, Query(alias="dateTo", description="YYYY-MM-DD, included")] = None,
) -> OrderPage:
    orders, total, status_counts = service.list_orders(
        db, page=page, size=size, status=status, q=q, date_from=date_from, date_to=date_to
    )
    return OrderPage(
        items=[OrderSummary.of(o) for o in orders], total=total, page=page, size=size,
        pages=ceil(total / size), status_counts=status_counts,
    )


@admin_router.get("/orders/{order_id}")
def get_order(order_id: uuid.UUID, db: DbSession) -> OrderDetail:
    return OrderDetail.of(service.get_order(db, order_id))


@admin_router.patch("/orders/{order_id}/status")
def change_status(order_id: uuid.UUID, data: StatusChange, db: DbSession) -> OrderDetail:
    return OrderDetail.of(service.change_status(db, order_id, data.status))


@admin_router.get("/customers")
def list_customers(
    db: DbSession, page: PageNumber = 1, size: PageSize = 20, q: Search = None
) -> Page[CustomerSummary]:
    customers, total = service.list_customers(db, page=page, size=size, q=q)
    return page_of(CustomerSummary, customers, total, page, size)
