from fastapi import APIRouter, Depends
from backend.app.api.deps import get_ai_evaluator
from backend.app.services.ai_evaluator import AIEvaluator

router = APIRouter()


@router.get("/health")
async def health(
    ai_evaluator: AIEvaluator = Depends(get_ai_evaluator),
):
    """Проверка работоспособности API и доступности Gemini AI"""
    return {
        "status": "ok",
        "ai_available": ai_evaluator.is_available(),
        "ai_provider": "Google Gemini",
    }
