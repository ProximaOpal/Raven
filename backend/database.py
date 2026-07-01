"""
NEXUS CCTV — Database Engine & Session Factory
Supports SQLite (dev) and PostgreSQL (prod) via DATABASE_URL.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.config import get_settings

settings = get_settings()

# SQLite needs check_same_thread=False; handled automatically by aiosqlite
connect_args = {}
if "sqlite" in settings.database_url:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables on startup (dev mode)."""
    async with engine.begin() as conn:
        # Import models so Base knows about them
        from backend import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
