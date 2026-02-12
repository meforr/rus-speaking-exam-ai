import os
from typing import Dict, Any

from google import genai
from google.genai import types
from dotenv import load_dotenv
import json

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

loaded = False
for path in ["backend/conf.env", "conf.env", ".env"]:
    full_path = os.path.join(base_dir, path)
    if os.path.exists(full_path):
        result = load_dotenv(full_path, override=True)
        if result:
            test_key = os.getenv("GEMINI_API_KEY", "")
            print(f"Загружен файл конфигурации: {full_path}")
            if test_key:
                print(f"   Ключ после загрузки: {test_key[:15]}... (длина: {len(test_key)})")
            else:
                print(f"   ВНИМАНИЕ: Файл загружен, но GEMINI_API_KEY не найден!")
            loaded = True
            break

if not loaded:
    result = load_dotenv(override=True)
    if result:
        print(f"Загружен стандартный .env файл")


class AIChecker:
    """Класс для проверки ответов ученика с помощью Google Gemini API"""
    
    def __init__(self):
        self.client = None
        self.model_name: str | None = None
        self.available = False

        api_key = os.getenv("GEMINI_API_KEY")
        
        print(f"Отладка: Проверка API ключа Gemini...")
        print(f"   Ключ найден: {'Да' if api_key else 'Нет'}")
        if api_key:
            print(f"   Длина ключа: {len(api_key)} символов")
            print(f"   Начало ключа: {api_key[:10]}...")
        
        if api_key:
            api_key_clean = api_key.strip()
            
            if api_key_clean and len(api_key_clean) > 20:
                try:
                    self.client = genai.Client(api_key=api_key_clean)
                    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

                    print(f"   Используем модель: {model_name}")
                    self.model_name = model_name
                    self.available = True
                    print("Google Gemini API ключ успешно загружен")
                    print(f"Используется модель: {model_name}")
                            
                except Exception as e:
                    self.client = None
                    self.model_name = None
                    self.available = False
                    print(f"Ошибка при инициализации Gemini клиента: {e}")
            else:
                self.client = None
                self.model_name = None
                self.available = False
                print(f"GEMINI_API_KEY слишком короткий: {len(api_key_clean)} символов (нужно > 20)")
        else:
            self.client = None
            self.model_name = None
            self.available = False
            print("GEMINI_API_KEY не найден в переменных окружения.")
            print("   Проверьте файлы: conf.env, backend/conf.env, .env")
            print(f"   Текущая рабочая директория: {os.getcwd()}")
    
    def is_available(self) -> bool:
        """Проверка доступности ИИ"""
        return self.available
    
    async def check_answer(
        self, 
        task_type: str, 
        student_answer: str, 
        task_content: str,
        task_instructions: str
    ) -> Dict[str, Any]:
        """
        Проверяет ответ ученика
        
        Args:
            task_type: Тип задания (reading, retelling, monologue)
            student_answer: Ответ ученика
            task_content: Содержание задания
            task_instructions: Инструкции к заданию
            
        Returns:
            Словарь с результатами проверки
        """
        if not self.available:
            return self._mock_check(task_type, student_answer)
        
        system_prompt = self._get_system_prompt(task_type)
        user_prompt = self._get_user_prompt(
            task_type, student_answer, task_content, task_instructions
        )
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        try:
            generation_config = {
                "temperature": 0.2,
                "response_mime_type": "application/json"
            }
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=generation_config,
            )
            
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                print(f"Использовано токенов: {usage.prompt_token_count} входных + {usage.candidates_token_count} выходных = {usage.total_token_count} всего")
            
            result_text = response.text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            result = json.loads(result_text)
            return result
            
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON ответа от Gemini: {e}")
            print(f"   Ответ: {response.text[:200] if hasattr(response, 'text') else 'Нет ответа'}")
            return self._mock_check(task_type, student_answer)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                print(f"Превышен лимит запросов к Gemini API")
                print(f"   Это может быть из-за:")
                print(f"   - Превышения лимита запросов в минуту (15 запросов/мин)")
                print(f"   - Превышения дневного лимита (1500 запросов/день)")
                print(f"   - Использования экспериментальной модели с лимитом 0")
                print(f"   Подождите немного и попробуйте снова")
                result = self._mock_check(task_type, student_answer)
                result["feedback"] = "Превышен лимит запросов к Gemini API. Подождите немного и попробуйте снова. " + result["feedback"]
                return result
            else:
                print(f"Ошибка при обращении к Gemini API: {e}")
            return self._mock_check(task_type, student_answer)
    
    def _get_system_prompt(self, task_type: str) -> str:
        """Получить системный промпт для типа задания"""
        base_prompt = """Ты - эксперт по проверке устного собеседования по русскому языку для 9 класса в России.
Твоя задача - оценить ответ ученика по критериям ФИПИ и дать конструктивную обратную связь.
Верни ответ ТОЛЬКО в формате JSON с полями: score (int), max_score (int), feedback (string), criteria (dict).
"""
        
        prompts = {
            "reading": base_prompt + """
Критерии оценки чтения:
- Интонация и выразительность (0-2 балла)
- Правильность произношения (0-2 балла)
- Темп чтения (0-1 балл)
Максимум: 5 баллов""",
            
            "retelling": base_prompt + """
Критерии оценки пересказа:
- Сохранение микротем исходного текста (0-2 балла)
- Использование приёмов сжатия текста (0-2 балла)
- Смысловая цельность и речевая связность (0-2 балла)
Максимум: 6 баллов""",
            
            "monologue": base_prompt + """
Критерии оценки монолога:
- Соответствие теме (0-1 балл)
- Учёт коммуникативной задачи (0-1 балл)
- Смысловая цельность и речевая связность (0-2 балла)
- Использование средств выразительности (0-2 балла)
Максимум: 6 баллов""",
            
        }
        
        return prompts.get(task_type, base_prompt)
    
    def _get_user_prompt(
        self, 
        task_type: str, 
        student_answer: str, 
        task_content: str,
        task_instructions: str
    ) -> str:
        """Получить пользовательский промпт"""
        prompts = {
            "reading": f"""Задание: Прочитай текст вслух выразительно.

Текст для чтения:
{task_content}

Ответ ученика (транскрипция речи):
{student_answer}

Оцени ответ по критериям и верни JSON.""",
            
            "retelling": f"""Задание: Перескажи текст, включив в пересказ высказывание [указано в задании].

Исходный текст:
{task_content}

Инструкции: {task_instructions}

Ответ ученика (пересказ):
{student_answer}

Оцени ответ по критериям и верни JSON.""",
            
            "monologue": f"""Задание: Подготовь монолог на заданную тему.

Тема: {task_content}

Инструкции: {task_instructions}

Ответ ученика (монолог):
{student_answer}

Оцени ответ по критериям и верни JSON."""
        }
        
        return prompts.get(task_type, f"Задание: {task_content}\n\nОтвет: {student_answer}")
    
    def _get_audio_user_prompt(
        self,
        task_type: str,
        task_content: str,
        task_instructions: str,
    ) -> str:
        """Промпт для проверки по аудиозаписи."""
        prompts = {
            "reading": f"""Задание: Прочитай текст вслух выразительно.

Текст для чтения:
{task_content}

Инструкции к чтению:
{task_instructions}

Ниже прикреплена АУДИОЗАПИСЬ ответа ученика. 
Проанализируй ИМЕННО АУДИО: орфоэпию, фонетику, интонацию, темп чтения, паузы.
Сравни чтение с исходным текстом, оцени правильность произношения.
Верни только JSON в формате: score, max_score, feedback, criteria.""",
            "retelling": f"""Задание: Перескажи текст, включив в пересказ указанное высказывание.

Исходный текст:
{task_content}

Инструкции:
{task_instructions}

Ниже прикреплена АУДИОЗАПИСЬ пересказа ученика.
Проанализируй содержание и устную речь (орфоэпия, выразительность, логика пересказа).
Верни только JSON в формате: score, max_score, feedback, criteria.""",
            "monologue": f"""Задание: Подготовь монолог на заданную тему.

Тема:
{task_content}

Инструкции:
{task_instructions}

Ниже прикреплена АУДИОЗАПИСЬ монолога ученика.
Оцени содержание и качество устной речи (орфоэпия, фонетика, выразительность, связность).
Верни только JSON в формате: score, max_score, feedback, criteria.""",
        }

        return prompts.get(
            task_type,
            f"""Задание:
{task_content}

Инструкции:
{task_instructions}

Ниже прикреплена АУДИОЗАПИСЬ ответа ученика.
Оцени ответ по критериям устного собеседования и верни JSON (score, max_score, feedback, criteria).""",
        )
    
    async def check_answer_audio(
        self,
        task_type: str,
        audio_bytes: bytes,
        audio_mime: str,
        task_content: str,
        task_instructions: str,
    ) -> Dict[str, Any]:
        """
        Проверяет ответ ученика по аудиозаписи.

        Модель получает:
        - системный промпт с описанием критериев;
        - текст задания и инструкций;
        - сам аудиофайл как отдельную модальность.
        """
        if not self.available:
            # Если ИИ недоступен, возвращаем мок-оценку
            return self._mock_check(task_type, "audio_answer")

        system_prompt = self._get_system_prompt(task_type)
        user_prompt = self._get_audio_user_prompt(
            task_type=task_type,
            task_content=task_content,
            task_instructions=task_instructions,
        )

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

            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                print(
                    f"Использовано токенов (audio): "
                    f"{usage.prompt_token_count} входных + "
                    f"{usage.candidates_token_count} выходных = "
                    f"{usage.total_token_count} всего"
                )

            result_text = response.text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()

            result = json.loads(result_text)
            return result

        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON ответа от Gemini (audio): {e}")
            print(
                f"   Ответ: {response.text[:200] if hasattr(response, 'text') else 'Нет ответа'}"
            )
            return self._mock_check(task_type, "audio_answer")
        except Exception as e:
            error_str = str(e)
            if (
                "429" in error_str
                or "quota" in error_str.lower()
                or "rate limit" in error_str.lower()
            ):
                print(f"Превышен лимит запросов к Gemini API (audio)")
                result = self._mock_check(task_type, "audio_answer")
                result["feedback"] = (
                    "Превышен лимит запросов к Gemini API. "
                    "Подождите немного и попробуйте снова. "
                    + result["feedback"]
                )
                return result
            elif "Server disconnected without sending a response" in error_str:
                print(
                    "Похоже на сетевую ошибку: прокси / VPN / файрвол обрывает "
                    "соединение с серверами Gemini (audio)."
                )
                result = self._mock_check(task_type, "audio_answer")
                result["feedback"] = (
                    "Не удалось соединиться с серверами Gemini (audio). "
                    "Чаще всего это означает проблемы с VPN, прокси или фильтрацией HTTPS‑трафика. "
                    + result["feedback"]
                )
                return result
            else:
                print(f"Ошибка при обращении к Gemini API (audio): {e}")
            return self._mock_check(task_type, "audio_answer")
    
    def _mock_check(self, task_type: str, student_answer: str) -> Dict[str, Any]:
        """Моковая проверка, если ИИ недоступен"""
        max_scores = {
            "reading": 5,
            "retelling": 6,
            "monologue": 6
        }
        
        max_score = max_scores.get(task_type, 5)
        answer_length = len(student_answer.split())
        score = min(max_score, max(1, answer_length // 20))
        
        return {
            "score": score,
            "max_score": max_score,
            "feedback": "ИИ проверка недоступна. Это примерная оценка. Установите GEMINI_API_KEY для полной проверки.",
            "criteria": {
                "note": "Моковая проверка. Установите GEMINI_API_KEY для реальной проверки."
            }
        }
