from backend.app.prompts.base import BASE_SYSTEM_PROMPT

RETELLING_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + """
Критерии оценки задания 2 (Пересказ текста с включением высказывания):
- Сохранение микротем (0-2 балла)
- Соблюдение фактологической точности (0-1 балл)
- Работа с цитатой (0-2 балла)
- Речевые нормы (0-1 балл)
Максимальный балл: 6 баллов.

ВАЖНО:
В объекте "criteria" указывай ТОЛЬКО название критерия и оценку через слэш (например "X / 2" или "X / 1") БЕЗ текста комментариев!
Все замечания пиши исключительно в "feedback" предельно кратко (2-3 предложения).
"""

def get_retelling_text_prompt(task_content: str, student_answer: str, task_instructions: str = "") -> str:
    return f"""Задание: Перескажи текст, включив в пересказ высказывание.

Исходный текст:
{task_content}

Инструкции: {task_instructions}

Ответ ученика (пересказ):
{student_answer}

Оцени пересказ. Верни ТОЛЬКО JSON с кратким feedback (2-3 предложения) и criteria без комментариев."""


def get_retelling_audio_prompt(task_content: str, task_instructions: str = "") -> str:
    return f"""Задание: Перескажи текст, включив в пересказ указанное высказывание.

Исходный текст:
{task_content}

Инструкции:
{task_instructions}

Ниже прикреплена АУДИОЗАПИСЬ пересказа ученика.
Оцени содержание и устную речь. Верни ТОЛЬКО JSON с кратким feedback (2-3 предложения) и criteria без комментариев."""
