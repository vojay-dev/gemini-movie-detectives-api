from datetime import datetime
from enum import Enum
from typing import Union

from pydantic import BaseModel, ConfigDict
from vertexai.generative_models import ChatSession


class QuizType(str, Enum):
    TITLE_DETECTIVES = 'title-detectives'
    SEQUEL_SALAD = 'sequel-salad'
    BTTF_TRIVIA = 'bttf-trivia'
    TRIVIA = 'trivia'


class Personality(str, Enum):
    DEFAULT = 'default'
    CHRISTMAS = 'christmas'
    SCIENTIST = 'scientist'
    DAD = 'dad'


# Title Detectives

class TitleDetectivesGeminiQuestion(BaseModel):
    question: str
    hint1: str
    hint2: str


class TitleDetectivesGeminiAnswer(BaseModel):
    points: int
    answer: str


class TitleDetectivesData(BaseModel):
    question: TitleDetectivesGeminiQuestion
    movie: dict
    speech: str


class TitleDetectivesResult(BaseModel):
    question: TitleDetectivesGeminiQuestion
    movie: dict
    user_answer: str
    result: TitleDetectivesGeminiAnswer
    speech: str


# Sequel Salad

class SequelSaladGeminiQuestion(BaseModel):
    sequel_plot: str
    sequel_title: str
    poster_prompt: str


class SequelSaladGeminiAnswer(BaseModel):
    points: int
    answer: str


class SequelSaladData(BaseModel):
    question: SequelSaladGeminiQuestion
    franchise: str
    speech: str


class SequelSaladResult(BaseModel):
    question: SequelSaladGeminiQuestion
    franchise: str
    user_answer: str
    result: SequelSaladGeminiAnswer
    speech: str


class StartQuizRequest(BaseModel):
    quiz_type: QuizType
    personality: Personality = Personality.DEFAULT


class StartQuizResponse(BaseModel):
    quiz_id: str
    quiz_type: QuizType
    quiz_data: Union[TitleDetectivesData, SequelSaladData]


class FinishQuizRequest(BaseModel):
    quiz_id: str
    answer: Union[str, int]


class FinishQuizResponse(BaseModel):
    quiz_id: str
    quiz_result: Union[TitleDetectivesResult, SequelSaladResult]


class SessionData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    quiz_id: str
    quiz_type: QuizType
    quiz_data: Union[TitleDetectivesData, SequelSaladData]
    chat: ChatSession
    started_at: datetime


class SessionResponse(BaseModel):
    quiz_id: str
    quiz_type: QuizType
    started_at: datetime


class LimitResponse(BaseModel):
    daily_limit: int
    quiz_count: int
    last_reset_time: datetime
    last_reset_date: datetime
    current_date: datetime
