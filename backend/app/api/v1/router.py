from fastapi import APIRouter

from app.api.v1 import (
    a2a,
    agents,
    analytics,
    approvals,
    auth,
    health,
    inventory,
    merchants,
    orders,
    recommendations,
    voice,
    websocket,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(merchants.router)
api_router.include_router(inventory.router)
api_router.include_router(recommendations.router)
api_router.include_router(agents.router)
api_router.include_router(a2a.router)
api_router.include_router(analytics.router)
api_router.include_router(approvals.router)
api_router.include_router(orders.router)
api_router.include_router(voice.router)
api_router.include_router(websocket.router)
