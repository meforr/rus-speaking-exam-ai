from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.deps import get_task_repository
from backend.app.models.task import TaskResponse, TasksListResponse
from backend.app.services.task_repository import TaskRepository

router = APIRouter()


@router.get("/tasks", response_model=TasksListResponse)
async def get_tasks(
    repo: TaskRepository = Depends(get_task_repository),
):
    """Получить список всех доступных заданий экзамена"""
    return repo.get_all_tasks_summary()


@router.get("/task/{task_type}", response_model=TaskResponse)
async def get_task(
    task_type: str,
    task_id: Optional[int] = None,
    repo: TaskRepository = Depends(get_task_repository),
):
    """Получить конкретное или случайное задание по типу"""
    try:
        task = repo.get_task(task_type, task_id)
        return TaskResponse(
            task_id=task.id,
            task_type=task_type,
            content=task.content,
            instructions=task.instructions,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
