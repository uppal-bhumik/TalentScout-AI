"""All LLM interaction: question generation, answer scoring and the final report.

Every call goes through `_complete`, which asks the model for a Pydantic-shaped
reply via OpenAI structured outputs and retries transient failures with
exponential backoff. If a call still fails, the caller falls back to canned
content and marks the result `degraded` so the UI can say so out loud - a
silent fallback is worse than an error, because it looks like a working app
that happens to score every candidate the same.
"""

import random
import time
from typing import Dict, List, Optional, Type, TypeVar

import openai
from pydantic import BaseModel

from config import Config
from llm_schemas import AnswerEvaluation, FinalReport, GeneratedQuestions
from utils import ErrorHandler, get_logger

logger = get_logger("TalentScout.llm")

TSchema = TypeVar("TSchema", bound=BaseModel)

# Transient: worth retrying. The SDK's own retry layer is turned off (see
# __init__) so that this one is the only one, making the backoff explicit,
# logged and testable.
RETRYABLE_ERRORS = (
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.InternalServerError,
)

# Permanent: a bad key or a malformed request will fail identically on retry.
FATAL_ERRORS = (
    openai.AuthenticationError,
    openai.PermissionDeniedError,
    openai.BadRequestError,
    openai.NotFoundError,
)


class LLMError(RuntimeError):
    """An LLM call that could not be completed, retries included."""


class LLMHandler:
    """Handles all LLM interactions for question generation and answer evaluation"""

    def __init__(self, client: Optional[openai.OpenAI] = None):
        # Talks to the OpenAI API directly; the key comes from OPENAI_API_KEY in .env.
        # `client` is injectable so tests can exercise the retry and fallback
        # paths without network access.
        self.client = client or openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            timeout=Config.OPENAI_TIMEOUT_SECONDS,
            max_retries=0,  # retries are handled in _complete
        )

        # Default model, plus the per-task overrides (each falls back to this one)
        self.model = Config.OPENAI_MODEL
        self.model_questions = Config.OPENAI_MODEL_QUESTIONS
        self.model_evaluation = Config.OPENAI_MODEL_EVALUATION
        self.model_report = Config.OPENAI_MODEL_REPORT

        # Human-readable reason for the most recent failure, surfaced in the UI
        # alongside the degraded result.
        self.last_error: Optional[str] = None

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _complete(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: Type[TSchema],
        temperature: float,
        max_tokens: int,
    ) -> TSchema:
        """Call the model and return its reply parsed into `schema`.

        Uses OpenAI structured outputs, so the reply is guaranteed to match the
        schema and there is nothing to parse by hand. Retries transient errors
        (rate limits, timeouts, connection drops, 5xx) with exponential backoff
        and jitter; raises LLMError once the attempts are exhausted or the
        failure is one that a retry cannot fix.
        """
        attempts = Config.OPENAI_MAX_RETRIES + 1
        last_exception: Optional[Exception] = None

        for attempt in range(attempts):
            try:
                completion = self.client.chat.completions.parse(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format=schema,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                message = completion.choices[0].message

                if getattr(message, "refusal", None):
                    # A refusal is a considered answer, not a glitch; retrying
                    # the same prompt will produce the same refusal.
                    raise LLMError(f"Model refused the request: {message.refusal}")

                if message.parsed is None:
                    raise LLMError("Model returned no parseable content.")

                return message.parsed

            except FATAL_ERRORS as exc:
                logger.error("%s failed permanently: %s", schema.__name__, exc)
                raise LLMError(ErrorHandler.handle_api_error(exc, schema.__name__)) from exc

            except openai.LengthFinishReasonError as exc:
                # The reply was cut off mid-JSON. More attempts with the same
                # token budget will be cut off in the same place.
                logger.error("%s hit the max_tokens limit (%s)", schema.__name__, max_tokens)
                raise LLMError(
                    f"The model's reply was truncated at {max_tokens} tokens."
                ) from exc

            except RETRYABLE_ERRORS as exc:
                last_exception = exc
                if attempt == attempts - 1:
                    break
                delay = self._backoff_delay(attempt, exc)
                logger.warning(
                    "%s attempt %d/%d failed (%s); retrying in %.1fs",
                    schema.__name__,
                    attempt + 1,
                    attempts,
                    type(exc).__name__,
                    delay,
                )
                time.sleep(delay)

        logger.error(
            "%s failed after %d attempts: %s", schema.__name__, attempts, last_exception
        )
        raise LLMError(
            ErrorHandler.handle_api_error(last_exception, schema.__name__)
        ) from last_exception

    @staticmethod
    def _backoff_delay(attempt: int, exc: Exception) -> float:
        """Exponential backoff with jitter, honouring a Retry-After header."""
        retry_after = getattr(getattr(exc, "response", None), "headers", {})
        if retry_after:
            header = retry_after.get("retry-after")
            if header:
                try:
                    return min(float(header), Config.OPENAI_RETRY_MAX_DELAY)
                except (TypeError, ValueError):
                    pass

        delay = Config.OPENAI_RETRY_BASE_DELAY * (2 ** attempt)
        delay = min(delay, Config.OPENAI_RETRY_MAX_DELAY)
        return delay * random.uniform(0.5, 1.0)  # jitter, to spread out retries

    def _record_failure(self, exc: Exception, what: str) -> str:
        """Store and return the user-facing reason for a degraded result."""
        reason = str(exc) if isinstance(exc, LLMError) else ErrorHandler.handle_api_error(exc, what)
        self.last_error = reason
        return reason

    # ------------------------------------------------------------------
    # Question generation
    # ------------------------------------------------------------------

    def generate_technical_questions(self, candidate_data: Dict) -> List[Dict]:
        """Generate exactly 5 personalized technical questions based on candidate's tech stack.

        Each question carries a `source` of 'llm' or 'template'. If the API call
        fails entirely the canned set comes back marked `degraded`, which the UI
        turns into a visible warning.
        """
        tech_stack = candidate_data.get("tech_stack", [])
        experience = candidate_data.get("experience", 1)
        target = Config.DEFAULT_QUESTIONS

        if not tech_stack:
            logger.warning("No tech stack supplied; using fallback questions.")
            return self._get_fallback_questions("No technologies were selected.")

        try:
            parsed = self._complete(
                model=self.model_questions,
                system=(
                    "You are an expert technical interviewer. Generate exactly "
                    f"{target} relevant, practical technical questions based on the "
                    "candidate's profile."
                ),
                user=self._create_question_generation_prompt(candidate_data),
                schema=GeneratedQuestions,
                temperature=Config.LLM_TEMPERATURE_QUESTIONS,
                max_tokens=Config.LLM_MAX_TOKENS_QUESTIONS,
            )
        except LLMError as exc:
            reason = self._record_failure(exc, "question generation")
            return self._get_fallback_questions(reason)

        questions = [
            {
                "question": q.question,
                "category": q.category,
                "difficulty": q.difficulty,
                "source": "llm",
            }
            for q in parsed.questions
            if q.question.strip()
        ]

        # Top up with template questions if the model returned too few. This is
        # not a degraded result - the questions that were generated are real.
        if len(questions) < target:
            logger.info(
                "Model returned %d of %d questions; topping up from templates.",
                len(questions),
                target,
            )
            questions.extend(
                self._get_additional_questions(tech_stack, experience, target - len(questions))
            )

        self.last_error = None
        return questions[:target]

    def _create_question_generation_prompt(self, candidate_data: Dict) -> str:
        """Create a detailed prompt for question generation"""
        tech_stack = candidate_data.get("tech_stack", [])
        experience = candidate_data.get("experience", 1)
        name = candidate_data.get("name", "the candidate")
        count = Config.DEFAULT_QUESTIONS

        return f"""
Generate EXACTLY {count} technical interview questions for {name} based on their profile:

Tech Stack: {', '.join(tech_stack)}
Experience: {experience} years
Location: {candidate_data.get('location', 'Not specified')}

Requirements:
1. Generate EXACTLY {count} questions, no more, no less
2. Questions should be appropriate for {experience} years of experience
3. Focus on their tech stack: {', '.join(tech_stack)}
4. Include a mix of:
   - Conceptual understanding questions
   - Practical implementation questions
   - Problem-solving scenarios
   - Best practices questions

5. Each question should:
   - Be specific and actionable
   - Allow for detailed answers
   - Test real-world application of knowledge
   - Be appropriate for their experience level

Make the questions challenging but fair for someone with {experience} years of experience.
"""

    def _get_additional_questions(
        self, tech_stack: List[str], experience: int, needed_count: int
    ) -> List[Dict]:
        """Generate additional questions if needed to reach exactly 5"""
        additional_questions = []

        programming_questions = [
            {
                "question": "Explain the difference between synchronous and asynchronous programming. Provide examples from your experience.",
                "category": "programming",
                "difficulty": "intermediate",
            },
            {
                "question": "How do you handle errors and exceptions in your code? Describe your approach with examples.",
                "category": "programming",
                "difficulty": "intermediate",
            },
            {
                "question": "What are the key principles of clean code? How do you ensure your code is maintainable?",
                "category": "programming",
                "difficulty": "intermediate",
            },
        ]

        if any(db in tech_stack for db in Config.DATABASES):
            additional_questions.append(
                {
                    "question": "How would you optimize the performance of a slow database query? Walk through your debugging process.",
                    "category": "system_design",
                    "difficulty": "intermediate",
                }
            )

        system_design_questions = [
            {
                "question": "Describe how you would approach scaling a web application to handle increased traffic.",
                "category": "system_design",
                "difficulty": "intermediate",
            },
            {
                "question": "How do you ensure the security of web applications? What measures do you implement?",
                "category": "system_design",
                "difficulty": "intermediate",
            },
        ]

        problem_solving_questions = [
            {
                "question": "Describe a challenging technical problem you solved recently. What was your approach?",
                "category": "problem_solving",
                "difficulty": "intermediate",
            },
            {
                "question": "How do you stay updated with new technologies and industry trends?",
                "category": "problem_solving",
                "difficulty": "beginner",
            },
        ]

        all_additional = (
            programming_questions
            + additional_questions
            + system_design_questions
            + problem_solving_questions
        )

        return [dict(q, source="template") for q in all_additional[:needed_count]]

    def _get_fallback_questions(self, reason: str) -> List[Dict]:
        """Return exactly 5 generic questions when personalised generation fails."""
        fallbacks = [
            {
                "question": "Describe a challenging technical project you worked on. What problems did you face and how did you solve them?",
                "category": "problem_solving",
                "difficulty": "intermediate",
            },
            {
                "question": "How do you ensure code quality and maintainability in your projects?",
                "category": "programming",
                "difficulty": "intermediate",
            },
            {
                "question": "Explain your approach to learning new technologies. Give an example of a recent technology you learned.",
                "category": "problem_solving",
                "difficulty": "beginner",
            },
            {
                "question": "How would you approach debugging a performance issue in a web application?",
                "category": "problem_solving",
                "difficulty": "intermediate",
            },
            {
                "question": "What are the key considerations when designing a REST API? How do you ensure it is scalable and maintainable?",
                "category": "system_design",
                "difficulty": "intermediate",
            },
        ]
        return [
            dict(q, source="fallback", degraded=True, degraded_reason=reason)
            for q in fallbacks
        ]

    # ------------------------------------------------------------------
    # Answer evaluation
    # ------------------------------------------------------------------

    def evaluate_answer(self, question: Dict, answer: str, candidate_data: Dict) -> Dict:
        """Score one answer. Returns a degraded placeholder if the call fails."""
        try:
            parsed = self._complete(
                model=self.model_evaluation,
                system=(
                    "You are an expert technical interviewer. Evaluate answers "
                    "objectively and provide constructive feedback."
                ),
                user=self._create_evaluation_prompt(question, answer, candidate_data),
                schema=AnswerEvaluation,
                temperature=Config.LLM_TEMPERATURE_EVALUATION,
                max_tokens=Config.LLM_MAX_TOKENS_EVALUATION,
            )
        except LLMError as exc:
            reason = self._record_failure(exc, "answer evaluation")
            return self._get_fallback_evaluation(reason)

        self.last_error = None
        return {
            "score": parsed.score,
            "feedback": parsed.feedback,
            "degraded": False,
        }

    def _create_evaluation_prompt(self, question: Dict, answer: str, candidate_data: Dict) -> str:
        """Create prompt for answer evaluation"""
        experience = candidate_data.get("experience", 1)
        tech_stack = candidate_data.get("tech_stack", [])

        return f"""
Evaluate this technical interview answer:

Question: {question['question']}
Question Category: {question.get('category', 'general')}
Question Difficulty: {question.get('difficulty', 'intermediate')}

Candidate's Answer: {answer}

Candidate Profile:
- Experience: {experience} years
- Tech Stack: {', '.join(tech_stack)}

Score the answer from {Config.MIN_SCORE} to {Config.MAX_SCORE} and explain the score
in your feedback: what the candidate did well, what is missing, what to improve, and
whether the answer demonstrates knowledge appropriate to their experience level.

Consider:
- Technical accuracy
- Depth of explanation
- Practical examples
- Communication clarity
- Appropriate complexity for experience level
"""

    @staticmethod
    def _get_fallback_evaluation(reason: str) -> Dict:
        """Return a neutral, clearly-marked evaluation if scoring failed."""
        return {
            "score": 5,
            "feedback": (
                "This answer could not be scored automatically, so it has been recorded "
                "with a neutral placeholder score. It needs a human review."
            ),
            "degraded": True,
            "degraded_reason": reason,
        }

    # ------------------------------------------------------------------
    # Final report
    # ------------------------------------------------------------------

    def generate_final_report(
        self, candidate_data: Dict, answers: List[Dict], evaluations: List[Dict]
    ) -> Dict:
        """Generate the final comprehensive evaluation report."""
        if not evaluations:
            return self._apply_completion_adjustment(self._get_empty_report(), 0)

        try:
            parsed = self._complete(
                model=self.model_report,
                system=(
                    "You are an expert technical recruiter. Generate comprehensive, "
                    "professional evaluation reports. Judge only the answers given: "
                    "never infer anything about the candidate from their name or "
                    "location, and refer to them by name or as 'they'."
                ),
                user=self._create_final_report_prompt(candidate_data, answers, evaluations),
                schema=FinalReport,
                temperature=Config.LLM_TEMPERATURE_REPORT,
                max_tokens=Config.LLM_MAX_TOKENS_REPORT,
            )
        except LLMError as exc:
            reason = self._record_failure(exc, "final report")
            report = self._get_fallback_report(evaluations, reason)
        else:
            self.last_error = None
            report = {
                "overall_score": round(parsed.overall_score, 1),
                "recommendation": parsed.recommendation,
                "detailed_feedback": parsed.analysis,
                "degraded": False,
            }

        # A report built on placeholder scores is not trustworthy either, even
        # if this particular call succeeded.
        if any(e.get("degraded") for e in evaluations):
            report["degraded"] = True
            report.setdefault(
                "degraded_reason",
                "One or more answers could not be scored, so the overall score is unreliable.",
            )

        return self._apply_completion_adjustment(report, len(answers))

    @staticmethod
    def _apply_completion_adjustment(report: Dict, questions_answered: int) -> Dict:
        """Apply the fixed early-completion penalty from Config.

        The model scores answer quality only; the completion adjustment happens
        here instead, so it is deterministic, identical for every candidate and
        visible in the report rather than buried in the model's judgement.
        """
        performance_score = report['overall_score']
        adjusted = Config.calculate_completion_adjusted_score(
            performance_score, questions_answered
        )
        report.update({
            'performance_score': round(performance_score, 1),
            'overall_score': adjusted,
            'completion_penalty_factor': Config.EARLY_COMPLETION_PENALTY.get(
                questions_answered, 1.0
            ),
            'questions_answered': questions_answered,
            'completion_status': Config.get_completion_status(questions_answered),
        })
        return report

    def _create_final_report_prompt(
        self, candidate_data: Dict, answers: List[Dict], evaluations: List[Dict]
    ) -> str:
        """Create prompt for final report generation"""
        avg_score = sum(e["score"] for e in evaluations) / len(evaluations)
        total_possible_questions = Config.DEFAULT_QUESTIONS
        questions_answered = len(answers)

        prompt = f"""
Generate a comprehensive technical assessment report:

CANDIDATE PROFILE:
Name: {candidate_data.get('name', 'Candidate')}
Experience: {candidate_data.get('experience', 0)} years
Tech Stack: {', '.join(candidate_data.get('tech_stack', []))}
Location: {candidate_data.get('location', 'Not specified')}

ASSESSMENT RESULTS:
Questions Answered: {questions_answered} out of {total_possible_questions} total questions
Average Score: {avg_score:.1f}/10
Test Status: {"Completed Early" if questions_answered < total_possible_questions else "Full Assessment Completed"}

INDIVIDUAL QUESTION PERFORMANCE:
"""

        for i, (answer, evaluation) in enumerate(zip(answers, evaluations)):
            prompt += f"""
Q{i + 1} - Score: {evaluation['score']}/10
Category: {answer.get('category', 'General')}
Question: {answer['question']}
Answer Length: {len(answer['answer'])} characters
"""

        prompt += f"""
The overall score must reflect ONLY the technical quality of the answers actually
given. A separate fixed completion adjustment handles partial assessments, so
penalising incompleteness here would double-count it.

The candidate answered {questions_answered} out of {total_possible_questions} possible questions.
{"You may comment in your analysis on the limited evidence this gives you." if questions_answered < total_possible_questions else ""}
"""
        return prompt

    @staticmethod
    def _get_empty_report() -> Dict:
        return {
            "overall_score": 0,
            "recommendation": "Incomplete",
            "detailed_feedback": "Assessment was not completed. No questions were answered.",
            "degraded": False,
        }

    @staticmethod
    def _get_fallback_report(evaluations: List[Dict], reason: str) -> Dict:
        """Build a report from the per-answer scores when the LLM call fails."""
        avg_score = sum(e["score"] for e in evaluations) / len(evaluations)
        questions_answered = len(evaluations)

        if questions_answered < 3:
            recommendation = "Maybe" if avg_score >= 6 else "No Hire"
            feedback = (
                f"Average score of {avg_score:.1f}/10 across {questions_answered} "
                "question(s), but the assessment is incomplete."
            )
        elif avg_score >= 7:
            recommendation = "Hire" if questions_answered >= 4 else "Maybe"
            feedback = (
                f"Good technical performance: {avg_score:.1f}/10 across "
                f"{questions_answered} questions."
            )
        elif avg_score >= 5:
            recommendation = "Maybe"
            feedback = (
                f"Average performance ({avg_score:.1f}/10) across {questions_answered} "
                "questions; some areas need improvement."
            )
        else:
            recommendation = "No Hire"
            feedback = (
                f"Below expectations ({avg_score:.1f}/10) across {questions_answered} "
                "questions."
            )

        return {
            "overall_score": round(avg_score, 1),
            "recommendation": recommendation,
            "detailed_feedback": (
                f"{feedback}\n\nThis summary was produced from the individual question "
                "scores because the narrative report could not be generated."
            ),
            "degraded": True,
            "degraded_reason": reason,
        }
