"""Admin sign-in.

There is no logout endpoint: a JWT can't be "switched off" on the server without
extra storage, so signing out means the frontend forgets the token. Tokens expire
after ACCESS_TOKEN_MINUTES; deactivating an account or changing its password
blocks its tokens at once (see get_current_admin).
"""

from fastapi import APIRouter, Depends

from app.api.deps import CurrentAdmin, DbSession
from app.core.config import get_settings
from app.core.rate_limit import RateLimiter
from app.core.security import create_access_token
from app.schemas.auth import AdminOut, LoginIn, TokenOut
from app.services import auth as service

router = APIRouter(prefix="/auth", tags=["auth"])

login_limit = RateLimiter("login", lambda: get_settings().login_rate_limit)


@router.post("/login", dependencies=[Depends(login_limit)])
def login(data: LoginIn, db: DbSession) -> TokenOut:
    admin = service.authenticate(db, data.email, data.password)
    token, expires_in = create_access_token(admin.id, admin.role)
    return TokenOut(access_token=token, expires_in=expires_in, user=AdminOut.model_validate(admin))


@router.get("/me")
def me(admin: CurrentAdmin) -> AdminOut:
    return admin
