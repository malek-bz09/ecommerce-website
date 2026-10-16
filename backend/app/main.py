"""Entry point. Run with: uv run uvicorn app.main:app --reload"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import admin, products, store
from .database import UPLOAD_DIR, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create/upgrade tables and first-run data before serving requests
    yield


app = FastAPI(title="UNDERGROUND API", lifespan=lifespan)
app.include_router(store.router)
app.include_router(products.router)
app.include_router(products.admin_router)
app.include_router(admin.router)

# Product photos uploaded from the admin
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
