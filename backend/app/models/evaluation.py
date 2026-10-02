from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ExamRequest(BaseModel):
    task_type: str
    student_answer: str
    task_id: Optional[int] = None


class ExamResponse(BaseModel):
    score: int
    max_score: int
    feedback: str
    criteria: Dict[str, Any] = Field(default_factory=dict)
