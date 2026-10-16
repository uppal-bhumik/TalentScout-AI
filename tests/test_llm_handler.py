"""Tests for the LLM layer: structured parsing, retries and degraded fallbacks.

The OpenAI client is always a stand-in, so nothing here makes a network call.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import openai
import pytest

from config import Config
from llm_handler import LLMError, LLMHandler
from llm_schemas import AnswerEvaluation, FinalReport, GeneratedQuestion, GeneratedQuestions


def parsed_reply(payload):
    """Shape a fake completion the way the SDK's parse helper returns one."""
    message = SimpleNamespace(parsed=payload, refusal=None, content=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def refusal_reply(reason="I can't help with that."):
    message = SimpleNamespace(parsed=None, refusal=reason, content=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def questions_payload(count=Config.DEFAULT_QUESTIONS):
    return GeneratedQuestions(
        questions=[
            GeneratedQuestion(
                question=f"Question {i + 1} about Python?",
                category="programming",
                difficulty="intermediate",
            )
            for i in range(count)
        ]
    )


@pytest.fixture
def client():
    """A mock OpenAI client whose parse call is configured per test."""
    mock = MagicMock()
    mock.chat.completions.parse.return_value = parsed_reply(questions_payload())
    return mock


@pytest.fixture
def handler(client):
    return LLMHandler(client=client)


def auth_error(request):
    return openai.AuthenticationError(
        "Incorrect API key provided",
        response=httpx.Response(401, request=request),
        body=None,
    )


def rate_limit_error(request, retry_after=None):
    headers = {"retry-after": retry_after} if retry_after else {}
    return openai.RateLimitError(
        "Rate limit reached",
        response=httpx.Response(429, request=request, headers=headers),
        body=None,
    )


class TestQuestionGeneration:
    def test_returns_the_parsed_questions(self, handler, client, candidate):
        questions = handler.generate_technical_questions(candidate)

        assert len(questions) == Config.DEFAULT_QUESTIONS
        assert all(q["source"] == "llm" for q in questions)
        assert not any(q.get("degraded") for q in questions)
        assert questions[0]["question"] == "Question 1 about Python?"
        assert handler.last_error is None

    def test_asks_for_the_schema(self, handler, client, candidate):
        """Structured outputs, not prose - there is no parsing left to go wrong."""
        handler.generate_technical_questions(candidate)
        kwargs = client.chat.completions.parse.call_args.kwargs
        assert kwargs["response_format"] is GeneratedQuestions
        assert kwargs["model"] == Config.OPENAI_MODEL_QUESTIONS

    def test_tops_up_a_short_set_without_degrading(self, handler, client, candidate):
        client.chat.completions.parse.return_value = parsed_reply(questions_payload(count=2))

        questions = handler.generate_technical_questions(candidate)

        assert len(questions) == Config.DEFAULT_QUESTIONS
        assert [q["source"] for q in questions[:2]] == ["llm", "llm"]
        assert all(q["source"] == "template" for q in questions[2:])
        # Real questions were generated, so this is not a degraded result.
        assert not any(q.get("degraded") for q in questions)

    def test_falls_back_when_the_candidate_has_no_tech_stack(self, handler, client, candidate):
        candidate["tech_stack"] = []

        questions = handler.generate_technical_questions(candidate)

        assert len(questions) == Config.DEFAULT_QUESTIONS
        assert all(q["degraded"] for q in questions)
        client.chat.completions.parse.assert_not_called()

    def test_falls_back_and_flags_degraded_on_api_failure(
        self, handler, client, candidate, http_request, no_sleep
    ):
        client.chat.completions.parse.side_effect = auth_error(http_request)

        questions = handler.generate_technical_questions(candidate)

        assert len(questions) == Config.DEFAULT_QUESTIONS
        assert all(q["degraded"] for q in questions)
        assert all(q["source"] == "fallback" for q in questions)
        assert "key" in questions[0]["degraded_reason"].lower()
        assert handler.last_error is not None

    def test_a_refusal_degrades_rather_than_crashing(self, handler, client, candidate, no_sleep):
        client.chat.completions.parse.return_value = refusal_reply()

        questions = handler.generate_technical_questions(candidate)

        assert all(q["degraded"] for q in questions)
        assert "refused" in questions[0]["degraded_reason"].lower()


class TestRetries:
    def test_retries_a_rate_limit_then_succeeds(
        self, handler, client, candidate, http_request, no_sleep
    ):
        client.chat.completions.parse.side_effect = [
            rate_limit_error(http_request),
            rate_limit_error(http_request),
            parsed_reply(questions_payload()),
        ]

        questions = handler.generate_technical_questions(candidate)

        assert client.chat.completions.parse.call_count == 3
        assert not any(q.get("degraded") for q in questions)
        assert len(no_sleep) == 2  # one backoff before each retry

    def test_backoff_grows_between_attempts(
        self, handler, client, candidate, http_request, no_sleep
    ):
        client.chat.completions.parse.side_effect = openai.APITimeoutError(request=http_request)

        handler.generate_technical_questions(candidate)

        assert len(no_sleep) == Config.OPENAI_MAX_RETRIES
        assert no_sleep == sorted(no_sleep)  # jittered, but non-decreasing
        assert all(d <= Config.OPENAI_RETRY_MAX_DELAY for d in no_sleep)

    def test_gives_up_after_the_configured_number_of_attempts(
        self, handler, client, candidate, http_request, no_sleep
    ):
        client.chat.completions.parse.side_effect = openai.APIConnectionError(
            request=http_request
        )

        handler.generate_technical_questions(candidate)

        assert client.chat.completions.parse.call_count == Config.OPENAI_MAX_RETRIES + 1

    def test_honours_a_retry_after_header(
        self, handler, client, candidate, http_request, no_sleep
    ):
        client.chat.completions.parse.side_effect = [
            rate_limit_error(http_request, retry_after="7"),
            parsed_reply(questions_payload()),
        ]

        handler.generate_technical_questions(candidate)

        assert no_sleep == [7.0]

    def test_does_not_retry_a_permanent_failure(
        self, handler, client, candidate, http_request, no_sleep
    ):
        """A bad key fails identically on every attempt; retrying only stalls the UI."""
        client.chat.completions.parse.side_effect = auth_error(http_request)

        handler.generate_technical_questions(candidate)

        assert client.chat.completions.parse.call_count == 1
        assert no_sleep == []

    def test_does_not_retry_a_truncated_reply(
        self, handler, client, candidate, http_request, no_sleep
    ):
        client.chat.completions.parse.side_effect = openai.LengthFinishReasonError(
            completion=MagicMock()
        )

        questions = handler.generate_technical_questions(candidate)

        assert client.chat.completions.parse.call_count == 1
        assert all(q["degraded"] for q in questions)
        assert "truncated" in questions[0]["degraded_reason"].lower()

    def test_complete_raises_rather_than_returning_none(
        self, handler, client, http_request, no_sleep
    ):
        client.chat.completions.parse.side_effect = auth_error(http_request)

        with pytest.raises(LLMError):
            handler._complete(
                model="gpt-4o-mini",
                system="s",
                user="u",
                schema=AnswerEvaluation,
                temperature=0.3,
                max_tokens=100,
            )


class TestAnswerEvaluation:
    def test_returns_the_parsed_score_and_feedback(self, handler, client, candidate):
        client.chat.completions.parse.return_value = parsed_reply(
            AnswerEvaluation(score=8, feedback="Specific and well reasoned.")
        )

        evaluation = handler.evaluate_answer(
            {"question": "Explain the GIL", "category": "programming"},
            "The GIL serialises bytecode execution per interpreter.",
            candidate,
        )

        assert evaluation == {
            "score": 8,
            "feedback": "Specific and well reasoned.",
            "degraded": False,
        }

    def test_degrades_to_a_flagged_placeholder(
        self, handler, client, candidate, http_request, no_sleep
    ):
        """The point of the flag: a failed call must not look like a real 5/10."""
        client.chat.completions.parse.side_effect = auth_error(http_request)

        evaluation = handler.evaluate_answer({"question": "q"}, "an answer", candidate)

        assert evaluation["score"] == 5
        assert evaluation["degraded"] is True
        assert evaluation["degraded_reason"]
        assert "human review" in evaluation["feedback"]


class TestFinalReport:
    def _report_payload(self, score=8.0, recommendation="Hire"):
        return FinalReport(
            overall_score=score,
            recommendation=recommendation,
            analysis="Strong on fundamentals.",
        )

    def test_uses_the_parsed_score_and_recommendation(self, handler, client, candidate):
        client.chat.completions.parse.return_value = parsed_reply(self._report_payload())
        answers = [{"question": "q", "answer": "a"}] * 5
        evaluations = [{"score": 8, "feedback": "good", "degraded": False}] * 5

        report = handler.generate_final_report(candidate, answers, evaluations)

        assert report["recommendation"] == "Hire"
        assert report["overall_score"] == 8.0
        assert report["degraded"] is False
        assert report["detailed_feedback"] == "Strong on fundamentals."

    def test_applies_the_completion_penalty_and_shows_the_arithmetic(
        self, handler, client, candidate
    ):
        client.chat.completions.parse.return_value = parsed_reply(self._report_payload())
        answers = [{"question": "q", "answer": "a"}]
        evaluations = [{"score": 8, "feedback": "good", "degraded": False}]

        report = handler.generate_final_report(candidate, answers, evaluations)

        assert report["performance_score"] == 8.0      # quality of the one answer
        assert report["completion_penalty_factor"] == 0.8
        assert report["overall_score"] == 6.4          # 8.0 * 0.8
        assert report["questions_answered"] == 1
        assert "1" in report["completion_status"]

    def test_degrades_when_any_answer_was_not_scored(self, handler, client, candidate):
        """A report built on a placeholder score is not trustworthy either."""
        client.chat.completions.parse.return_value = parsed_reply(self._report_payload())
        answers = [{"question": "q", "answer": "a"}] * 2
        evaluations = [
            {"score": 8, "feedback": "good", "degraded": False},
            {"score": 5, "feedback": "placeholder", "degraded": True},
        ]

        report = handler.generate_final_report(candidate, answers, evaluations)

        assert report["degraded"] is True
        assert report["degraded_reason"]

    def test_falls_back_to_the_mean_of_the_scores(
        self, handler, client, candidate, http_request, no_sleep
    ):
        client.chat.completions.parse.side_effect = auth_error(http_request)
        answers = [{"question": "q", "answer": "a"}] * 4
        evaluations = [{"score": s, "feedback": "f", "degraded": False} for s in (9, 8, 7, 8)]

        report = handler.generate_final_report(candidate, answers, evaluations)

        assert report["degraded"] is True
        assert report["performance_score"] == 8.0      # mean of 9, 8, 7, 8
        assert report["overall_score"] == 7.8          # 8.0 * 0.98 for 4 of 5
        assert report["recommendation"] == "Hire"

    def test_an_empty_assessment_is_reported_as_incomplete(self, handler, client, candidate):
        report = handler.generate_final_report(candidate, [], [])

        assert report["recommendation"] == "Incomplete"
        assert report["overall_score"] == 0
        client.chat.completions.parse.assert_not_called()

    @pytest.mark.parametrize(
        ("scores", "expected"),
        [
            ([9, 9, 9, 9, 9], "Hire"),
            ([6, 6, 6, 5, 5], "Maybe"),
            ([2, 3, 2, 1, 2], "No Hire"),
        ],
    )
    def test_fallback_recommendation_tracks_performance(
        self, handler, client, candidate, http_request, no_sleep, scores, expected
    ):
        client.chat.completions.parse.side_effect = auth_error(http_request)
        answers = [{"question": "q", "answer": "a"}] * len(scores)
        evaluations = [{"score": s, "feedback": "f", "degraded": False} for s in scores]

        report = handler.generate_final_report(candidate, answers, evaluations)

        assert report["recommendation"] == expected
