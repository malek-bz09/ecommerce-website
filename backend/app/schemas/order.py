"""What the order endpoints accept and return.

The checkout request keeps the shape the existing checkout page already sends:
{"customer": {...}, "items": [{"id": productId, "quantity": n}]}.
"""

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.core.algeria import WILAYA_BY_CODE, normalize_phone
from app.models.order import ORDER_STATUSES, TRANSITIONS, Order, OrderItem
from app.schemas.common import CamelModel, Money, Page

OrderStatus = Literal[ORDER_STATUSES]

NAME_PATTERN = re.compile(r"^(?:[^\W\d_]|[\s'.-])+$")  # letters (any language), spaces, ' . -
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")

# ---------- Checkout (public) ----------


class CustomerIn(CamelModel):
    full_name: str = Field(max_length=80)
    phone: str = Field(max_length=20)
    email: str | None = Field(None, max_length=254)
    wilaya: str  # the 2-digit code, e.g. "16"
    commune: str = Field(max_length=60)
    address: str = Field(max_length=200)
    notes: str = Field("", max_length=500)

    @field_validator("full_name")
    @classmethod
    def check_name(cls, value: str) -> str:
        if len(value) < 3 or not NAME_PATTERN.match(value):
            raise ValueError("Please enter a valid full name.")
        if len(value.split()) < 2:
            raise ValueError("Please enter your first and last name.")
        return value

    @field_validator("phone")
    @classmethod
    def check_phone(cls, value: str) -> str:
        phone = normalize_phone(value)
        if not phone:
            raise ValueError("Enter a valid mobile number, e.g. 0555 12 34 56.")
        return phone  # saved in one format, so searching and grouping by phone works

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str | None) -> str | None:
        if not value:
            return None  # optional
        if not EMAIL_PATTERN.match(value):
            raise ValueError("Enter a valid email address, e.g. name@example.com.")
        return value.lower()

    @field_validator("wilaya")
    @classmethod
    def check_wilaya(cls, value: str) -> str:
        if value not in WILAYA_BY_CODE:
            raise ValueError("Please select a valid wilaya.")
        return value

    @field_validator("commune")
    @classmethod
    def check_commune(cls, value: str) -> str:
        if len(value) < 2:
            raise ValueError("Please enter your commune.")
        return value

    @field_validator("address")
    @classmethod
    def check_address(cls, value: str) -> str:
        if len(value) < 10:
            raise ValueError("Please give a more detailed address (street, building, floor…).")
        return value


class ItemIn(CamelModel):
    id: int = Field(ge=1)  # product id
    quantity: int = Field(ge=1, le=100)


class OrderCreate(CamelModel):
    customer: CustomerIn
    # Prices are deliberately not accepted: the server looks them up
    items: list[ItemIn] = Field(max_length=50)


# ---------- Responses ----------


class CustomerOut(CamelModel):
    full_name: str
    phone: str
    email: str | None
    wilaya: str  # the name, e.g. "Alger"
    commune: str
    address: str
    notes: str


def customer_of(order: Order) -> CustomerOut:
    return CustomerOut(
        full_name=order.customer_name, phone=order.customer_phone, email=order.customer_email,
        wilaya=order.wilaya, commune=order.commune, address=order.shipping_address, notes=order.notes,
    )


class LineOut(CamelModel):
    id: int | None  # the product's id; null if the product was deleted since
    name: str
    price: Money
    quantity: int
    subtotal: Money


def line_of(item: OrderItem) -> dict:
    return {"id": item.product_id, "name": item.product_name, "price": item.unit_price,
            "quantity": item.quantity, "subtotal": item.subtotal}


class OrderPlaced(CamelModel):
    """Returned to the shopper after checkout (shown on the confirmation page)."""

    order_number: str
    status: str
    payment_method: str
    customer: CustomerOut
    lines: list[LineOut]
    subtotal: Money
    delivery_fee: Money
    total: Money
    created_at: datetime

    @classmethod
    def of(cls, order: Order) -> "OrderPlaced":
        return cls(
            order_number=order.order_number, status=order.status, payment_method=order.payment_method,
            customer=customer_of(order), lines=[line_of(i) for i in order.items],
            subtotal=order.subtotal, delivery_fee=order.delivery_fee, total=order.total_amount,
            created_at=order.created_at,
        )


# ---------- Admin ----------


class OrderSummary(CamelModel):
    """One row of the admin order list."""

    id: uuid.UUID
    order_number: str
    status: str
    created_at: datetime
    customer: CustomerOut
    item_count: int
    total: Money

    @classmethod
    def of(cls, order: Order) -> "OrderSummary":
        return cls(
            id=order.id, order_number=order.order_number, status=order.status, created_at=order.created_at,
            customer=customer_of(order), item_count=sum(i.quantity for i in order.items),
            total=order.total_amount,
        )


class OrderPage(Page[OrderSummary]):
    # How many orders have each status (with the same search and dates), for the tabs
    status_counts: dict[str, int]


class AdminLineOut(LineOut):
    image: str | None  # the product's current photo
    slug: str | None  # for a link to the product in the shop; null if deleted or hidden


class OrderDetail(CamelModel):
    id: uuid.UUID
    order_number: str
    status: str
    next_statuses: list[str]  # what the admin may change it to; the page shows one button each
    history: dict[str, datetime | None]  # when each step happened (null = not yet)
    customer: CustomerOut
    lines: list[AdminLineOut]
    subtotal: Money
    delivery_fee: Money
    total: Money
    payment_method: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, order: Order) -> "OrderDetail":
        def admin_line(item: OrderItem) -> dict:
            product = item.product
            return line_of(item) | {
                "image": product.image_url if product else None,
                "slug": product.slug if product and product.is_available else None,
            }

        history = {"pending": order.created_at} | {
            status: getattr(order, f"{status}_at") for status in ORDER_STATUSES if status != "pending"
        }
        return cls(
            id=order.id, order_number=order.order_number, status=order.status,
            next_statuses=list(TRANSITIONS[order.status]), history=history, customer=customer_of(order),
            lines=[admin_line(i) for i in order.items], subtotal=order.subtotal,
            delivery_fee=order.delivery_fee, total=order.total_amount, payment_method=order.payment_method,
            created_at=order.created_at, updated_at=order.updated_at,
        )


class StatusChange(CamelModel):
    status: OrderStatus


class CustomerSummary(CamelModel):
    """A buyer, put together from their orders (one per phone number)."""

    id: str  # the phone number: what identifies a customer without accounts
    full_name: str
    phone: str
    email: str | None
    wilaya: str
    commune: str
    address: str
    order_count: int
    total_spent: Money  # delivered orders only, like revenue
    last_order_at: datetime
