import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from .db import get_slowest_endpoints, get_degradation, get_hourly_trend, get_error_rate_over_time
from .middleware import digest_map
from .llm import get_llm_summary

latency_router = APIRouter(prefix="/latency", tags=["latency"])

BASE_DIR = os.path.dirname(__file__)

def read_template(name):
    path = os.path.join(BASE_DIR, "templates", name)
    with open(path, "r") as f:
        return f.read()

def build_endpoint_data(endpoint, include_trends=False):
    key = (endpoint["method"], endpoint["endpoint"])

    if key in digest_map:
        sample_size = digest_map[key].n
        percentiles = {
            "p50_ms": round(digest_map[key].percentile(50), 2),
            "p95_ms": round(digest_map[key].percentile(95), 2),
            "p99_ms": round(digest_map[key].percentile(99), 2),
            "sample_size": sample_size,
            "percentiles_reliable": sample_size >= 100
        }
    else:
        percentiles = None

    degradation = get_degradation(endpoint["endpoint"], endpoint["method"])

    status = "ok"
    if degradation:
        if degradation["change_pct"] > 50:
            status = "degraded"
        elif degradation["change_pct"] > 20:
            status = "warning"

    result = {
        "endpoint": endpoint["endpoint"],
        "method": endpoint["method"],
        "avg_ms": round(endpoint["avg_ms"], 2),
        "total_requests": endpoint["total_requests"],
        "error_count": endpoint["error_count"],
        "status": status,
        "degradation": degradation,
        "percentiles": percentiles
    }

    if include_trends:
        result["hourly_trend"] = get_hourly_trend(endpoint["endpoint"], endpoint["method"])
        result["error_rate_over_time"] = get_error_rate_over_time(endpoint["endpoint"], endpoint["method"])

    return result


@latency_router.get("/health")
def health():
    slowest = get_slowest_endpoints()
    results = [build_endpoint_data(ep, include_trends=True) for ep in slowest]
    return {"endpoints": results}


@latency_router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(read_template("dashboard.html"))


@latency_router.get("/dashboard/detail", response_class=HTMLResponse)
def dashboard_detail():
    return HTMLResponse(read_template("detail.html"))

   
@latency_router.post("/summary")
async def summary():
    slowest = get_slowest_endpoints()
    results = [build_endpoint_data(ep, include_trends=False) for ep in slowest]
    try:
        text = await get_llm_summary(results)
        return {"summary": text}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
       return {"error": f"llm call failed: {str(e)}"}
