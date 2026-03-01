"""Health and readiness endpoints for orchestration probes."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from db import get_connection

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Liveness probe - returns 200 if the process is running."""
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    """Readiness probe - returns 200 if DB is reachable, 503 otherwise."""
    try:
        conn = get_connection()
        await conn.execute("SELECT 1")
        return {"status": "ok"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "detail": "Database unreachable"},
        )
