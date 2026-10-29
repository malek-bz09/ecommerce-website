"""Admin accounts and sign-in."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import DUMMY_HASH, hash_password, verify_password
from app.models.admin import ROLES, Admin

MIN_PASSWORD_LENGTH = 10


def authenticate(db: Session, email: str, password: str) -> Admin:
    admin = db.scalar(select(Admin).where(Admin.email == email.strip().lower()))
    # Always run one hash check, even for an unknown email (see DUMMY_HASH)
    password_ok = verify_password(password, admin.password_hash if admin else DUMMY_HASH)
    # Same message for every failure, so it doesn't reveal which emails exist
    if not admin or not password_ok or not admin.is_active:
        raise AppError(401, "Incorrect email or password.")
    return admin


def save_admin(db: Session, *, email: str, full_name: str, password: str, role: str) -> tuple[Admin, bool]:
    """Creates the account, or updates it if the email exists. Returns (admin, created)."""
    email = email.strip().lower()
    if "@" not in email:
        raise ValueError("Please enter a valid email address.")
    if not full_name.strip():
        raise ValueError("Please enter a name.")
    if role not in ROLES:
        raise ValueError(f"Role must be one of: {', '.join(ROLES)}.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    admin = db.scalar(select(Admin).where(Admin.email == email))
    created = admin is None
    if created:
        admin = Admin(email=email)
        db.add(admin)
    admin.full_name = full_name.strip()
    admin.role = role
    admin.is_active = True
    admin.password_hash = hash_password(password)
    admin.password_changed_at = func.now()  # signs out any old sessions
    db.commit()
    return admin, created
