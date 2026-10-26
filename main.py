import os
import time
import uuid
import socket
import redis
from fastapi import FastAPI, Request, Response, HTTPException

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

INSTANCE_ID = socket.gethostname()

# --- Tier configuration: (limit, window_seconds) ---
TIERS = {
    "free":    (5, 60),
    "pro":     (100, 60),
    "unknown": (3, 60),
}

API_KEYS = {
    "demo-free-key": "free",
    "demo-pro-key":  "pro",
}

with open("rate_limiter.lua") as f:
    rate_limit_script = r.register_script(f.read())


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def identify(request: Request):
    api_key = request.headers.get("X-API-Key")
    if api_key and api_key in API_KEYS:
        return f"key:{api_key}", API_KEYS[api_key]
    return f"ip:{get_client_ip(request)}", "unknown"


@app.get("/")
def read_root(request: Request, response: Response):
    identity, tier = identify(request)
    limit, window = TIERS[tier]
    key = f"rate_limit:{identity}"

    now = time.time()
    member = f"{now}:{uuid.uuid4()}"

    allowed, remaining = rate_limit_script(
        keys=[key],
        args=[now, window, limit, member],
    )

    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for tier '{tier}'. Limit is {limit} per {window}s.",
            headers={"Retry-After": str(window), "X-RateLimit-Limit": str(limit)},
        )

    return {
        "message": "Request allowed!",
        "served_by": INSTANCE_ID,
        "tier": tier,
        "remaining": remaining,
    }
