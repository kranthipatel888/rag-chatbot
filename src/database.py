# database.py
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
    host     = os.getenv("DATABASE_HOSTNAME", "localhost")
    port     = os.getenv("DATABASE_PORT", "5432")
    user     = os.getenv("DATABASE_USERNAME", "postgres")
    password = os.getenv("DATABASE_PASSWORD", "")
    name     = os.getenv("DATABASE_NAME", "")
    DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"

# Swap scheme for asyncpg
DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")

# Strip sslmode/channel_binding — asyncpg doesn't accept them in the URL
is_ssl = "neon.tech" in DATABASE_URL or "sslmode" in DATABASE_URL
DATABASE_URL = re.sub(r"[?&]sslmode=[^&]*", "", DATABASE_URL)
DATABASE_URL = re.sub(r"[?&]channel_binding=[^&]*", "", DATABASE_URL)

connect_args = {"ssl": "require"} if is_ssl else {}

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    # Neon closes idle connections after ~5 minutes.
    # pool_pre_ping tests the connection before use and reconnects if dead.
    pool_pre_ping=True,
    # Recycle connections every 5 minutes to stay ahead of Neon's idle timeout.
    pool_recycle=300,
    # Keep a small pool — Neon free tier has a 10-connection limit.
    pool_size=5,
    max_overflow=2,
)

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
