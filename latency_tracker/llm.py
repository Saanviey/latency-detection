#making the actual api request body 
#needs --
# base_url — to know where to POST
# api_key — for the auth header
# model — for the request body
# messages — built inside llm.py itself from the endpoints data passed in
#passing the endpoint data as string instead of pure json leading to reduced overhaed for llm in parsing json 

import httpx
from .config import llm_config

#json -> string
def _format_endpoints(endpoints):
    lines = []
    for ep in endpoints:
        p = ep.get("percentiles")
        d = ep.get("degradation")

        p50 = f"{p['p50_ms']}ms" if p else "—"
        p95 = f"{p['p95_ms']}ms" if p else "—"
        p99 = f"{p['p99_ms']}ms" if p else "—"
        change = f"{d['change_pct']:+.1f}%" if d else "no trend data"
        reliable = "percentiles unreliable (low sample size)" if p and not p["percentiles_reliable"] else ""

        line = (
            f"{ep['method']} {ep['endpoint']} — "
            f"avg: {ep['avg_ms']}ms, p50: {p50}, p95: {p95}, p99: {p99}, "
            f"change: {change}, errors: {ep['error_count']}, status: {ep['status']}"
        )
        if reliable:
            line += f" [{reliable}]"
        lines.append(line)

    return "\n".join(lines)



async def get_llm_summary(endpoints):
    if not llm_config["api_key"] or not llm_config["base_url"]:
        raise ValueError(
            "llm not configured. call configure_llm(provider, api_key) before using the dashboard summary."
        )

    formatted = _format_endpoints(endpoints)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a backend performance analyst. "
                "Given latency metrics for API endpoints, identify which endpoints are concerning. "
                "A large gap between p50 and p99 means occasional spikes, not consistent slowness. "
                "A high change_pct means recent degradation. Use this to distinguish spike vs consistent issues. "
                "Only flag endpoints with status warning or degraded. Don't comment on healthy endpoints. "
                "Suggest possible causes from: slow db queries, missing indexes, connection pool exhaustion, "
                "memory pressure, N+1 queries, cache misses, or infra throttling. "
                "Respond in 3 parts: one line overall system health, per-endpoint issues for flagged ones only, "
                "then possible causes. Keep the entire response under 120 words. Be specific and technical, no fluff."
            )
        },
        {
            "role": "user",
            "content": f"Here is the current latency data for my API endpoints:\n\n{formatted}"
        }
    ]
   

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{llm_config['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {llm_config['api_key']}",
                "Content-Type": "application/json"
            },
            json={
                "model": llm_config["model"],
                "messages": messages,
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()