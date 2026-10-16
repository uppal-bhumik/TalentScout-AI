"""Tests for the shared helpers: error messages, exports and small utilities."""

import csv
from io import StringIO

import httpx
import openai
import pytest

from config import Config
from utils import (
    ErrorHandler,
    ReportGenerator,
    calculate_assessment_metrics,
    sanitize_filename,
    truncate_text,
)

CANDIDATE = {
    "name": "Ada Lovelace",
    "email": "ada@analytical.example",
    "phone": "+442071838750",
    "experience": 5,
    "location": "London, United Kingdom",
    "tech_stack": ["Python", "PostgreSQL"],
}

ANSWERS = [{"question": "What is the GIL?", "answer": "A mutex.", "category": "programming"}]
EVALUATIONS = [{"score": 8, "feedback": "Clear.", "degraded": False}]
REPORT = {
    "overall_score": 6.4,
    "performance_score": 8.0,
    "completion_penalty_factor": 0.8,
    "completion_status": "Partial Assessment (1/5 questions)",
    "recommendation": "Maybe",
    "detailed_feedback": "Promising.",
    "degraded": False,
}


class TestErrorHandler:
    def test_rate_limit_message_is_actionable(self):
        error = openai.RateLimitError(
            "Rate limit reached",
            response=httpx.Response(429, request=httpx.Request("POST", "https://x")),
            body=None,
        )
        assert "rate limit" in ErrorHandler.handle_api_error(error).lower()

    def test_auth_message_points_at_the_key(self):
        error = openai.AuthenticationError(
            "Incorrect API key",
            response=httpx.Response(401, request=httpx.Request("POST", "https://x")),
            body=None,
        )
        assert "OPENAI_API_KEY" in ErrorHandler.handle_api_error(error)

    def test_timeout_message(self):
        error = openai.APITimeoutError(request=httpx.Request("POST", "https://x"))
        assert "timed out" in ErrorHandler.handle_api_error(error).lower()

    def test_unknown_error_still_names_the_context(self):
        message = ErrorHandler.handle_api_error(ValueError("odd"), "question generation")
        assert "question generation" in message

    def test_handles_no_exception_at_all(self):
        assert "unknown" in ErrorHandler.handle_api_error(None, "scoring").lower()


class TestHtmlReport:
    def test_includes_the_candidate_and_the_score(self):
        html = ReportGenerator.generate_html_report(CANDIDATE, ANSWERS, EVALUATIONS, REPORT)

        assert "Ada Lovelace" in html
        assert "6.4/10" in html
        assert "Maybe" in html
        assert "What is the GIL?" in html
        assert html.lstrip().startswith("<!DOCTYPE html>")

    def test_shows_the_completion_arithmetic(self):
        html = ReportGenerator.generate_html_report(CANDIDATE, ANSWERS, EVALUATIONS, REPORT)
        assert "8.0/10 on the answers given" in html
        assert "0.8 completion factor" in html

    def test_hides_the_arithmetic_when_there_is_no_penalty(self):
        report = dict(REPORT, completion_penalty_factor=1.0)
        html = ReportGenerator.generate_html_report(CANDIDATE, ANSWERS, EVALUATIONS, report)
        assert "completion factor" not in html

    def test_warns_when_the_report_is_degraded(self):
        report = dict(REPORT, degraded=True, degraded_reason="The API timed out.")
        html = ReportGenerator.generate_html_report(CANDIDATE, ANSWERS, EVALUATIONS, report)

        assert "degraded mode" in html
        assert "The API timed out." in html
        assert "human review" in html

    def test_marks_an_unscored_answer(self):
        evaluations = [{"score": 5, "feedback": "placeholder", "degraded": True}]
        html = ReportGenerator.generate_html_report(CANDIDATE, ANSWERS, evaluations, REPORT)
        assert "not scored" in html

    def test_survives_an_empty_assessment(self):
        html = ReportGenerator.generate_html_report(CANDIDATE, [], [], REPORT)
        assert "Ada Lovelace" in html


class TestCsvSummary:
    def test_is_parseable_and_carries_the_average(self):
        csv_text = ReportGenerator.generate_csv_summary(
            CANDIDATE, [{"score": 8}, {"score": 6}]
        )
        rows = dict(row for row in csv.reader(StringIO(csv_text)) if len(row) == 2)

        assert rows["Name"] == "Ada Lovelace"
        assert rows["Average Score"] == "7.0/10"
        assert rows["Total Questions"] == "2"

    def test_omits_the_average_with_no_evaluations(self):
        csv_text = ReportGenerator.generate_csv_summary(CANDIDATE, [])
        assert "Average Score" not in csv_text


class TestMetrics:
    def test_summarises_a_set_of_scores(self):
        metrics = calculate_assessment_metrics(
            [{"score": s} for s in (9, 8, 4, 6)]
        )

        assert metrics["total_questions"] == 4
        assert metrics["average_score"] == pytest.approx(6.75)
        assert metrics["highest_score"] == 9
        assert metrics["lowest_score"] == 4
        assert metrics["passing_questions"] == 3  # >= Config.PASSING_SCORE (6)
        assert metrics["pass_rate"] == pytest.approx(75.0)

    def test_pass_threshold_follows_config(self, monkeypatch):
        monkeypatch.setattr(Config, "PASSING_SCORE", 9)
        metrics = calculate_assessment_metrics([{"score": s} for s in (9, 8, 4, 6)])
        assert metrics["passing_questions"] == 1

    def test_no_evaluations_gives_an_empty_dict(self):
        assert calculate_assessment_metrics([]) == {}


class TestSmallHelpers:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Ada Lovelace", "Ada_Lovelace"),
            ("../../etc/passwd", ".._.._etc_passwd"),
            ('bad:name*here?', "bad_name_here"),
            ("", "unnamed"),
            ("___", "unnamed"),
        ],
    )
    def test_sanitize_filename(self, raw, expected):
        assert sanitize_filename(raw) == expected

    def test_truncate_text_adds_an_ellipsis_only_when_needed(self):
        assert truncate_text("short", 10) == "short"
        assert truncate_text("a" * 20, 10) == "a" * 10 + "..."
        assert truncate_text("", 10) == ""
        assert truncate_text(None, 10) == ""
