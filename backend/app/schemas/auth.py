"""What the sign-in endpoints accept and return."""

from pydantic import Field

from app.schemas.common import CamelModel


class LoginIn(CamelModel):
    email: str = Field(min_length=3, max_length=254)
    # No strip: spaces can be part of a password
    password: str = Field(min_length=1, max_length=256, json_schema_extra={"format": "password"})


class AdminOut(CamelModel):
    """An admin as shown to the frontend. Never includes the password hash."""

    id: int
    email: str
    full_name: str
    role: str


class TokenOut(CamelModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: AdminOut
