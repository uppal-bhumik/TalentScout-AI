"""Pydantic models describing the JSON the LLM must return.

These are handed to the OpenAI SDK's `chat.completions.parse` helper, which
turns them into a strict JSON schema and guarantees the reply matches it. That
replaces the hand-written regex parsing this module used to need: there is no
longer any markdown, label or heading variation to survive, because the model
cannot emit prose at all.

Note for schema edits: OpenAI structured outputs require every field to be
required (no defaults) and `additionalProperties: false`, which the SDK derives
from these models. Keep fields non-optional and avoid defaults here - put any
defaulting in llm_handler after parsing.
"""

from typing import List, Literal

from pydantic import BaseModel, Field

from config import Config

QuestionCategory = Literal["programming", "system_design", "problem_solving"]
QuestionDifficulty = Literal["beginner", "intermediate", "advanced"]
Recommendation = Literal["Strong Hire", "Hire", "Maybe", "No Hire"]


class GeneratedQuestion(BaseModel):
    """One technical interview question."""

    question: str = Field(description="The question text, as it will be shown to the candidate.")
    category: QuestionCategory
    difficulty: QuestionDifficulty


class GeneratedQuestions(BaseModel):
    """The full set of questions for one candidate."""

    questions: List[GeneratedQuestion] = Field(
        description=f"Exactly {Config.DEFAULT_QUESTIONS} questions, ordered as they should be asked."
    )


class AnswerEvaluation(BaseModel):
    """The score and feedback for a single answer."""

    score: int = Field(
        ge=Config.MIN_SCORE,
        le=Config.MAX_SCORE,
        description=f"Technical quality of the answer, {Config.MIN_SCORE}-{Config.MAX_SCORE}.",
    )
    feedback: str = Field(
        description="Constructive feedback: what was strong, what was missing, what to improve."
    )


class FinalReport(BaseModel):
    """The overall assessment of a candidate."""

    overall_score: float = Field(
        ge=Config.MIN_SCORE,
        le=Config.MAX_SCORE,
        description=(
            "Technical quality of the answers actually given. Do NOT lower this because "
            "fewer questions were answered - a separate fixed completion adjustment "
            "handles that, and penalising it here would double-count it."
        ),
    )
    recommendation: Recommendation
    analysis: str = Field(
        description=(
            "Professional assessment covering technical competency, communication, "
            "problem-solving approach, strengths, areas for improvement and fit for "
            "the candidate's experience level."
        )
    )
