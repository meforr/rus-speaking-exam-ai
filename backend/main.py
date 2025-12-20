from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv

from backend.ai_checker import AIChecker
from backend.exam_data import ExamData

# Загружаем переменные окружения (пробуем разные пути)
# ВАЖНО: Используем override=True и правильный порядок
# backend/conf.env имеет наивысший приоритет
load_dotenv("backend/conf.env", override=True)  # Самый приоритетный
load_dotenv("conf.env", override=True)  # Второй приоритет
load_dotenv(".env", override=True)  # Третий приоритет
load_dotenv(override=True)  # Стандартный .env в корне

app = FastAPI(title="Устное собеседование по русскому языку")

# CORS для локальной разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтирование статических файлов
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Инициализация компонентов
ai_checker = AIChecker()
exam_data = ExamData()


class ExamRequest(BaseModel):
    task_type: str  # "reading", "retelling", "monologue"
    student_answer: str
    task_id: Optional[int] = None


class ExamResponse(BaseModel):
    score: int
    max_score: int
    feedback: str
    criteria: dict


class TaskResponse(BaseModel):
    task_id: int
    task_type: str
    content: str
    instructions: str


@app.get("/")
async def root():
    """Главная страница"""
    return FileResponse("frontend/index.html")


@app.get("/style.css")
async def get_css():
    """CSS файл"""
    return FileResponse("frontend/style.css", media_type="text/css")


@app.get("/script.js")
async def get_js():
    """JavaScript файл"""
    return FileResponse("frontend/script.js", media_type="application/javascript")


@app.get("/api/tasks")
async def get_tasks():
    """Получить список доступных заданий"""
    return {
        "reading": exam_data.get_reading_tasks(),
        "retelling": exam_data.get_retelling_tasks(),
        "monologue": exam_data.get_monologue_tasks()
    }


@app.get("/api/task/{task_type}")
async def get_task(task_type: str, task_id: Optional[int] = None):
    """Получить конкретное задание"""
    try:
        task = exam_data.get_task(task_type, task_id)
        return TaskResponse(
            task_id=task["id"],
            task_type=task_type,
            content=task["content"],
            instructions=task["instructions"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/check", response_model=ExamResponse)
async def check_answer(request: ExamRequest):
    """Проверить ответ ученика с помощью ИИ"""
    try:
        # Получаем задание для контекста
        task = exam_data.get_task(request.task_type, request.task_id)
        
        # Проверяем ответ через ИИ
        result = await ai_checker.check_answer(
            task_type=request.task_type,
            student_answer=request.student_answer,
            task_content=task["content"],
            task_instructions=task["instructions"]
        )
        
        return ExamResponse(
            score=result["score"],
            max_score=result["max_score"],
            feedback=result["feedback"],
            criteria=result["criteria"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при проверке: {str(e)}")


@app.get("/api/health")
async def health():
    """Проверка работоспособности API"""
    return {"status": "ok", "ai_available": ai_checker.is_available(), "ai_provider": "Google Gemini"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", 8000)))

