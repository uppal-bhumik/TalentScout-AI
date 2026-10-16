"""Tests for the pure input-validation functions."""

import pytest

from config import Config


class TestName:
    @pytest.mark.parametrize(
        "name",
        ["Ada Lovelace", "Jean-Luc Picard", "O'Brien", "Dr. Who", "Li Wei"],
    )
    def test_accepts_real_names(self, validator, name):
        assert validator.validate_name(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "   ",
            "A",                      # under MIN_NAME_LENGTH
            "x" * 51,                 # over MAX_NAME_LENGTH
            "Ada3",                   # digits
            "Ada <script>",           # HTML
            "Ada (Lovelace)",         # brackets
            "-Ada",                   # leading separator
            "Ada.",                   # trailing separator
        ],
    )
    def test_rejects_bad_names(self, validator, name):
        assert validator.validate_name(name) is False

    def test_length_limits_follow_config(self, validator):
        assert validator.validate_name("x" * Config.MAX_NAME_LENGTH) is True
        assert validator.validate_name("x" * (Config.MAX_NAME_LENGTH + 1)) is False

    def test_rejects_blocked_words(self, validator):
        # A deliberate product decision: names containing 'test' or 'admin'
        # are treated as junk input.
        assert validator.validate_name("Test User") is False
        assert validator.validate_name("Admin") is False


class TestEmail:
    @pytest.mark.parametrize(
        "email",
        ["ada@analytical.io", "first.last+tag@sub.domain.org", "A.B@Example.CO"],
    )
    def test_accepts_valid_addresses(self, validator, email, accept_email_deliverability):
        assert validator.validate_email(email) is True

    @pytest.mark.parametrize(
        "email",
        ["", "   ", "no-at-sign", "ada@", "@analytical.io", "ada@nodot", "ada ada@x.io"],
    )
    def test_rejects_malformed_addresses(self, validator, email, accept_email_deliverability):
        assert validator.validate_email(email) is False

    def test_rejects_overlong_address(self, validator, accept_email_deliverability):
        local = "a" * Config.MAX_EMAIL_LENGTH
        assert validator.validate_email(f"{local}@analytical.io") is False

    def test_rejects_undeliverable_domain(self, validator, monkeypatch):
        """A domain email-validator rejects is rejected, not waved through."""
        from email_validator import EmailNotValidError

        def reject(email):
            raise EmailNotValidError("domain does not accept mail")

        monkeypatch.setattr("data_validator.validate_email", reject)
        assert validator.validate_email("ada@no-such-domain.invalid") is False

    def test_falls_back_to_regex_when_validator_breaks(self, validator, monkeypatch):
        """An unexpected library error must not reject a well-formed address."""
        def explode(email):
            raise RuntimeError("DNS resolver unavailable")

        monkeypatch.setattr("data_validator.validate_email", explode)
        assert validator.validate_email("ada@analytical.io") is True
        assert validator.validate_email("ada@@analytical.io") is False


class TestPhone:
    @pytest.mark.parametrize("phone", ["+44 20 7183 8750", "+919876543210"])
    def test_accepts_valid_numbers(self, validator, phone):
        assert validator.validate_phone(phone) is True

    @pytest.mark.parametrize(
        "phone",
        ["", "   ", "12345", "not a phone", "+1 (555) 010-1234"],
    )
    def test_rejects_invalid_numbers(self, validator, phone):
        # Note the last case: parentheses hit the injection-character filter
        # before the number itself is ever parsed.
        assert validator.validate_phone(phone) is False

    def test_rejects_overlong_input(self, validator):
        assert validator.validate_phone("+" + "1" * Config.MAX_PHONE_LENGTH) is False


class TestExperience:
    @pytest.mark.parametrize("value", [0, 0.5, 5, "7", 50])
    def test_accepts_plausible_values(self, validator, value):
        assert validator.validate_experience(value) is True

    @pytest.mark.parametrize("value", [-1, 51, "", None, "five", [3]])
    def test_rejects_implausible_values(self, validator, value):
        assert validator.validate_experience(value) is False


class TestLocation:
    @pytest.mark.parametrize("location", ["Delhi, India", "St. John's", "Ann Arbor"])
    def test_accepts_valid_locations(self, validator, location):
        assert validator.validate_location(location) is True

    @pytest.mark.parametrize("location", ["", "D", "x" * 101, "Delhi 110001", "<b>Delhi</b>"])
    def test_rejects_invalid_locations(self, validator, location):
        assert validator.validate_location(location) is False


class TestTechStack:
    def test_accepts_a_normal_stack(self, validator):
        assert validator.validate_tech_stack(["Python", "React", "C++", "Node.js", "C#"]) is True

    def test_rejects_empty_or_wrong_type(self, validator):
        assert validator.validate_tech_stack([]) is False
        assert validator.validate_tech_stack("Python") is False
        assert validator.validate_tech_stack(None) is False

    def test_rejects_more_items_than_config_allows(self, validator):
        too_many = ["Python"] * (Config.MAX_TECH_STACK_ITEMS + 1)
        assert validator.validate_tech_stack(too_many) is False
        assert validator.validate_tech_stack(["Python"] * Config.MAX_TECH_STACK_ITEMS) is True

    def test_rejects_a_stack_containing_junk(self, validator):
        assert validator.validate_tech_stack(["Python", "<script>alert(1)</script>"]) is False


class TestAnswer:
    def test_accepts_a_substantial_answer(self, validator):
        assert validator.validate_answer("I would use an index on the join column.") is True

    def test_rejects_too_short(self, validator):
        assert validator.validate_answer("x" * (Config.MIN_ANSWER_LENGTH - 1)) is False

    def test_rejects_too_long(self, validator):
        assert validator.validate_answer("x" * (Config.MAX_ANSWER_LENGTH + 1)) is False

    def test_rejects_script_injection(self, validator):
        assert validator.validate_answer("Sure: <script>steal()</script> that's how.") is False

    def test_allows_technical_punctuation(self, validator):
        """Code-ish answers must survive the filter that names do not."""
        answer = "Use list(map(f, xs)) or {k: v for k, v in items} - both are fine."
        assert validator.validate_answer(answer) is True


class TestSanitizeInput:
    def test_strips_whitespace_and_null_bytes(self, validator):
        assert validator.sanitize_input("  Ada\x00  ") == "Ada"

    def test_caps_length(self, validator):
        assert len(validator.sanitize_input("x" * 5000)) == 1000

    def test_handles_empty(self, validator):
        assert validator.sanitize_input("") == ""
        assert validator.sanitize_input(None) == ""


class TestProfileValidation:
    def test_complete_profile_passes(self, validator, candidate, accept_email_deliverability):
        assert validator.is_valid_candidate_profile(candidate) is True

    def test_missing_field_fails(self, validator, candidate, accept_email_deliverability):
        del candidate["location"]
        assert validator.is_valid_candidate_profile(candidate) is False

    def test_errors_name_each_bad_field(self, validator, accept_email_deliverability):
        errors = validator.get_validation_errors(
            {"name": "A", "experience": 99, "tech_stack": []}
        )
        assert len(errors) == 3

    def test_json_validation_drops_bad_fields_and_keeps_good_ones(
        self, validator, accept_email_deliverability
    ):
        cleaned = validator.validate_json_data(
            {
                "name": "Ada Lovelace",
                "email": "ADA@Analytical.io",
                "experience": "4",
                "location": "Delhi 110001",      # invalid: digits
                "tech_stack": ["Python", "<script>"],
            }
        )
        assert cleaned["name"] == "Ada Lovelace"
        assert cleaned["email"] == "ada@analytical.io"
        assert cleaned["experience"] == 4.0
        assert "location" not in cleaned
        assert cleaned["tech_stack"] == ["Python"]
