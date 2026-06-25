import asyncio
import httpx
import random

BASE_URL = "http://localhost:8000"

ENDPOINTS = [
    ("GET", "/posts"),
    ("GET", "/posts/1"),
    ("GET", "/posts/2"),
    ("GET", "/posts/5"),
    ("POST", "/comments"),
    ("GET", "/slow"),
]

async def hit(client, method, path):
    try:
        if method == "GET":
            await client.get(f"{BASE_URL}{path}")
        elif method == "POST":
            await client.post(f"{BASE_URL}{path}")
    except Exception as e:
        print(f"failed: {method} {path} — {e}")

async def run_wave(n_requests=200):
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = []
        for _ in range(n_requests):
            method, path = random.choice(ENDPOINTS)
            # weight /slow heavier so it accumulates enough samples
            if random.random() < 0.3:
                method, path = "GET", "/slow"
            tasks.append(hit(client, method, path))
        await asyncio.gather(*tasks)

async def main():
    print("wave 1 — baseline traffic (300 requests)...")
    await run_wave(300)
    print("done. waiting 5s...")
    await asyncio.sleep(5)

    print("wave 2 — more traffic (300 requests)...")
    await run_wave(300)
    print("done.")

    print("\nall done. hit /latency/dashboard to see results.")

if __name__ == "__main__":
    asyncio.run(main())