"""Building blocks shared by every schema."""

from decimal import Decimal
from math import ceil
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Python code uses snake_case (compare_at_price); the JSON the frontend sees uses
    camelCase (compareAtPrice). Both spellings are accepted as input."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,  # can be built straight from a database model
        str_strip_whitespace=True,  # "  Polo " → "Polo"
    )


# Money is an exact Decimal inside Python, but is sent as a JSON number (8500.0),
# not a string ("8500.00"): in JavaScript "8500.00" + 600 would give "8500.00600"
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class Page[T](CamelModel):
    """One page of a longer list."""

    items: list[T]
    total: int  # how many items match, across all pages
    page: int
    size: int
    pages: int


def page_of[T](schema: type[T], items, total: int, page: int, size: int) -> Page[T]:
    return Page[schema].model_validate(
        {"items": items, "total": total, "page": page, "size": size, "pages": ceil(total / size)}
    )
