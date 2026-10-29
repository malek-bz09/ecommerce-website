"""Test setup: every test run gets a brand-new, separate test database.

The test database URL comes from TEST_DATABASE_URL (environment or .env), never
from DATABASE_URL, so the tests can't touch development or production data.
"""

import os

from dotenv import dotenv_values

# This must happen before anything from `app` is imported: the app reads
# DATABASE_URL once at import time, and here it is pointed at the test database.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or dotenv_values(".env").get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("Set TEST_DATABASE_URL (see .env.example) before running the tests.")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
# A fixed signing key for test tokens, so tests don't depend on your .env
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-that-is-long-enough-1234"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, make_url, text  # noqa: E402

from app.core.rate_limit import RateLimiter  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.services.auth import save_admin  # noqa: E402


def recreate_test_database(url: str) -> None:
    db_name = make_url(url).database
    # Safety net: this function deletes the whole database
    if not db_name or not db_name.endswith("_test"):
        raise RuntimeError(f"Refusing to reset '{db_name}': the test database name must end in _test.")
    # CREATE/DROP DATABASE can't run inside a transaction, hence AUTOCOMMIT,
    # and they must run while connected to another database ("postgres")
    admin = create_engine(make_url(url).set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Runs once per test run: fresh database, then every migration, exactly like production."""
    recreate_test_database(TEST_DATABASE_URL)
    command.upgrade(alembic_config(), "head")
    yield


def alembic_config() -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL.replace("%", "%%"))
    return config


@pytest.fixture(autouse=True)
def empty_tables():
    """After each test, delete every row so the next test starts from an empty shop.

    (TRUNCATE rather than rolling back a transaction: later tests commit from
    several connections at once, to check two orders can't buy the same last item.)"""
    yield
    RateLimiter.reset()
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.exec_driver_sql(f"TRUNCATE {tables} RESTART IDENTITY CASCADE")


@pytest.fixture
def client():
    # raise_server_exceptions=False: a crash becomes a 500 response, as a browser would see it
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------- Signed-in clients ----------

PASSWORD = "correct horse battery staple"


@pytest.fixture
def make_admin():
    def make(email="boss@shop.dz", role="admin", name="Shop Boss"):
        with SessionLocal() as db:
            admin, _ = save_admin(db, email=email, full_name=name, password=PASSWORD, role=role)
            return admin

    return make


def signed_in_client(admin) -> TestClient:
    token, _ = create_access_token(admin.id, admin.role)
    return TestClient(app, raise_server_exceptions=False, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture
def admin_client(make_admin):
    with signed_in_client(make_admin()) as c:
        yield c


@pytest.fixture
def staff_client(make_admin):
    with signed_in_client(make_admin(email="staff@shop.dz", role="staff", name="Shop Staff")) as c:
        yield c
