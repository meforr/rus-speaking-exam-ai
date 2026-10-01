from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    READING = "reading"
    RETELLING = "retelling"
    MONOLOGUE = "monologue"


class TaskItem(BaseModel):
    id: int
    content: str
    instructions: str


class TaskResponse(BaseModel):
    task_id: int
    task_type: str
    content: str
    instructions: str


class TasksListResponse(BaseModel):
    reading: List[TaskItem] = Field(default_factory=list)
    retelling: List[TaskItem] = Field(default_factory=list)
    monologue: List[TaskItem] = Field(default_factory=list)
