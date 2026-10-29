"""Shared dependencies that routes ask for with Depends(...)."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.admin import Admin


def get_db() -> Iterator[Session]:
    """One database session per request, closed when the request ends.

    Closing without commit undoes anything not committed, so a request that
    fails halfway never leaves half-saved changes behind.
    """
    with SessionLocal() as session:
        yield session


# Lets routes write `db: DbSession` instead of `db: Session = Depends(get_db)`
DbSession = Annotated[Session, Depends(get_db)]

# Reads "Authorization: Bearer <token>". auto_error=False: we send our own 401 message.
# It also adds the "Authorize" button to the /docs page.
bearer = HTTPBearer(auto_error=False, description="Paste the accessToken from POST /auth/login")

NOT_SIGNED_IN = "Please sign in to continue."
SESSION_EXPIRED = "Your session has expired. Please sign in again."


def unauthorized(message: str) -> AppError:
    return AppError(401, message)


def get_current_admin(
    db: DbSession, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> Admin:
    """The signed-in admin, or 401. Checked against the database on every request,
    so a deactivated account or a changed password takes effect immediately."""
    if credentials is None:
        raise unauthorized(NOT_SIGNED_IN)
    claims = decode_access_token(credentials.credentials)
    if claims is None or not claims["sub"].isdigit():
        raise unauthorized(SESSION_EXPIRED)
    admin = db.get(Admin, int(claims["sub"]))
    if admin is None or not admin.is_active:
        raise unauthorized(SESSION_EXPIRED)
    # Token from before the last password change: sign out
    if datetime.fromtimestamp(claims["iat"], UTC) < admin.password_changed_at.replace(microsecond=0):
        raise unauthorized(SESSION_EXPIRED)
    return admin


CurrentAdmin = Annotated[Admin, Depends(get_current_admin)]


def require_role(*roles: str):
    """Dependency: signed in AND one of these roles, else 403 (signed in, but not allowed)."""

    def check(admin: CurrentAdmin) -> Admin:
        if admin.role not in roles:
            raise AppError(403, "You don't have permission to do this.")
        return admin

    return check


# Use in routes: dependencies=[StaffOrAdmin] or dependencies=[AdminOnly]
StaffOrAdmin = Depends(require_role("admin", "staff"))
AdminOnly = Depends(require_role("admin"))
