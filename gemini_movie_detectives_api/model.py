from datetime import datetime
from enum import Enum
from typing import Union

from pydantic import BaseModel, ConfigDict
from vertexai.generative_models import ChatSession

from gemini_movie_detectives_api.gemini import GeminiQuestion, GeminiAnswer


class QuizType(str, Enum):
    TITLE_DETECTIVES = 'title-detectives'
    SEQUEL_SALAD = 'sequel-salad'
    BTTF_TRIVIA = 'bttf-trivia'
    TRIVIA = 'trivia'


class UserAnswer(BaseModel):
    answer: str


class TitleDetectivesData(BaseModel):
    question: GeminiQuestion
    movie: dict
    speech: str


class StartQuizResponse(BaseModel):
    quiz_id: str
    quiz_type: QuizType
    quiz_data: Union[TitleDetectivesData, dict]


class FinishQuizResponse(BaseModel):
    quiz_id: str
    question: GeminiQuestion
    movie: dict
    user_answer: str
    result: GeminiAnswer
    speech: str


class SessionData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    quiz_id: str
    quiz_data: Union[TitleDetectivesData, dict]
    chat: ChatSession
    started_at: datetime


class SessionResponse(BaseModel):
    quiz_id: str
    question: GeminiQuestion
    movie: dict
    started_at: datetime


class LimitResponse(BaseModel):
    daily_limit: int
    quiz_count: int
    last_reset_time: datetime
    last_reset_date: datetime
    current_date: datetime


class Stats(BaseModel):
    quiz_count_total: int = 0
    points_total: int = 0


class StatsResponse(BaseModel):
    stats: Stats
    limit: LimitResponse
