"""Tests for configuration validation and the scoring arithmetic."""

import pytest

from config import Config


class TestValidateConfig:
    def test_passes_with_a_plausible_key(self, monkeypatch):
        monkeypatch.setattr(Config, "OPENAI_API_KEY", "sk-proj-abc123")
        assert Config.validate_config() is True

    def test_rejects_a_missing_key(self, monkeypatch):
        monkeypatch.setattr(Config, "OPENAI_API_KEY", None)
        with pytest.raises(ValueError, match="OPENAI_API_KEY is missing"):
            Config.validate_config()

    def test_rejects_an_openrouter_key(self, monkeypatch):
        """The app talks to OpenAI directly; an sk-or- key would 401 on every call."""
        monkeypatch.setattr(Config, "OPENAI_API_KEY", "sk-or-v1-abc123")
        with pytest.raises(ValueError, match="OpenRouter"):
            Config.validate_config()

    def test_reports_every_problem_at_once(self, monkeypatch):
        monkeypatch.setattr(Config, "OPENAI_API_KEY", None)
        monkeypatch.setattr(Config, "PASSING_SCORE", 99)
        monkeypatch.setattr(Config, "OPENAI_MAX_RETRIES", -1)

        with pytest.raises(ValueError) as exc_info:
            Config.validate_config()

        message = str(exc_info.value)
        assert "OPENAI_API_KEY" in message
        assert "PASSING_SCORE" in message
        assert "OPENAI_MAX_RETRIES" in message

    @pytest.mark.parametrize(
        ("attribute", "value", "expected"),
        [
            ("MIN_QUESTIONS", 0, "MIN_QUESTIONS"),
            ("DEFAULT_QUESTIONS", 99, "DEFAULT_QUESTIONS"),
            ("MIN_SCORE", 10, "MIN_SCORE"),
            ("QUESTION_TIMEOUT_SECONDS", 0, "QUESTION_TIMEOUT_SECONDS"),
            ("OPENAI_TIMEOUT_SECONDS", 0, "OPENAI_TIMEOUT_SECONDS"),
            ("OPENAI_RETRY_BASE_DELAY", 0, "OPENAI_RETRY_BASE_DELAY"),
            ("OPENAI_RETRY_MAX_DELAY", 0.1, "OPENAI_RETRY_MAX_DELAY"),
            ("DATABASE_URL", "", "DATABASE_URL"),
            ("EARLY_COMPLETION_PENALTY", {1: 1.5}, "EARLY_COMPLETION_PENALTY"),
        ],
    )
    def test_rejects_each_bad_setting(self, monkeypatch, attribute, value, expected):
        monkeypatch.setattr(Config, "OPENAI_API_KEY", "sk-proj-abc123")
        monkeypatch.setattr(Config, attribute, value)
        with pytest.raises(ValueError, match=expected):
            Config.validate_config()


class TestCompletionAdjustedScore:
    @pytest.mark.parametrize(
        ("score", "answered", "expected"),
        [
            (8.0, 5, 8.0),    # full assessment: no penalty
            (8.0, 4, 7.8),    # 8.0 * 0.98
            (8.0, 3, 7.6),    # 8.0 * 0.95
            (8.0, 2, 7.2),    # 8.0 * 0.90
            (8.0, 1, 6.4),    # 8.0 * 0.80
        ],
    )
    def test_applies_the_configured_penalty(self, score, answered, expected):
        assert Config.calculate_completion_adjusted_score(score, answered) == expected

    def test_unknown_question_count_is_left_alone(self):
        """A count with no configured penalty must not be silently zeroed."""
        assert Config.calculate_completion_adjusted_score(8.0, 9) == 8.0

    def test_a_penalty_never_raises_a_score(self):
        for answered in Config.EARLY_COMPLETION_PENALTY:
            assert Config.calculate_completion_adjusted_score(10.0, answered) <= 10.0

    def test_result_is_rounded_to_one_decimal(self):
        assert Config.calculate_completion_adjusted_score(7.77, 3) == 7.4


class TestCompletionStatus:
    def test_full_assessment(self):
        status = Config.get_completion_status(Config.MAX_QUESTIONS)
        assert status == "Full Assessment Completed"

    def test_partial_assessment_names_the_counts(self):
        status = Config.get_completion_status(2)
        assert "2" in status and str(Config.MAX_QUESTIONS) in status

    def test_nothing_answered(self):
        assert Config.get_completion_status(0) == "Assessment Incomplete"


class TestTechnologyLists:
    def test_categories_cover_the_flat_list(self):
        from itertools import chain

        categorised = list(chain.from_iterable(Config.get_technology_categories().values()))
        assert sorted(categorised) == sorted(Config.get_all_technologies())

    def test_no_duplicates_across_categories(self):
        technologies = Config.get_all_technologies()
        assert len(technologies) == len(set(technologies))
