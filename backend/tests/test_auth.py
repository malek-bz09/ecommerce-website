"""Phase 4: sign-in, tokens, roles, rate limiting, uploads."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.security import JWT_ALGORITHM
from app.db.session import SessionLocal
from app.models.admin import Admin
from app.services.auth import save_admin
from tests.conftest import PASSWORD

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
SECRET = "test-only-secret-key-that-is-long-enough-1234"


def login(client, email="boss@shop.dz", password=PASSWORD):
    return client.post(LOGIN, json={"email": email, "password": password})


# ---------- Login ----------


def test_login_returns_a_token_that_works(client, make_admin):
    make_admin()
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["tokenType"] == "bearer"
    assert body["expiresIn"] == 8 * 60 * 60
    assert body["user"] == {"id": 1, "email": "boss@shop.dz", "fullName": "Shop Boss", "role": "admin"}

    me = client.get(ME, headers={"Authorization": f"Bearer {body['accessToken']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "boss@shop.dz"


def test_email_is_not_case_sensitive(client, make_admin):
    make_admin()
    assert login(client, email="  BOSS@Shop.DZ ").status_code == 200


@pytest.mark.parametrize(
    ("email", "password"), [("boss@shop.dz", "wrong password"), ("nobody@shop.dz", PASSWORD)]
)
def test_wrong_email_or_password_get_the_same_answer(client, make_admin, email, password):
    make_admin()
    response = login(client, email=email, password=password)
    assert response.status_code == 401
    assert response.json() == {"detail": {"message": "Incorrect email or password."}}


def test_deactivated_admin_cannot_sign_in_and_is_signed_out(client, make_admin, admin_client):
    with SessionLocal() as db:
        db.query(Admin).update({"is_active": False})
        db.commit()
    assert login(client).status_code == 401
    assert admin_client.get(ME).status_code == 401


def test_password_hash_is_argon2_and_never_returned(client, make_admin):
    admin = make_admin()
    assert admin.password_hash.startswith("$argon2id$")
    body = login(client).text
    assert "password" not in body.lower() and "argon" not in body


# ---------- Tokens ----------


def make_token(sub="1", role="admin", minutes=60, secret=SECRET, iat=None):
    now = datetime.now(UTC)
    claims = {"sub": sub, "role": role, "iat": iat or now, "exp": now + timedelta(minutes=minutes)}
    return jwt.encode(claims, secret, algorithm=JWT_ALGORITHM)


@pytest.mark.parametrize(
    "token",
    [
        "not-a-token",
        make_token(minutes=-1),  # expired
        make_token(secret="someone-elses-key-someone-elses-key-1234"),  # forged
        make_token(sub="999"),  # account doesn't exist
        make_token(sub="abc"),
    ],
)
def test_bad_tokens_are_rejected(client, make_admin, token):
    make_admin()
    response = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json() == {"detail": {"message": "Your session has expired. Please sign in again."}}


def test_unsigned_token_is_rejected(client, make_admin):
    # The classic JWT attack: a token that says "alg: none" and has no signature
    make_admin()
    token = jwt.encode({"sub": "1", "role": "admin", "iat": 1, "exp": 9_999_999_999}, None, algorithm="none")
    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_changing_password_signs_out_old_tokens(client, make_admin):
    make_admin()
    with SessionLocal() as db:  # pretend the account was set up 10 minutes ago
        db.query(Admin).update({"password_changed_at": datetime.now(UTC) - timedelta(minutes=10)})
        db.commit()
    old_token = make_token(iat=datetime.now(UTC) - timedelta(minutes=5))
    assert client.get(ME, headers={"Authorization": f"Bearer {old_token}"}).status_code == 200
    with SessionLocal() as db:
        save_admin(db, email="boss@shop.dz", full_name="Shop Boss", password="a brand new password", role="admin")
    assert client.get(ME, headers={"Authorization": f"Bearer {old_token}"}).status_code == 401


def test_missing_token(client):
    response = client.get(ME)
    assert response.status_code == 401
    assert response.json() == {"detail": {"message": "Please sign in to continue."}}


# ---------- Who may do what ----------

ADMIN_ONLY = [
    ("post", "/api/v1/products"),
    ("patch", "/api/v1/products/1"),
    ("delete", "/api/v1/products/1"),
    ("post", "/api/v1/admin/uploads"),
]
STAFF_OR_ADMIN = [
    ("get", "/api/v1/admin/products"),
    ("get", "/api/v1/admin/products/1"),
]


@pytest.mark.parametrize(("method", "url"), ADMIN_ONLY + STAFF_OR_ADMIN)
def test_public_cannot_use_admin_endpoints(client, method, url):
    assert getattr(client, method)(url).status_code == 401


@pytest.mark.parametrize(("method", "url"), ADMIN_ONLY)
def test_staff_cannot_change_the_catalogue(staff_client, method, url):
    response = getattr(staff_client, method)(url)
    assert response.status_code == 403
    assert response.json() == {"detail": {"message": "You don't have permission to do this."}}


def test_staff_can_view_admin_product_list(staff_client):
    assert staff_client.get("/api/v1/admin/products").status_code == 200


# ---------- Rate limiting ----------


def test_login_is_rate_limited(client, make_admin):
    make_admin()
    for _ in range(5):
        assert login(client, password="wrong password").status_code == 401
    blocked = login(client)  # even the right password is refused now
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["message"].startswith("Too many attempts")


# ---------- Uploads ----------

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def upload(client, data, name="photo.png"):
    return client.post("/api/v1/admin/uploads", files={"file": (name, data)})


def test_upload_and_download_a_photo(admin_client, client):
    response = upload(admin_client, PNG)
    assert response.status_code == 201
    url = response.json()["url"]
    assert url.startswith("/api/v1/uploads/") and url.endswith(".png")
    assert client.get(url).content == PNG  # anyone can view the photo


def test_upload_rejects_files_that_are_not_images(admin_client):
    # The name says .jpg, the content says otherwise
    assert upload(admin_client, b"MZ\x90\x00 an .exe file", name="photo.jpg").status_code == 415


def test_upload_rejects_big_files(admin_client):
    assert upload(admin_client, PNG + b"\x00" * (5 * 1024 * 1024)).status_code == 413
