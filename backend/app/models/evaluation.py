from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ExamRequest(BaseModel):
    task_type: str
    student_answer: str
    task_id: Optional[int] = None


class DSPMetricsModel(BaseModel):
    total_duration_sec: float = 0.0
    speech_duration_sec: float = 0.0
    pause_duration_sec: float = 0.0
    speech_ratio_pct: float = 0.0
    wpm: float = 0.0
    spm: float = 0.0
    tempo_status: str = "не определен"
    tempo_score: int = 0
    pauses_count: int = 0
    justified_pauses_count: int = 0
    unjustified_pauses_count: int = 0
    justified_pauses_pct: float = 100.0
    pause_segments: List[Dict[str, Any]] = Field(default_factory=list)
    pitch_contour: List[float] = Field(default_factory=list)
    pitch_mean_hz: float = 0.0
    intonation_status: str = ""
    orthoepy_matches: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class ExamResponse(BaseModel):
    score: int
    max_score: int
    feedback: str
    criteria: Dict[str, Any] = Field(default_factory=dict)
    dsp: Optional[DSPMetricsModel] = None
