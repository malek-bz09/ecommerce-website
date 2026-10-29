"""The connection to PostgreSQL."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

# The engine keeps a pool of open connections and hands them out as needed.
# pool_pre_ping checks a connection still works before using it (e.g. after a DB restart).
engine = create_engine(get_settings().database_url, pool_pre_ping=True)

# A session is one "unit of work": the queries and changes made while handling a request.
# expire_on_commit=False keeps loaded objects readable after commit, so a route can
# still return them.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
