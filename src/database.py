# Phase 3 - database.py
# Engine + session factory + table init

import os
import re

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from models import Base

load_dotenv()

# ---------------------------------------------------------------------------
# Build connection URL
# Supports both:
#   - Single DATABASE_URL (Neon / any hosted Postgres)
#   - Individual vars for local Postgres
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fall back to individual vars for local development
    host     = os.getenv("DATABASE_HOSTNAME", "localhost")
    port     = os.getenv("DATABASE_PORT", "5432")
    user     = os.getenv("DATABASE_USERNAME", "postgres")
    password = os.getenv("DATABASE_PASSWORD", "")
    name     = os.getenv("DATABASE_NAME", "")
    DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"

# Neon (and some other providers) give a postgres:// or postgresql:// URL —
# swap the scheme so asyncpg is used
DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")

# asyncpg doesn't understand sslmode= or channel_binding= in the query string.
# Strip them out and pass ssl directly via connect_args instead.
is_ssl = "neon.tech" in DATABASE_URL or "sslmode" in DATABASE_URL
DATABASE_URL = re.sub(r"[?&]sslmode=[^&]*", "", DATABASE_URL)
DATABASE_URL = re.sub(r"[?&]channel_binding=[^&]*", "", DATABASE_URL)

connect_args = {"ssl": "require"} if is_ssl else {}

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=connect_args)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Dependency — yields a DB session per request
# ---------------------------------------------------------------------------

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


# ---------------------------------------------------------------------------
# Table creation (called once on startup)
# ---------------------------------------------------------------------------

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables ready.")
