"""What the product endpoints accept and return.

Field names follow what the existing frontend already uses (`stock`, `images`),
while the database uses the longer names (`stock_quantity`, `image_url`).
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, computed_field, field_validator

from app.models.product import CATEGORIES
from app.schemas.common import CamelModel, Money

Category = Literal[CATEGORIES]

# max_digits/decimal_places match the NUMERIC(12, 2) column
Price = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
Name = Annotated[str, Field(min_length=2, max_length=120)]
Description = Annotated[str, Field(max_length=2000)]
Stock = Annotated[int, Field(ge=0, le=1_000_000)]
ImageUrl = Annotated[str, Field(min_length=1, max_length=500)]


def check_image_url(value: str | None) -> str | None:
    # A path on our own site (/polo.jpg, /api/v1/uploads/...) or a full web address.
    # Rejects things like "javascript:..." that would be dangerous inside <img src>.
    if value is not None and not value.startswith(("/", "https://", "http://")):
        raise ValueError("Image must be a web address (https://...) or a path starting with /.")
    return value


# ---------- Responses ----------


class ProductPublic(CamelModel):
    """What anyone browsing the shop may see."""

    id: int
    slug: str
    name: str
    description: str
    category: str
    price: Money
    compare_at_price: Money | None
    stock: int = Field(validation_alias="stock_quantity")
    image_url: str = Field(exclude=True)  # sent as `images` below instead

    @computed_field
    @property
    def images(self) -> list[str]:
        # The frontend shows a list of photos; we store one for now
        return [self.image_url]


class ProductAdmin(ProductPublic):
    """Everything, for the admin pages."""

    image_url: str
    is_available: bool
    created_at: datetime
    updated_at: datetime


# ---------- Requests ----------


class ProductCreate(CamelModel):
    name: Name
    description: Description = ""
    category: Category
    price: Price
    compare_at_price: Price | None = None
    stock: Stock
    image_url: ImageUrl
    is_available: bool = True

    _image = field_validator("image_url")(check_image_url)


class ProductUpdate(CamelModel):
    """PATCH: send only the fields that change. Leaving a field out keeps its value."""

    name: Name | None = None
    description: Description | None = None
    category: Category | None = None
    price: Price | None = None
    compare_at_price: Price | None = None  # null removes the old price (sale ends)
    stock: Stock | None = None
    image_url: ImageUrl | None = None
    is_available: bool | None = None

    _image = field_validator("image_url")(check_image_url)

    @field_validator("name", "description", "category", "price", "stock", "image_url", "is_available")
    @classmethod
    def not_null(cls, value):
        # Only runs for fields actually sent: {"price": null} is a mistake, not "no change"
        if value is None:
            raise ValueError("This field can't be empty.")
        return value
