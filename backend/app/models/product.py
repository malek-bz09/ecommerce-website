"""The products table."""

from decimal import Decimal

from sqlalchemy import CheckConstraint, Identity, Numeric, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, sql_in

# Keep in sync with `categories` in frontend/src/data/products.js
CATEGORIES = ("tops", "bottoms", "hats")


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    # The database enforces these rules too, so bad data can't get in even through
    # a bug in our code or a manual SQL query. The API checks them first to give
    # friendly messages.
    __table_args__ = (
        CheckConstraint("price > 0", name="price_positive"),
        CheckConstraint(
            "compare_at_price IS NULL OR compare_at_price > price", name="compare_at_price_above_price"
        ),
        CheckConstraint("stock_quantity >= 0", name="stock_not_negative"),
        CheckConstraint(sql_in("category", CATEGORIES), name="category_known"),
    )

    # Identity(): PostgreSQL picks the next number for each new product
    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    # The product's web address (/product/<slug>); unique, and never changed after creation
    # so shared links keep working
    slug: Mapped[str] = mapped_column(String(140), unique=True)
    description: Mapped[str] = mapped_column(Text, server_default="")
    category: Mapped[str] = mapped_column(String(30), index=True)
    # NUMERIC(12, 2): exact decimal money, up to 9,999,999,999.99 (never a float)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # The old price, shown crossed out when the product is on sale
    compare_at_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    image_url: Mapped[str] = mapped_column(String(500))
    stock_quantity: Mapped[int] = mapped_column(server_default="0")
    # Admin switch: false hides the product from the shop without deleting it
    is_available: Mapped[bool] = mapped_column(server_default=true(), index=True)
