import json
import logging
from typing import Dict, Any, Optional

from google import genai
from google.genai import types

from backend.app.core.config import settings
from backend.app.prompts import (
    get_system_prompt,
    get_user_prompt,
    get_audio_user_prompt,
)

logger = logging.getLogger("ai_evaluator")


class AIEvaluator:
    """Сервис проверки устных ответов через Google Gemini API с fallback-режимом"""

    def __init__(self):
        self.client: Optional[genai.Client] = None
        self.model_name: str = settings.gemini_model
        self.available: bool = False
        self._init_client()

    def _init_client(self):
        api_key = settings.gemini_api_key
        if not api_key:
            logger.info("GEMINI_API_KEY не установлен. Работает режим мок-проверки.")
            self.available = False
            return

        api_key_clean = api_key.strip()
        if len(api_key_clean) < 20:
            logger.warning(f"GEMINI_API_KEY некорректен (длина {len(api_key_clean)} < 20).")
            self.available = False
            return

        try:
            self.client = genai.Client(api_key=api_key_clean)
            self.available = True
            logger.info(f"Google Gemini клиент успешно инициализирован. Модель: {self.model_name}")
        except Exception as e:
            logger.error(f"Ошибка при инициализации Gemini Client: {e}")
            self.client = None
            self.available = False

    def is_available(self) -> bool:
        return self.available

    async def evaluate_text(
        self,
        task_type: str,
        student_answer: str,
        task_content: str,
        task_instructions: str = "",
    ) -> Dict[str, Any]:
        """Оценка текстового ответа (транскрипции)"""
        if not self.available:
            return self._mock_evaluate(task_type, student_answer)

        system_prompt = get_system_prompt(task_type)
        user_prompt = get_user_prompt(task_type, student_answer, task_content, task_instructions)
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        try:
            generation_config = {
                "temperature": 0.2,
                "response_mime_type": "application/json",
            }

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=generation_config,
            )

            self._log_tokens(response)
            return self._parse_json_response(response.text, task_type, student_answer)

        except Exception as e:
            return self._handle_gemini_error(e, task_type, student_answer)

    async def evaluate_audio(
        self,
        task_type: str,
        audio_bytes: bytes,
        audio_mime: str,
        task_content: str,
        task_instructions: str = "",
    ) -> Dict[str, Any]:
        """Оценка аудиозаписи ответа"""
        if not self.available:
            return self._mock_evaluate(task_type, "audio_answer")

        system_prompt = get_system_prompt(task_type)
        user_prompt = get_audio_user_prompt(task_type, task_content, task_instructions)

        normalized_mime = (audio_mime or "audio/webm").split(";")[0].strip().lower()
        if normalized_mime.startswith("audio/webm"):
            normalized_mime = "audio/webm"

        try:
            contents = [
                system_prompt,
                user_prompt,
                types.Part.from_bytes(data=audio_bytes, mime_type=normalized_mime),
            ]
            generation_config = {
                "temperature": 0.2,
                "response_mime_type": "application/json",
            }

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=generation_config,
            )

            self._log_tokens(response, is_audio=True)
            return self._parse_json_response(response.text, task_type, "audio_answer")

        except Exception as e:
            return self._handle_gemini_error(e, task_type, "audio_answer")

    def _parse_json_response(self, text: str, task_type: str, fallback_text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            if "score" in data and "max_score" in data:
                return data
        except json.JSONDecodeError as e:
            logger.warning(f"Ошибка парсинга JSON ответа Gemini: {e}")

        result = self._mock_evaluate(task_type, fallback_text)
        result["feedback"] = f"ИИ сформировал ответ в нестандартном формате: {cleaned[:300]}"
        return result

    def _handle_gemini_error(self, e: Exception, task_type: str, fallback_text: str) -> Dict[str, Any]:
        error_str = str(e)
        logger.error(f"Ошибка обращения к Gemini API: {error_str}")

        result = self._mock_evaluate(task_type, fallback_text)
        if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
            result["feedback"] = "Превышен лимит запросов к Gemini API (15 запросов в минуту). Подождите полминуты и повторите попытку."
        elif "Server disconnected" in error_str or "connection" in error_str.lower():
            result["feedback"] = "Сетевая ошибка соединения с серверами Gemini. Проверьте подключение, VPN или настройки прокси в .env."
        else:
            result["feedback"] = f"Ошибка связи с ИИ: {error_str}. Включен резервный режим оценки."
        return result

    def _log_tokens(self, response, is_audio: bool = False):
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            u = response.usage_metadata
            mode = "audio" if is_audio else "text"
            logger.info(f"Токены ({mode}): in={u.prompt_token_count}, out={u.candidates_token_count}, total={u.total_token_count}")

    def _mock_evaluate(self, task_type: str, student_answer: str) -> Dict[str, Any]:
        max_scores = {"reading": 5, "retelling": 6, "monologue": 6}
        max_score = max_scores.get(task_type.lower(), 5)
        
        # Примерный подсчет для мок-режима
        words = len(student_answer.split())
        score = min(max_score, max(2, words // 15)) if words > 1 else (max_score - 1)

        return {
            "score": score,
            "max_score": max_score,
            "feedback": (
                "ИИ-проверка сейчас работает в резервном режиме (примерная оценка). "
                "Для точной оценки с разбором орфоэпии и интонации укажите GEMINI_API_KEY в файле конфигурации (.env)."
            ),
            "criteria": {
                "Режим работы": "Резервный (Mock). Установите GEMINI_API_KEY для полной экспертной проверки.",
                "Общая оценка": f"{score} из {max_score}",
            },
        }
