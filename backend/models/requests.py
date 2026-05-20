from __future__ import annotations
"""Pydantic request models for all Distill API endpoints."""

from typing import Literal
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    transcript: str = Field(..., min_length=100, description="Full meeting transcript text")
    student_name: str = Field(default="Student", max_length=100)
    session_label: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, description="Article URL if content was fetched from a link")  
    source_type: str | None = Field(default=None, description="One of: paste | file | url")                    

class MCQEvaluateRequest(BaseModel):
    session_id: str
    question_id: int
    selected_answer: Literal["A", "B", "C", "D"]
    time_taken_seconds: int | None = None
    hint_level_used: int = Field(default=0, ge=0, le=3)


class VoiceEvaluateRequest(BaseModel):
    session_id: str
    question_id: int
    student_answer: str = Field(..., min_length=10)
    answer_duration_seconds: float | None = None
    was_voice: bool = True
