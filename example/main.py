from fastapi import FastAPI
from latency_tracker import LatencyMiddleware, latency_router, init_db
import asyncio 
import random

app = FastAPI()

init_db()  # creates the SQLite table on startup
app.add_middleware(LatencyMiddleware)
app.include_router(latency_router)

# some dummy endpoints to generate traffic
@app.get("/posts")
async def get_posts():
    return {"posts": ["post1", "post2"]}

@app.get("/posts/{id}")
async def get_post(id: int):
    return {"post": id}

@app.post("/comments")
async def create_comment():
    return {"comment": "created"}

@app.get("/slow")
async def slow_endpoint():
    await asyncio.sleep(random.uniform(0.1, 1.0)) 
    return {"status": "done"}