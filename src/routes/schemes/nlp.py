from pydantic import BaseModel
from typing import Optional


class PushRequest(BaseModel):
    do_reset: Optional[int] = 0


class SearchRequest(BaseModel):
    text: str
    limit: Optional[int] = 5
    chapters: Optional[list[str]] = None
    file_chapter_filters: Optional[list[dict]] = None


class ExamRequest(BaseModel):
    content: str
    difficulty: Optional[str] = "medium"
    num_mcq: Optional[int] = 3
    num_written: Optional[int] = 2
    chapters: Optional[list[str]] = None
    file_chapter_filters: Optional[list[dict]] = None


class EvaluateQuestionItem(BaseModel):
    question: str
    reference: Optional[str] = None


class EvaluateRequest(BaseModel):
    questions: list[EvaluateQuestionItem]

class SummarizeContextRequest(BaseModel):
    content: Optional[str] = ""
    chapters: Optional[list[str]] = None
    file_chapter_filters: Optional[list[dict]] = None

