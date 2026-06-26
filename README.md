# latency_tracker

python middleware library for FastAPI that tracks API endpoint latency with statistical percentiles, time-based degradation detection, a built-in dashboard, and an optional LLM summary layer.

---

## features

- **t-digest percentiles** — p50, p95, p99 computed in memory, persisted across restarts
- **time-windowed degradation** — recent 10min avg vs 24h baseline, not just absolute latency
- **hourly bucketing** — shows *when* degradation started, not just that it exists
- **distribution shape** — p50→p99 spread distinguishes spiky vs consistently slow endpoints
- **error rate tracking** — 5xx rate per hour, correlated with latency data
- **sample size warnings** — percentiles flagged unreliable below 100 samples
- **HTML dashboard** — sortable table, per-endpoint drill-down with charts, auto-refreshes
- **LLM summary** — on-demand diagnosis via Groq, OpenAI, or Gemini. optional.

---

## architecture

```
request → LatencyMiddleware → TDigest (memory) + SQLite (raw rows)
                                      ↓
/latency/health     → percentiles from tdigest + degradation/trend from SQL
/latency/dashboard  → static HTML, fetches /health client-side, chart.js renders
/latency/summary    → formats health data as text → LLM provider → plain english diagnosis
```

---

## quickstart

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from latency_tracker import LatencyMiddleware, latency_router, init_db, startup, shutdown, configure_llm

load_dotenv()
configure_llm("groq", os.getenv("GROQ_API_KEY"))  # optional

@asynccontextmanager
async def lifespan(app):
    startup()
    yield
    shutdown()

app = FastAPI(lifespan=lifespan)
init_db()
app.add_middleware(LatencyMiddleware)
app.include_router(latency_router)
```

visit `http://localhost:8000/latency/dashboard`.

---

## supported providers

`groq` · `openai` · `gemini`

LLM summary is optional — all statistical features work without it.
