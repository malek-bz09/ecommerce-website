"""The order_items table: one row per product in an order."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Identity, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.product import Product

if TYPE_CHECKING:
    from app.models.order import Order


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price > 0", name="unit_price_positive"),
        CheckConstraint("subtotal = unit_price * quantity", name="subtotal_adds_up"),
        # The same product appears once per order (quantities are added together)
        UniqueConstraint("order_id", "product_id", name="uq_order_items_order_id_product_id"),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    # Deleting an order deletes its items
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    # Deleting a product keeps the item (its name and price are copied below) but
    # empties this link
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), index=True)

    # Snapshots: what the customer saw and agreed to, even if the product changes later
    product_name: Mapped[str] = mapped_column(String(120))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int]
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    order: Mapped[Order] = relationship(back_populates="items")
    # The live product, for its current photo and link in the admin (None if deleted)
    product: Mapped[Product | None] = relationship(lazy="selectin")
