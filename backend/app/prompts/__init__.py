from backend.app.prompts.base import BASE_SYSTEM_PROMPT
from backend.app.prompts.reading import (
    READING_SYSTEM_PROMPT,
    get_reading_text_prompt,
    get_reading_audio_prompt,
)
from backend.app.prompts.retelling import (
    RETELLING_SYSTEM_PROMPT,
    get_retelling_text_prompt,
    get_retelling_audio_prompt,
)
from backend.app.prompts.monologue import (
    MONOLOGUE_SYSTEM_PROMPT,
    get_monologue_text_prompt,
    get_monologue_audio_prompt,
)

SYSTEM_PROMPTS = {
    "reading": READING_SYSTEM_PROMPT,
    "retelling": RETELLING_SYSTEM_PROMPT,
    "monologue": MONOLOGUE_SYSTEM_PROMPT,
}


def get_system_prompt(task_type: str) -> str:
    return SYSTEM_PROMPTS.get(task_type.lower(), BASE_SYSTEM_PROMPT)


def get_user_prompt(
    task_type: str, student_answer: str, task_content: str, task_instructions: str = ""
) -> str:
    tt = task_type.lower()
    if tt == "reading":
        return get_reading_text_prompt(task_content, student_answer, task_instructions)
    elif tt == "retelling":
        return get_retelling_text_prompt(task_content, student_answer, task_instructions)
    elif tt == "monologue":
        return get_monologue_text_prompt(task_content, student_answer, task_instructions)
    return f"Задание: {task_content}\n\nИнструкции: {task_instructions}\n\nОтвет: {student_answer}"


def get_audio_user_prompt(
    task_type: str, task_content: str, task_instructions: str = ""
) -> str:
    tt = task_type.lower()
    if tt == "reading":
        return get_reading_audio_prompt(task_content, task_instructions)
    elif tt == "retelling":
        return get_retelling_audio_prompt(task_content, task_instructions)
    elif tt == "monologue":
        return get_monologue_audio_prompt(task_content, task_instructions)
    return f"""Задание: {task_content}\n\nИнструкции: {task_instructions}\n\nНиже прикреплена АУДИОЗАПИСЬ ответа ученика. Оцени её и верни JSON."""
