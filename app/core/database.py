import re
from typing import AsyncGenerator
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Normalize Database URL for PostgreSQL (Railway / Supabase / Render / Docker)
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://") or db_url.startswith("postgresql://"):
    db_url = re.sub(r"^postgres(ql)?://", "postgresql+asyncpg://", db_url, count=1)
elif db_url.startswith("postgresql+") and not db_url.startswith("postgresql+asyncpg://"):
    db_url = re.sub(r"^postgresql\+[a-zA-Z0-9_]+://", "postgresql+asyncpg://", db_url, count=1)

# Connect args check for SQLite vs Postgres
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    db_url,
    echo=settings.DEBUG,
    future=True,
    connect_args=connect_args
)

# Async Session Factory
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def init_db() -> None:
    """Initialize database tables asynchronously."""
    # Ensure all models are imported so SQLModel.metadata is populated
    import app.models  # noqa: F401

    # 1. Create all missing tables in their own transaction
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # 2. Ensure new columns exist on agents and messages tables for legacy DB migrations
    async with engine.begin() as conn:
        from sqlalchemy import text
        is_sqlite = db_url.startswith("sqlite")

        for col_name in ["telegram_chat_id", "telegram_username"]:
            try:
                sql = f"ALTER TABLE agents ADD COLUMN {col_name} VARCHAR(255)" if is_sqlite else f"ALTER TABLE agents ADD COLUMN IF NOT EXISTS {col_name} VARCHAR(255)"
                await conn.execute(text(sql))
            except Exception:
                pass  # Column already exists or dialect error

        for col_name, col_type in [("media_url", "TEXT"), ("media_type", "VARCHAR(255)")]:
            try:
                sql = f"ALTER TABLE messages ADD COLUMN {col_name} {col_type}" if is_sqlite else f"ALTER TABLE messages ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                await conn.execute(text(sql))
            except Exception:
                pass  # Column already exists or dialect error

    # 3. Ensure telegram_id and sender_id are BIGINT to support 64-bit Telegram IDs
    async with engine.begin() as conn:
        from sqlalchemy import text
        try:
            await conn.execute(text("ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT"))
        except Exception:
            pass
        try:
            await conn.execute(text("ALTER TABLE messages ALTER COLUMN sender_id TYPE BIGINT"))
        except Exception:
            pass


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing AsyncSession to endpoints & repositories."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
