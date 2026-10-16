"""Tests for the declared profile stages.

The Streamlit wrapper around these declarations needs a running app, but the
part worth testing does not: `resolve_text_field` decides what gets stored and
what error the candidate sees, and the declarations decide where each stage
leads. Both are checked here without a Streamlit runtime.
"""

import pytest

from data_validator import DataValidator
from stages import STAGES
from stages.profile import TEXT_FIELD_STAGES, resolve_text_field

#: The order the candidate walks the profile, which the declarations'
#: next_stage/previous_stage links have to agree with.
PROFILE_WALK = [
    'welcome', 'name', 'email', 'phone', 'experience', 'location', 'tech_stack',
]


class TestDeclarations:
    def test_every_declaration_is_keyed_on_its_own_field(self):
        for key, stage in TEXT_FIELD_STAGES.items():
            assert stage.field == key

    def test_widget_keys_follow_the_field_name(self):
        for stage in TEXT_FIELD_STAGES.values():
            assert stage.input_key == f"{stage.field}_input"

    def test_validators_exist_on_the_validator(self):
        for stage in TEXT_FIELD_STAGES.values():
            assert callable(getattr(DataValidator, stage.validator, None)), (
                f"{stage.field} names a validator that does not exist"
            )

    @pytest.mark.parametrize("name", sorted(TEXT_FIELD_STAGES))
    def test_navigation_matches_the_walk_order(self, name):
        position = PROFILE_WALK.index(name)
        stage = TEXT_FIELD_STAGES[name]
        assert stage.previous_stage == PROFILE_WALK[position - 1]
        assert stage.next_stage == PROFILE_WALK[position + 1]

    @pytest.mark.parametrize("name", sorted(TEXT_FIELD_STAGES))
    def test_both_neighbours_are_routable(self, name):
        # A typo in a stage name would strand the candidate on a blank page.
        stage = TEXT_FIELD_STAGES[name]
        assert stage.previous_stage in STAGES
        assert stage.next_stage in STAGES

    def test_messages_are_distinct(self):
        # "that is empty" and "that is wrong" are different problems, and the
        # candidate is told which one they have.
        for stage in TEXT_FIELD_STAGES.values():
            assert stage.empty_message != stage.invalid_message


class TestResolveTextField:
    @pytest.mark.parametrize("raw", ["", "   ", "\t\n"])
    @pytest.mark.parametrize("name", sorted(TEXT_FIELD_STAGES))
    def test_blank_input_reports_the_empty_message(self, validator, name, raw):
        stage = TEXT_FIELD_STAGES[name]
        value, error = resolve_text_field(stage, raw, validator)
        assert value is None
        assert error == stage.empty_message

    @pytest.mark.parametrize(
        "name, raw",
        [
            ('name', "Ada3"),
            ('email', "not-an-email"),
            ('phone', "12"),
            ('location', "<script>"),
        ],
    )
    def test_rejected_input_reports_the_invalid_message(self, validator, name, raw):
        stage = TEXT_FIELD_STAGES[name]
        value, error = resolve_text_field(stage, raw, validator)
        assert value is None
        assert error == stage.invalid_message

    @pytest.mark.parametrize(
        "name, raw, stored",
        [
            ('name', "  Ada Lovelace  ", "Ada Lovelace"),
            ('phone', "  +442071838750 ", "+442071838750"),
            ('location', " London, United Kingdom ", "London, United Kingdom"),
        ],
    )
    def test_accepted_input_is_stripped(self, validator, name, raw, stored):
        value, error = resolve_text_field(TEXT_FIELD_STAGES[name], raw, validator)
        assert error is None
        assert value == stored

    def test_email_is_lowercased(self, validator, accept_email_deliverability):
        # The email is the key candidates are matched on in the database, so
        # it is stored in one case rather than as typed.
        value, error = resolve_text_field(
            TEXT_FIELD_STAGES['email'], "  Ada@Analytical.Example ", validator
        )
        assert error is None
        assert value == "ada@analytical.example"

    def test_the_validator_sees_the_raw_value(self, validator):
        # Padding a rejected value with spaces must not sneak it past the
        # validator: it is validated before it is normalised.
        calls = []

        class Recording:
            def validate_name(self, value):
                calls.append(value)
                return False

        value, error = resolve_text_field(
            TEXT_FIELD_STAGES['name'], "  Ada3  ", Recording()
        )
        assert calls == ["  Ada3  "]
        assert value is None
        assert error == TEXT_FIELD_STAGES['name'].invalid_message


class TestRouter:
    def test_every_walk_stage_is_routable(self):
        for name in PROFILE_WALK:
            assert name in STAGES

    def test_the_assessment_stages_are_routable(self):
        assert 'generate_questions' in STAGES
        assert 'technical_assessment' in STAGES
        assert 'final_evaluation' in STAGES

    def test_every_route_is_callable(self):
        for name, stage in STAGES.items():
            assert callable(stage), f"{name} does not map to a callable"
