from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from backend.app.api.deps import get_task_repository, get_ai_evaluator
from backend.app.models.evaluation import ExamRequest, ExamResponse
from backend.app.services.task_repository import TaskRepository
from backend.app.services.ai_evaluator import AIEvaluator

router = APIRouter()


@router.post("/check", response_model=ExamResponse)
async def check_answer(
    request: ExamRequest,
    repo: TaskRepository = Depends(get_task_repository),
    ai_evaluator: AIEvaluator = Depends(get_ai_evaluator),
):
    """Проверить текстовый ответ ученика с помощью ИИ"""
    try:
        task = repo.get_task(request.task_type, request.task_id)
        result = await ai_evaluator.evaluate_text(
            task_type=request.task_type,
            student_answer=request.student_answer,
            task_content=task.content,
            task_instructions=task.instructions,
        )
        return ExamResponse(
            score=result["score"],
            max_score=result["max_score"],
            feedback=result["feedback"],
            criteria=result.get("criteria", {}),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при проверке: {str(e)}")


@router.post("/check-audio", response_model=ExamResponse)
async def check_answer_audio(
    task_type: str = Form(...),
    task_id: Optional[int] = Form(None),
    audio: UploadFile = File(...),
    repo: TaskRepository = Depends(get_task_repository),
    ai_evaluator: AIEvaluator = Depends(get_ai_evaluator),
):
    """Проверить аудиозапись ответа ученика с помощью ИИ"""
    try:
        task = repo.get_task(task_type, task_id)
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Пустой аудиофайл")

        audio_mime = audio.content_type or "audio/webm"

        result = await ai_evaluator.evaluate_audio(
            task_type=task_type,
            audio_bytes=audio_bytes,
            audio_mime=audio_mime,
            task_content=task.content,
            task_instructions=task.instructions,
        )

        return ExamResponse(
            score=result["score"],
            max_score=result["max_score"],
            feedback=result["feedback"],
            criteria=result.get("criteria", {}),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при проверке аудио: {str(e)}")
