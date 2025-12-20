import os
from typing import Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv
import json

# Загружаем переменные окружения (пробуем разные пути)
# ВАЖНО: Используем override=True чтобы перезаписать существующие переменные
# Определяем базовую директорию проекта
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Пробуем загрузить из разных мест (в порядке приоритета)
# Сначала backend/conf.env (самый приоритетный), потом conf.env, потом .env
loaded = False
for path in ["backend/conf.env", "conf.env", ".env"]:
    full_path = os.path.join(base_dir, path)
    if os.path.exists(full_path):
        # override=True перезаписывает уже существующие переменные
        result = load_dotenv(full_path, override=True)
        if result:
            # Проверяем, что ключ действительно загрузился
            test_key = os.getenv("GEMINI_API_KEY", "")
            print(f"✅ Загружен файл конфигурации: {full_path}")
            if test_key:
                print(f"   Ключ после загрузки: {test_key[:15]}... (длина: {len(test_key)})")
            else:
                print(f"   ⚠️  ВНИМАНИЕ: Файл загружен, но GEMINI_API_KEY не найден!")
            loaded = True
            break

if not loaded:
    # Пробуем стандартный .env (тоже с override)
    result = load_dotenv(override=True)
    if result:
        print(f"✅ Загружен стандартный .env файл")


class AIChecker:
    """Класс для проверки ответов ученика с помощью Google Gemini API"""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        
        # Детальное логирование для диагностики
        print(f"🔍 Отладка: Проверка API ключа Gemini...")
        print(f"   Ключ найден: {'Да' if api_key else 'Нет'}")
        if api_key:
            print(f"   Длина ключа: {len(api_key)} символов")
            print(f"   Начало ключа: {api_key[:10]}...")
        
        if api_key:
            # Проверяем, что ключ не пустой
            api_key_clean = api_key.strip()
            
            if api_key_clean and len(api_key_clean) > 20:
                try:
                    # Настраиваем Gemini API
                    genai.configure(api_key=api_key_clean)
                    
                    # Получаем список доступных моделей
                    print("   Получаем список доступных моделей...")
                    models = genai.list_models()
                    available_models = [
                        m.name.split('/')[-1] 
                        for m in models 
                        if 'generateContent' in m.supported_generation_methods
                    ]
                    
                    if not available_models:
                        raise Exception("Нет доступных моделей для generateContent")
                    
                    # Фильтруем доступные модели, исключая экспериментальные
                    # Экспериментальные модели (exp) имеют лимит 0 на бесплатном тарифе
                    available_models = [
                        m for m in available_models 
                        if not m.endswith('-exp') and 'exp' not in m.lower()
                    ]
                    
                    if not available_models:
                        raise Exception("Нет доступных стабильных моделей (экспериментальные исключены)")
                    
                    # Предпочитаем стабильные flash модели (быстрее и дешевле)
                    preferred_models = [
                        'gemini-1.5-flash-latest',
                        'gemini-1.5-flash',
                        'gemini-1.5-pro-latest',
                        'gemini-1.5-pro',
                        'gemini-pro'
                    ]
                    
                    # Ищем предпочитаемую модель среди доступных
                    model_name = None
                    for preferred in preferred_models:
                        if preferred in available_models:
                            model_name = preferred
                            break
                    
                    # Если предпочитаемой нет, берём первую доступную
                    if not model_name:
                        model_name = available_models[0]
                    
                    print(f"   Используем модель: {model_name}")
                    self.model = genai.GenerativeModel(model_name)
                    self.available = True
                    print("✅ Google Gemini API ключ успешно загружен")
                    print(f"✅ Используется модель: {model_name}")
                            
                except Exception as e:
                    self.model = None
                    self.available = False
                    print(f"❌ Ошибка при инициализации Gemini клиента: {e}")
            else:
                self.model = None
                self.available = False
                print(f"⚠️  GEMINI_API_KEY слишком короткий: {len(api_key_clean)} символов (нужно > 20)")
        else:
            self.model = None
            self.available = False
            print("⚠️  GEMINI_API_KEY не найден в переменных окружения.")
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
        
        # Формируем промпт в зависимости от типа задания
        system_prompt = self._get_system_prompt(task_type)
        user_prompt = self._get_user_prompt(
            task_type, student_answer, task_content, task_instructions
        )
        
        # Объединяем системный и пользовательский промпты для Gemini
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        try:
            # Генерируем ответ через Gemini
            # Используем более простую конфигурацию для совместимости
            generation_config = {
                "temperature": 0.3,
                "response_mime_type": "application/json"
            }
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            # Логируем использование токенов
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                print(f"📊 Использовано токенов: {usage.prompt_token_count} входных + {usage.candidates_token_count} выходных = {usage.total_token_count} всего")
            
            # Парсим JSON ответ
            result_text = response.text.strip()
            # Убираем markdown код блоки, если есть
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
            print(f"❌ Ошибка парсинга JSON ответа от Gemini: {e}")
            print(f"   Ответ: {response.text[:200] if hasattr(response, 'text') else 'Нет ответа'}")
            return self._mock_check(task_type, student_answer)
        except Exception as e:
            error_str = str(e)
            # Проверяем, не превышена ли квота
            if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                print(f"⚠️  Превышен лимит запросов к Gemini API")
                print(f"   Это может быть из-за:")
                print(f"   - Превышения лимита запросов в минуту (15 запросов/мин)")
                print(f"   - Превышения дневного лимита (1500 запросов/день)")
                print(f"   - Использования экспериментальной модели с лимитом 0")
                print(f"   Подождите немного и попробуйте снова")
                # Возвращаем моковую проверку с информативным сообщением
                result = self._mock_check(task_type, student_answer)
                result["feedback"] = "⚠️ Превышен лимит запросов к Gemini API. Подождите немного и попробуйте снова. " + result["feedback"]
                return result
            else:
                print(f"❌ Ошибка при обращении к Gemini API: {e}")
            return self._mock_check(task_type, student_answer)
    
    def _get_system_prompt(self, task_type: str) -> str:
        """Получить системный промпт для типа задания"""
        base_prompt = """Ты - эксперт по проверке устного собеседования по русскому языку для 9 класса.
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
    
    def _mock_check(self, task_type: str, student_answer: str) -> Dict[str, Any]:
        """Моковая проверка, если ИИ недоступен"""
        max_scores = {
            "reading": 5,
            "retelling": 6,
            "monologue": 6
        }
        
        max_score = max_scores.get(task_type, 5)
        # Простая эвристика: оценка на основе длины ответа
        answer_length = len(student_answer.split())
        score = min(max_score, max(1, answer_length // 20))
        
        return {
            "score": score,
            "max_score": max_score,
            "feedback": "⚠️ ИИ проверка недоступна. Это примерная оценка. Установите GEMINI_API_KEY для полной проверки.",
            "criteria": {
                "note": "Моковая проверка. Установите GEMINI_API_KEY для реальной проверки."
            }
        }
