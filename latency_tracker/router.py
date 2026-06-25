from fastapi import APIRouter
from .db import get_slowest_endpoints, get_degradation
from .middleware import digest_map

latency_router = APIRouter(prefix="/latency", tags=["latency"])

@latency_router.get("/health")
def health():
    slowest = get_slowest_endpoints()
    
    results = []
    for endpoint in slowest: #iterate over slowest endpoints and form tuple key 

        key =(endpoint["method"], endpoint["endpoint"])
        if key in digest_map:
            percentiles = {
            "p50_ms": round(digest_map[key].percentile(50), 2),
            "p95_ms": round(digest_map[key].percentile(95), 2),
            "p99_ms": round(digest_map[key].percentile(99), 2)
    }
        else:
            percentiles = None
        
        # get degradation = baseline avg-recent avg %
        degradation = get_degradation(endpoint["endpoint"], endpoint["method"])
        
        status = "ok"
        if degradation:
            if degradation["change_pct"] >50:
                status = "degraded"
            elif degradation["change_pct"] >20:
                status = "warning"

        results.append({
            "endpoint": endpoint["endpoint"],
            "method": endpoint["method"],
            "avg_ms": round(endpoint["avg_ms"], 2),
            "total_requests": endpoint["total_requests"],
            "error_count": endpoint["error_count"],
            "status": status,
            "degradation": degradation,
            "percentiles":percentiles
        })
    
    return {"endpoints": results}