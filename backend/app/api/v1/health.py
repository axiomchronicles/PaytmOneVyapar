from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict:
    redis_status = "disabled"
    manager = getattr(request.app.state, "redis", None)
    if manager:
        try:
            redis_status = "ok" if await manager.health() else "degraded"
        except Exception:
            redis_status = "degraded"
    return {"status": "ok", "service": "vyapaar-commander", "redis": redis_status}
