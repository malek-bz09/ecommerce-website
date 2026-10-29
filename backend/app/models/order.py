"""The orders table, plus the rules for how an order's status may change."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, sql_in
from app.models.order_item import OrderItem

# Keep in sync with STATUSES in frontend/src/pages/admin/orderStatus.js
ORDER_STATUSES = ("pending", "confirmed", "processing", "shipped", "delivered", "cancelled", "returned")

# What each status may change to. Anything else is refused.
TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending": ("confirmed", "cancelled"),
    "confirmed": ("processing", "cancelled"),
    "processing": ("shipped", "cancelled"),
    "shipped": ("delivered", "returned"),  # returned = refused at the door
    "delivered": ("returned",),
    "cancelled": (),
    "returned": (),
}

# Stock is taken when the order is placed, and given back when it ends in one of these
RESTOCKING_STATUSES = ("cancelled", "returned")

# Cash on delivery is the only payment method for now
PAYMENT_METHODS = ("cod",)


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(sql_in("status", ORDER_STATUSES), name="status_known"),
        CheckConstraint(sql_in("payment_method", PAYMENT_METHODS), name="payment_method_known"),
        CheckConstraint("subtotal >= 0 AND delivery_fee >= 0", name="amounts_not_negative"),
        CheckConstraint("total_amount = subtotal + delivery_fee", name="total_adds_up"),
        # The admin list is sorted newest first, and filtered by date
        Index("ix_orders_created_at", "created_at"),
    )

    # A random UUID: used in admin URLs; can't be guessed or counted through
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # What people see and say on the phone, e.g. "ORD-7K3F9Q2M" (also random, not a counter)
    order_number: Mapped[str] = mapped_column(String(20), unique=True)
    status: Mapped[str] = mapped_column(String(20), server_default="pending", index=True)

    # A copy of the customer's details as they were when ordering
    customer_name: Mapped[str] = mapped_column(String(80))
    customer_phone: Mapped[str] = mapped_column(String(10), index=True)  # normalised: 0XXXXXXXXX
    customer_email: Mapped[str | None] = mapped_column(String(254))
    wilaya_code: Mapped[str] = mapped_column(String(2))
    wilaya: Mapped[str] = mapped_column(String(40))
    commune: Mapped[str] = mapped_column(String(60))
    shipping_address: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, server_default="")

    payment_method: Mapped[str] = mapped_column(String(20), server_default="cod")
    # Calculated by the server from database prices, never taken from the browser
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    # Sent by the checkout page; the same key twice means "the same order", not a second one
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True)

    # When each step happened (null = not yet)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # lazy="selectin": loading orders also loads their items, in one extra query
    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin", order_by="OrderItem.id"
    )
