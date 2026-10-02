from functools import lru_cache
from backend.app.services.task_repository import TaskRepository
from backend.app.services.ai_evaluator import AIEvaluator


@lru_cache()
def get_task_repository() -> TaskRepository:
    return TaskRepository()


@lru_cache()
def get_ai_evaluator() -> AIEvaluator:
    return AIEvaluator()
