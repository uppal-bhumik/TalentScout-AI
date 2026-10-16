"""Persistence for candidates, questions, answers, evaluations and reports.

SQLAlchemy over SQLite by default (`Config.DATABASE_URL`), so an assessment
survives a browser refresh and recruiters can reopen past results. Any
SQLAlchemy URL works, which is what makes a hosted Postgres deployment a
config change rather than a rewrite.

Every public function returns plain dictionaries rather than ORM instances:
the Streamlit layer holds values across reruns, and a detached ORM object
would raise the moment it was touched outside its session.
"""

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urlparse

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    desc,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    selectinload,
    sessionmaker,
)

from config import Config
from utils import get_logger

logger = get_logger("TalentScout.db")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Candidate(Base):
    """One person. Re-identified by email so repeat assessments group together."""

    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(Config.MAX_NAME_LENGTH))
    email: Mapped[str] = mapped_column(String(Config.MAX_EMAIL_LENGTH), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(Config.MAX_PHONE_LENGTH))
    experience: Mapped[Optional[float]] = mapped_column(Float)
    location: Mapped[Optional[str]] = mapped_column(String(Config.MAX_LOCATION_LENGTH))
    tech_stack: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    assessments: Mapped[List["Assessment"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "experience": self.experience,
            "location": self.location,
            "tech_stack": list(self.tech_stack or []),
        }


class Assessment(Base):
    """One screening session: the questions asked and how far it got."""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ended_early: Mapped[bool] = mapped_column(Boolean, default=False)
    # True when the questions came from the canned fallback set rather than
    # from the model, i.e. this assessment was not personalised.
    questions_degraded: Mapped[bool] = mapped_column(Boolean, default=False)

    candidate: Mapped[Candidate] = relationship(back_populates="assessments")
    questions: Mapped[List["Question"]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="Question.position",
    )
    report: Mapped[Optional["Report"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", uselist=False
    )


class Question(Base):
    """A question put to the candidate, with the answer it drew (if any)."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)  # 0-based, as asked
    text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32), default="programming")
    difficulty: Mapped[str] = mapped_column(String(32), default="intermediate")
    source: Mapped[str] = mapped_column(String(16), default="llm")  # llm/template/fallback

    assessment: Mapped[Assessment] = relationship(back_populates="questions")
    answer: Mapped[Optional["Answer"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", uselist=False
    )


class Answer(Base):
    """What the candidate wrote. Absent for skipped questions."""

    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), unique=True)
    text: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    question: Mapped[Question] = relationship(back_populates="answer")
    evaluation: Mapped[Optional["Evaluation"]] = relationship(
        back_populates="answer", cascade="all, delete-orphan", uselist=False
    )


class Evaluation(Base):
    """The score and feedback for one answer."""

    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    answer_id: Mapped[int] = mapped_column(ForeignKey("answers.id"), unique=True)
    score: Mapped[float] = mapped_column(Float)
    feedback: Mapped[str] = mapped_column(Text)
    # A degraded evaluation is a placeholder, not a judgement - it is kept so
    # the recruiter view can say which scores are real.
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)
    degraded_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    answer: Mapped[Answer] = relationship(back_populates="evaluation")


class Report(Base):
    """The final overall assessment, including the completion arithmetic."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), unique=True)
    overall_score: Mapped[float] = mapped_column(Float)
    performance_score: Mapped[float] = mapped_column(Float)
    completion_penalty_factor: Mapped[float] = mapped_column(Float, default=1.0)
    questions_answered: Mapped[int] = mapped_column(Integer, default=0)
    completion_status: Mapped[str] = mapped_column(String(64), default="")
    recommendation: Mapped[str] = mapped_column(String(32), default="Maybe")
    detailed_feedback: Mapped[str] = mapped_column(Text, default="")
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)
    degraded_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    assessment: Mapped[Assessment] = relationship(back_populates="report")

    def to_dict(self) -> Dict[str, Any]:
        """Shaped like the dict LLMHandler.generate_final_report returns."""
        return {
            "overall_score": self.overall_score,
            "performance_score": self.performance_score,
            "completion_penalty_factor": self.completion_penalty_factor,
            "questions_answered": self.questions_answered,
            "completion_status": self.completion_status,
            "recommendation": self.recommendation,
            "detailed_feedback": self.detailed_feedback,
            "degraded": self.degraded,
            "degraded_reason": self.degraded_reason,
        }


# ----------------------------------------------------------------------
# Engine / session plumbing
# ----------------------------------------------------------------------

_engine = None
_SessionFactory = None


def _ensure_sqlite_directory(url: str) -> None:
    """Create the folder for a file-backed SQLite database if it is missing."""
    if not url.startswith("sqlite"):
        return
    path = urlparse(url).path.lstrip("/")
    if not path or path == ":memory:":
        return
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def init_db(database_url: Optional[str] = None, echo: Optional[bool] = None):
    """Create the engine and tables. Idempotent; safe to call on every rerun."""
    global _engine, _SessionFactory

    url = database_url or Config.DATABASE_URL

    if _engine is not None and str(_engine.url) == url:
        return _engine

    _ensure_sqlite_directory(url)

    connect_args = {}
    if url.startswith("sqlite"):
        # Streamlit serves each session on its own thread.
        connect_args["check_same_thread"] = False

    _engine = create_engine(
        url,
        echo=Config.DATABASE_ECHO if echo is None else echo,
        connect_args=connect_args,
        future=True,
    )
    Base.metadata.create_all(_engine)
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    logger.info("Database ready at %s", _engine.url.render_as_string(hide_password=True))
    return _engine


def reset_engine() -> None:
    """Drop the cached engine. Used by tests to point at a fresh database."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope: commits on success, rolls back on error."""
    if _SessionFactory is None:
        init_db()

    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ----------------------------------------------------------------------
# Write operations
# ----------------------------------------------------------------------

def upsert_candidate(session: Session, candidate_data: Dict) -> Candidate:
    """Find the candidate by email or create them, refreshing their details."""
    email = (candidate_data.get("email") or "").strip().lower()
    candidate = None

    if email:
        candidate = session.scalar(select(Candidate).where(Candidate.email == email))

    if candidate is None:
        candidate = Candidate(email=email, name=candidate_data.get("name", "Unknown"))
        session.add(candidate)

    candidate.name = candidate_data.get("name", candidate.name)
    candidate.phone = candidate_data.get("phone", candidate.phone)
    candidate.experience = candidate_data.get("experience", candidate.experience)
    candidate.location = candidate_data.get("location", candidate.location)
    candidate.tech_stack = list(candidate_data.get("tech_stack") or candidate.tech_stack or [])

    session.flush()
    return candidate


def create_assessment(candidate_data: Dict, questions: List[Dict]) -> int:
    """Persist the candidate and the generated question set. Returns its id."""
    with session_scope() as session:
        candidate = upsert_candidate(session, candidate_data)

        assessment = Assessment(
            candidate_id=candidate.id,
            questions_degraded=any(q.get("degraded") for q in questions),
        )
        session.add(assessment)
        session.flush()

        for position, question in enumerate(questions):
            session.add(
                Question(
                    assessment_id=assessment.id,
                    position=position,
                    text=question.get("question", ""),
                    category=question.get("category", "programming"),
                    difficulty=question.get("difficulty", "intermediate"),
                    source=question.get("source", "llm"),
                )
            )

        session.flush()
        logger.info(
            "Created assessment %d for candidate %d with %d questions",
            assessment.id,
            candidate.id,
            len(questions),
        )
        return assessment.id


def record_answer(
    assessment_id: int, position: int, answer_text: str, evaluation: Dict
) -> None:
    """Store an answer and its evaluation, replacing any earlier attempt.

    Re-answering is possible because the candidate can navigate back, so this
    overwrites rather than accumulating duplicate rows.
    """
    with session_scope() as session:
        question = session.scalar(
            select(Question).where(
                Question.assessment_id == assessment_id, Question.position == position
            )
        )
        if question is None:
            logger.error(
                "No question at position %d of assessment %s; answer not stored.",
                position,
                assessment_id,
            )
            return

        if question.answer is not None:
            session.delete(question.answer)
            session.flush()

        answer = Answer(question_id=question.id, text=answer_text)
        session.add(answer)
        session.flush()

        session.add(
            Evaluation(
                answer_id=answer.id,
                score=evaluation.get("score", 0),
                feedback=evaluation.get("feedback", ""),
                degraded=bool(evaluation.get("degraded")),
                degraded_reason=evaluation.get("degraded_reason"),
            )
        )


def save_final_report(assessment_id: int, report: Dict, ended_early: bool = False) -> None:
    """Store (or replace) the final report and close out the assessment."""
    with session_scope() as session:
        assessment = session.get(Assessment, assessment_id)
        if assessment is None:
            logger.error("Assessment %s not found; report not stored.", assessment_id)
            return

        if assessment.report is not None:
            session.delete(assessment.report)
            session.flush()

        session.add(
            Report(
                assessment_id=assessment_id,
                overall_score=report.get("overall_score", 0),
                performance_score=report.get("performance_score", report.get("overall_score", 0)),
                completion_penalty_factor=report.get("completion_penalty_factor", 1.0),
                questions_answered=report.get("questions_answered", 0),
                completion_status=report.get("completion_status", ""),
                recommendation=report.get("recommendation", "Maybe"),
                detailed_feedback=report.get("detailed_feedback", ""),
                degraded=bool(report.get("degraded")),
                degraded_reason=report.get("degraded_reason"),
            )
        )

        assessment.ended_early = ended_early
        assessment.completed_at = _utcnow()
        logger.info("Saved final report for assessment %d", assessment_id)


# ----------------------------------------------------------------------
# Read operations
# ----------------------------------------------------------------------

def list_assessments(limit: int = 100) -> List[Dict[str, Any]]:
    """Summary rows for the recruiter list, most recent first."""
    with session_scope() as session:
        assessments = session.scalars(
            select(Assessment)
            .options(
                selectinload(Assessment.candidate),
                selectinload(Assessment.report),
                selectinload(Assessment.questions).selectinload(Question.answer),
            )
            .order_by(desc(Assessment.started_at))
            .limit(limit)
        ).all()

        rows = []
        for assessment in assessments:
            answered = sum(1 for q in assessment.questions if q.answer is not None)
            report = assessment.report
            rows.append(
                {
                    "assessment_id": assessment.id,
                    "name": assessment.candidate.name,
                    "email": assessment.candidate.email,
                    "experience": assessment.candidate.experience,
                    "tech_stack": list(assessment.candidate.tech_stack or []),
                    "started_at": assessment.started_at,
                    "completed_at": assessment.completed_at,
                    "ended_early": assessment.ended_early,
                    "questions_total": len(assessment.questions),
                    "questions_answered": answered,
                    "overall_score": report.overall_score if report else None,
                    "recommendation": report.recommendation if report else None,
                    "degraded": bool(report.degraded) if report else assessment.questions_degraded,
                    "is_complete": report is not None,
                }
            )
        return rows


def get_assessment(assessment_id: int) -> Optional[Dict[str, Any]]:
    """Everything needed to re-render one assessment's report."""
    with session_scope() as session:
        assessment = session.scalar(
            select(Assessment)
            .options(
                selectinload(Assessment.candidate),
                selectinload(Assessment.report),
                selectinload(Assessment.questions)
                .selectinload(Question.answer)
                .selectinload(Answer.evaluation),
            )
            .where(Assessment.id == assessment_id)
        )
        if assessment is None:
            return None

        answers: List[Dict[str, Any]] = []
        evaluations: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []

        for question in assessment.questions:
            if question.answer is None:
                skipped.append({"question": question.text, "category": question.category})
                continue

            answers.append(
                {
                    "question": question.text,
                    "answer": question.answer.text,
                    "category": question.category,
                    "difficulty": question.difficulty,
                }
            )
            evaluation = question.answer.evaluation
            evaluations.append(
                {
                    "score": evaluation.score if evaluation else 0,
                    "feedback": evaluation.feedback if evaluation else "",
                    "degraded": bool(evaluation.degraded) if evaluation else False,
                    "degraded_reason": evaluation.degraded_reason if evaluation else None,
                }
            )

        return {
            "assessment_id": assessment.id,
            "candidate_data": assessment.candidate.to_dict(),
            "answers": answers,
            "evaluations": evaluations,
            "skipped_questions": skipped,
            "final_report": assessment.report.to_dict() if assessment.report else None,
            "questions_total": len(assessment.questions),
            "ended_early": assessment.ended_early,
            "started_at": assessment.started_at,
            "completed_at": assessment.completed_at,
        }


def delete_assessment(assessment_id: int) -> bool:
    """Remove one assessment and everything hanging off it."""
    with session_scope() as session:
        assessment = session.get(Assessment, assessment_id)
        if assessment is None:
            return False
        session.delete(assessment)
        logger.info("Deleted assessment %d", assessment_id)
        return True
