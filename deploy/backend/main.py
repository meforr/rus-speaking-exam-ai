from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv

from backend.ai_checker import AIChecker
from backend.exam_data import ExamData

load_dotenv("backend/conf.env", override=True)
load_dotenv("conf.env", override=True)
load_dotenv(".env", override=True)
load_dotenv(override=True)

app = FastAPI(title="Устное собеседование по русскому языку")


@app.middleware("http")
async def log_requests(request, call_next):
    """Логирование всех HTTP-запросов"""
    import time
    import json

    start = time.time()
    response = await call_next(request)
    duration_ms = int((start - time.time()) * -1000)

    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_path = os.path.join(base_dir, ".debugs", "debug.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        log_entry = {
            "id": f"log_{int(time.time() * 1000)}",
            "timestamp": int(time.time() * 1000),
            "location": "backend/main.py:log_requests",
            "message": "http_request",
            "data": {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
            "runId": "fix3",
            "hypothesisId": "H6",
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

ai_checker = AIChecker()
exam_data = ExamData()


class ExamRequest(BaseModel):
    task_type: str
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
        task = exam_data.get_task(request.task_type, request.task_id)
        
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


@app.post("/api/check-audio", response_model=ExamResponse)
async def check_answer_audio(
    task_type: str = Form(...),
    task_id: Optional[int] = Form(None),
    audio: UploadFile = File(...),
):
    """Проверить ответ ученика по аудиозаписи с помощью ИИ"""
    try:
        task = exam_data.get_task(task_type, task_id)

        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Пустой аудиофайл")

        audio_mime = audio.content_type or "audio/webm"

        result = await ai_checker.check_answer_audio(
            task_type=task_type,
            audio_bytes=audio_bytes,
            audio_mime=audio_mime,
            task_content=task["content"],
            task_instructions=task["instructions"],
        )

        return ExamResponse(
            score=result["score"],
            max_score=result["max_score"],
            feedback=result["feedback"],
            criteria=result["criteria"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при проверке аудио: {str(e)}")


@app.get("/api/health")
async def health():
    """Проверка работоспособности API"""
    # region agent log
    try:
        import json, time
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_path = os.path.join(base_dir, ".debugs", "debug.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        log_entry = {
            "id": f"log_{int(time.time() * 1000)}",
            "timestamp": int(time.time() * 1000),
            "location": "backend/main.py:131",
            "message": "health_endpoint_called",
            "data": {
                "ai_available": ai_checker.is_available(),
            },
            "runId": "fix2",
            "hypothesisId": "H5",
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # endregion agent log

    return {"status": "ok", "ai_available": ai_checker.is_available(), "ai_provider": "Google Gemini"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8000)))

