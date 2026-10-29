"""The admins table: people who can sign in to the admin dashboard."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Identity, String, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, sql_in

# admin: everything. staff: orders and dashboard only (can't change products or prices).
ROLES = ("admin", "staff")


class Admin(TimestampMixin, Base):
    __tablename__ = "admins"
    __table_args__ = (
        CheckConstraint(sql_in("role", ROLES), name="role_known"),
        # Emails are saved lowercase so "Ali@Shop.dz" and "ali@shop.dz" are the same account
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    # Only the Argon2 hash, never the password itself
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), server_default="staff")
    # false blocks sign-in and every existing token at once, without deleting the account
    is_active: Mapped[bool] = mapped_column(server_default=true())
    # Tokens issued before this moment stop working: changing a password signs out everywhere
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
