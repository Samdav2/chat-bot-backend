import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger("api.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging incoming requests and recording execution times."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        process_time = (time.time() - start_time) * 1000
        formatted_process_time = f"{process_time:.2f}ms"
        
        response.headers["X-Process-Time"] = formatted_process_time
        
        logger.info(
            f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {formatted_process_time}"
        )
        
        return response
