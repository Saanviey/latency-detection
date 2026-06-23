import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from .db import insert_request

class LatencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        # normalized path for handling path params
        route = request.scope.get("route")
        endpoint = route.path if route else request.url.path
        method = request.method

        insert_request(
            endpoint=endpoint,
            method=method,
            status_code=response.status_code,
            response_time_ms=duration_ms
        )

        return response