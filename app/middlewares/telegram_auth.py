import logging
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse
from app.core.config import settings

logger = logging.getLogger("telegram.auth")


class TelegramAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware verifying X-Telegram-Bot-Api-Secret-Token on incoming webhook calls.
    Protects the telegram webhook route from unauthorized external requests.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        webhook_path = f"{settings.API_V1_STR}/telegram/webhook"
        
        if request.url.path == webhook_path and request.method == "POST":
            secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            expected_secret = settings.TELEGRAM_WEBHOOK_SECRET
            
            # If a webhook secret is set in config and does not match incoming header
            if expected_secret and expected_secret != "dev_secret_token":
                if secret_token != expected_secret:
                    logger.warning("Unauthorized webhook request: secret token mismatch.")
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Invalid Telegram secret token header."}
                    )

        return await call_next(request)
