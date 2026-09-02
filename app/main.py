import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import init_db, async_session_maker
from app.core.redis import RedisClient
from app.core.security import get_password_hash
from app.middlewares.cors import setup_cors
from app.middlewares.logging import RequestLoggingMiddleware
from app.middlewares.telegram_auth import TelegramAuthMiddleware
from app.api.v1.router import api_v1_router
from app.models.agent import Agent
from app.repositories.agent_repository import AgentRepository

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("app.main")


async def seed_initial_data():
    """Seed a default admin/support agent account if none exists."""
    async with async_session_maker() as session:
        agent_repo = AgentRepository(session)
        existing = await agent_repo.get_by_email("admin@support.com")
        if not existing:
            default_agent = Agent(
                email="admin@support.com",
                hashed_password=get_password_hash("AdminSecret123!"),
                full_name="Default Admin Agent",
                is_online=False,
            )
            await agent_repo.create(default_agent)
            logger.info("Seeded initial support agent: admin@support.com / AdminSecret123!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup database initialization and shutdown cleanup."""
    logger.info("Starting up FastAPI application...")
    os.makedirs("public/uploads", exist_ok=True)
    # Initialize DB tables asynchronously
    await init_db()
    await seed_initial_data()
    yield
    logger.info("Shutting down application...")
    await RedisClient.close()


def create_application() -> FastAPI:
    """Factory function for creating FastAPI application instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        version="1.0.0",
        lifespan=lifespan,
    )

    # Attach Middlewares
    setup_cors(app)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(TelegramAuthMiddleware)

    # Mount static uploads directory
    os.makedirs("public/uploads", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="public/uploads"), name="uploads")

    # Mount API Routers
    app.include_router(api_v1_router, prefix=settings.API_V1_STR)

    @app.get("/health", tags=["Health Check"])
    async def health_check():
        return {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
        }

    return app


app = create_application()
