from datetime import datetime
from enum import Enum
from typing import Union, Optional

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
    poster: Optional[str] = None


class SequelSaladResult(BaseModel):
    question: SequelSaladGeminiQuestion
    franchise: str
    user_answer: str
    result: SequelSaladGeminiAnswer
    speech: str


# Back to the Future Trivia

class BttfTriviaGeminiQuestion(BaseModel):
    question: str
    option_1: str
    option_2: str
    option_3: str
    option_4: str
    correct_answer: int


class BttfTriviaGeminiAnswer(BaseModel):
    answer: str


class BttfTriviaData(BaseModel):
    question: BttfTriviaGeminiQuestion
    speech: str


class BttfTriviaResult(BaseModel):
    question: BttfTriviaGeminiQuestion
    user_answer: int
    result: BttfTriviaGeminiAnswer
    points: int
    speech: str


# Movie Trivia

class TriviaGeminiQuestion(BaseModel):
    question: str
    option_1: str
    option_2: str
    option_3: str
    option_4: str
    correct_answer: int


class TriviaGeminiAnswer(BaseModel):
    answer: str


class TriviaData(BaseModel):
    question: TriviaGeminiQuestion
    movie: dict
    speech: str


class TriviaResult(BaseModel):
    question: TriviaGeminiQuestion
    movie: dict
    user_answer: int
    result: TriviaGeminiAnswer
    points: int
    speech: str


class StartQuizRequest(BaseModel):
    quiz_type: QuizType
    personality: Personality = Personality.DEFAULT


class StartQuizResponse(BaseModel):
    quiz_id: str
    quiz_type: QuizType
    quiz_data: Union[TitleDetectivesData, SequelSaladData, BttfTriviaData, TriviaData]


class FinishQuizRequest(BaseModel):
    quiz_id: str
    answer: Union[str, int]


class FinishQuizResponse(BaseModel):
    quiz_id: str
    quiz_result: Union[TitleDetectivesResult, SequelSaladResult, BttfTriviaResult, TriviaResult]


class SessionData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    quiz_id: str
    quiz_type: QuizType
    quiz_data: Union[TitleDetectivesData, SequelSaladData, BttfTriviaData, TriviaData]
    chat: ChatSession
    started_at: datetime


class SessionResponse(BaseModel):
    quiz_id: str
    quiz_type: QuizType
    started_at: datetime


class ResetLimitsRequest(BaseModel):
    password: str


class LimitsResponse(BaseModel):
    limits: dict
    usage_counts: dict
    current_date: datetime
