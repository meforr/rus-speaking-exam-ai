import json
import random
from pathlib import Path
from typing import Dict, List, Optional
from backend.app.core.config import settings
from backend.app.models.task import TaskItem, TasksListResponse, TaskType


class TaskRepository:
    """Репозиторий для загрузки и предоставления экзаменационных заданий из JSON файлов"""

    def __init__(self, tasks_dir: Optional[Path] = None):
        self.tasks_dir = tasks_dir or settings.tasks_dir
        self._cache: Dict[str, List[TaskItem]] = {}
        self.load_all()

    def load_all(self):
        """Загрузка всех заданий из JSON в кэш памяти"""
        self._cache = {
            "reading": self._load_file("reading.json"),
            "retelling": self._load_file("retelling.json"),
            "monologue": self._load_file("monologue.json"),
        }

    def _load_file(self, filename: str) -> List[TaskItem]:
        file_path = self.tasks_dir / filename
        if not file_path.is_file():
            return []
        try:
            raw_data = json.loads(file_path.read_text(encoding="utf-8"))
            return [TaskItem(**item) for item in raw_data]
        except Exception as e:
            print(f"Ошибка при загрузке {file_path}: {e}")
            return []

    def get_tasks_by_type(self, task_type: str) -> List[TaskItem]:
        self.load_all()
        normalized = task_type.lower()
        return self._cache.get(normalized, [])

    def get_task(self, task_type: str, task_id: Optional[int] = None) -> TaskItem:
        tasks = self.get_tasks_by_type(task_type)
        if not tasks:
            raise ValueError(f"Задания типа '{task_type}' не найдены или банк заданий пуст")

        if task_id is None:
            return random.choice(tasks)

        for t in tasks:
            if t.id == task_id:
                return t

        raise ValueError(f"Задание с ID {task_id} не найдено для типа '{task_type}'")

    def get_all_tasks_summary(self) -> TasksListResponse:
        return TasksListResponse(
            reading=self.get_tasks_by_type("reading"),
            retelling=self.get_tasks_by_type("retelling"),
            monologue=self.get_tasks_by_type("monologue"),
        )
