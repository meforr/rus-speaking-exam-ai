from backend.app.prompts.base import BASE_SYSTEM_PROMPT

MONOLOGUE_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + """
Критерии оценки задания 3 (Монологическое высказывание):
- Выполнение коммуникативной задачи (0-2 балла)
- Логичность и связность (0-2 балла)
- Речевое оформление и богатство словаря (0-2 балла)
Максимальный балл: 6 баллов.

ВАЖНО:
В объекте "criteria" указывай ТОЛЬКО название критерия и оценку через слэш (например "X / 2") БЕЗ текста комментариев!
Все замечания пиши исключительно в "feedback" предельно кратко (2-3 предложения).
"""

def get_monologue_text_prompt(task_content: str, student_answer: str, task_instructions: str = "") -> str:
    return f"""Задание: Подготовь монолог на заданную тему.

Тема: {task_content}

Инструкции: {task_instructions}

Ответ ученика (монолог):
{student_answer}

Оцени ответ. Верни ТОЛЬКО JSON с кратким feedback (2-3 предложения) и criteria без комментариев."""


def get_monologue_audio_prompt(task_content: str, task_instructions: str = "") -> str:
    return f"""Задание: Подготовь монолог на заданную тему.

Тема:
{task_content}

Инструкции:
{task_instructions}

Ниже прикреплена АУДИОЗАПИСЬ монолога ученика.
Оцени монолог. Верни ТОЛЬКО JSON с кратким feedback (2-3 предложения) и criteria без комментариев."""
