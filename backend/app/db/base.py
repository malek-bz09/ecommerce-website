"""The base class every database model inherits from."""

from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Gives every index and constraint a predictable name (e.g. "uq_products_slug").
# Alembic needs names to be able to drop or change them in later migrations.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def sql_in(column: str, values: tuple[str, ...]) -> str:
    """SQL for a CHECK rule: sql_in("role", ("admin", "staff")) → "role IN ('admin', 'staff')".
    (Python's own tuple text would give ('cod',) for one value, which isn't valid SQL.)"""
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Adds created_at / updated_at, set by the database itself.

    timezone=True stores them as PostgreSQL "timestamptz": always saved in UTC,
    so times never depend on where the server happens to run.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
