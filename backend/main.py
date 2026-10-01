"""
Фасад для обратной совместимости.
Экспортирует приложение `app` из модульного пакета `backend.app.main`.
"""
import os
import uvicorn
from backend.app.main import app
from backend.app.core.config import settings

# Обратная совместимость для устаревших импортов
from backend.ai_checker import AIChecker
from backend.exam_data import ExamData

__all__ = ["app", "AIChecker", "ExamData"]

if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)
