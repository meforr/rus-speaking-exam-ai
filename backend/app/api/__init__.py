from fastapi import APIRouter
from backend.app.api.routes.tasks import router as tasks_router
from backend.app.api.routes.evaluate import router as evaluate_router
from backend.app.api.routes.health import router as health_router

api_router = APIRouter(prefix="/api")
api_router.include_router(tasks_router, tags=["tasks"])
api_router.include_router(evaluate_router, tags=["evaluation"])
api_router.include_router(health_router, tags=["health"])

__all__ = ["api_router"]
