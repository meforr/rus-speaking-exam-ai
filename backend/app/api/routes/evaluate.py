import re
from dataclasses import asdict
from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from backend.app.api.deps import get_task_repository, get_ai_evaluator, get_dsp_analyzer
from backend.app.models.evaluation import ExamRequest, ExamResponse, DSPMetricsModel
from backend.app.services.task_repository import TaskRepository
from backend.app.services.ai_evaluator import AIEvaluator
from backend.app.services.dsp_analyzer import DSPAnalyzer

router = APIRouter()

MAX_CRITERIA_MAP = {
    "reading": {
        "интонация и выразительность": 2,
        "орфоэпия": 2,
        "темп чтения": 1,
    },
    "retelling": {
        "сохранение микротем": 2,
        "соблюдение фактологической точности": 1,
        "работа с цитатой": 2,
        "речевые нормы": 1,
        "речевые и грамматические нормы": 1,
    },
    "monologue": {
        "выполнение коммуникативной задачи": 2,
        "логичность и связность": 2,
        "речевое оформление и богатство словаря": 2,
        "речевое оформление": 2,
    },
}


def clean_criteria_dict(raw_criteria: Dict, task_type: str, dsp_tempo_score: Optional[int] = None) -> Dict[str, str]:
    """Очищает критерии: оставляет ТОЛЬКО название и оценку, убирает комментарии, заменяет формулировки."""
    cleaned = {}
    norm_type = task_type.lower()
    type_limits = MAX_CRITERIA_MAP.get(norm_type, {})

    for raw_k, raw_v in raw_criteria.items():
        if not raw_k or raw_k.lower() == "note":
            continue

        # Убираем любые упоминания DSP и членения
        if "dsp" in raw_k.lower() or "интонационное членение" in raw_k.lower():
            continue

        # Замена "Правильность произношения / Орфоэпия" -> "Орфоэпия"
        k = raw_k.strip()
        if re.search(r"правильность произношения\s*/\s*орфоэпия", k, re.IGNORECASE) or k.lower() == "произношение / орфоэпия":
            k = "Орфоэпия"
        elif "орфоэпия" in k.lower():
            k = "Орфоэпия"

        # Извлечение чистого числового балла без комментариев
        val_str = str(raw_v).strip()
        score_val = 0
        match = re.search(r"\b(\d+)\b", val_str)
        if match:
            score_val = int(match.group(1))

        # Определение максимума для критерия
        max_val = None
        for known_k, m in type_limits.items():
            if known_k in k.lower():
                max_val = m
                break

        if max_val is not None:
            score_val = min(score_val, max_val)
            cleaned[k] = f"{score_val} / {max_val}"
        else:
            cleaned[k] = f"{score_val}"

    # Для задания 1 (чтение) фиксируем официальный список критериев и объективный темп
    if norm_type == "reading":
        ordered = {}
        int_score = 0
        for k, v in cleaned.items():
            if "интонация" in k.lower():
                int_score = int(v.split('/')[0].strip())
                break
        ordered["Интонация и выразительность"] = f"{int_score} / 2"

        ortho_score = 0
        for k, v in cleaned.items():
            if "орфоэпия" in k.lower():
                ortho_score = int(v.split('/')[0].strip())
                break
        ordered["Орфоэпия"] = f"{ortho_score} / 2"

        tempo_val = dsp_tempo_score if dsp_tempo_score is not None else 1
        ordered["Темп чтения"] = f"{tempo_val} / 1"
        return ordered

    return cleaned


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
        clean_criteria = clean_criteria_dict(
            result.get("criteria", {}),
            task_type=request.task_type,
        )
        return ExamResponse(
            score=result["score"],
            max_score=result["max_score"],
            feedback=result["feedback"],
            criteria=clean_criteria,
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
    dsp_analyzer: DSPAnalyzer = Depends(get_dsp_analyzer),
):
    """Проверить аудиозапись ответа ученика через гибридный пайплайн (DSP + Gemini AI)"""
    try:
        task = repo.get_task(task_type, task_id)
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Пустой аудиофайл")

        audio_mime = audio.content_type or "audio/webm"

        # 1. Акустический анализ (DSP, Silero VAD, WPM, Pitch, Орфоэпия)
        dsp_result = dsp_analyzer.analyze(
            audio_bytes=audio_bytes,
            task_content=task.content,
            mime_type=audio_mime,
        )

        # 2. Семантическая оценка через мультимодальный Gemini AI
        ai_result = await ai_evaluator.evaluate_audio(
            task_type=task_type,
            audio_bytes=audio_bytes,
            audio_mime=audio_mime,
            task_content=task.content,
            task_instructions=task.instructions,
        )

        # 3. Чистые критерии оценки без комментариев и нейрослопа
        clean_criteria = clean_criteria_dict(
            ai_result.get("criteria", {}),
            task_type=task_type,
            dsp_tempo_score=dsp_result.tempo_score if task_type.lower() == "reading" else None,
        )

        final_score = ai_result["score"]
        final_max = ai_result["max_score"]
        if task_type.lower() == "reading":
            final_score = sum(int(v.split('/')[0].strip()) for v in clean_criteria.values())
            final_max = 5

        dsp_model = DSPMetricsModel(**asdict(dsp_result))

        return ExamResponse(
            score=final_score,
            max_score=final_max,
            feedback=ai_result["feedback"],
            criteria=clean_criteria,
            dsp=dsp_model,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при проверке аудио: {str(e)}")

