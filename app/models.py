from typing import Any, Literal

from pydantic import BaseModel, Field


class ChoiceQuestion(BaseModel):
    type: Literal["choice"]
    options: list[str] | dict[str, str | None]


class NoulQuestion(BaseModel):
    type: Literal["noul"]
    instruction: str
    true_criteria: str | None = None
    false_criteria: str | None = None


class ScoreQuestion(BaseModel):
    type: Literal["score"]
    instruction: str
    levels: list[str] | None = None


Question = ChoiceQuestion | NoulQuestion | ScoreQuestion


class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    questions: dict[str, Question] = Field(..., min_length=1)


class ClassifyResponse(BaseModel):
    model: str
    answers: dict[str, Any]
    usage: dict[str, int]
    routing: dict[str, Any] | None = None
