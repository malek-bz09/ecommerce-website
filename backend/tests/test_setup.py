"""Phase 2: the app starts, reaches PostgreSQL, and answers errors in one shape."""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.core.errors import AppError
from app.main import app

# Extra routes, only for these tests, to trigger each kind of error
error_routes = APIRouter(prefix="/api/v1/_test")


class Thing(BaseModel):
    name: str
    price: int


@error_routes.post("/validate")
def validate(thing: Thing):
    return thing


@error_routes.get("/app-error")
def app_error():
    raise AppError(409, "Only 2 left in stock.", cartChanged=True)


@error_routes.get("/crash")
def crash():
    raise RuntimeError("secret internal details")


app.include_router(error_routes)


def test_health_reports_database_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_tests_use_the_test_database():
    assert get_settings().database_url.endswith("_test")


def test_migrations_ran():
    engine = create_engine(get_settings().database_url)
    assert "alembic_version" in inspect(engine).get_table_names()
    engine.dispose()


def test_unknown_url_is_404_in_our_shape(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": {"message": "Not Found"}}


def test_invalid_input_lists_each_bad_field(client):
    response = client.post("/api/v1/_test/validate", json={"price": "cheap"})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["message"] == "Please fix the highlighted fields."
    assert set(detail["fieldErrors"]) == {"name", "price"}


def test_app_error_keeps_extra_fields(client):
    response = client.get("/api/v1/_test/app-error")
    assert response.status_code == 409
    assert response.json() == {"detail": {"message": "Only 2 left in stock.", "cartChanged": True}}


def test_crash_hides_internal_details(client):
    response = client.get("/api/v1/_test/crash")
    assert response.status_code == 500
    assert "secret" not in response.text
    assert response.json()["detail"]["message"].startswith("Something went wrong")


def test_cors_allows_configured_origin_only(client):
    def preflight(origin):
        return client.options(
            "/api/v1/health",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )

    allowed = preflight("http://localhost:5173")
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in preflight("https://evil.example").headers
