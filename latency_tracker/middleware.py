import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from .db import insert_request
from tdigest import TDigest


class LatencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        #before request hits the route 
        start = time.time()
        #request hits +processing (via call_next)
        response = await call_next(request)
        #after
        duration_ms = (time.time() - start) * 1000

        # normalized path for handling path params
        route = request.scope.get("route")
        endpoint = route.path if route else request.url.path
        method = request.method
        
        #dict key --> tdigest() object for that key=(method , endpoint)
        key = (method, endpoint)
        if key not in digest_map: #check if tdigest obj already exists 
            digest_map[key] = TDigest()
        digest_map[key].update(duration_ms) #update existing tdigest centriods with current response time

        insert_request(
            endpoint=endpoint,
            method=method,
            status_code=response.status_code,
            response_time_ms=duration_ms
        )

        return response
    
#for in memory tdigest (fetching db at every calculation is expensive)
digest_map ={}
