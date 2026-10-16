"""The profile stages: everything collected before the questions are generated.

Four of these stages - name, email, phone and location - are the same form:
a heading, one text input, validate, store, advance. They are declared as
`TextFieldStage` values rather than written out four times, so adding another
one is a declaration instead of another copy of the same twenty lines.

Experience (a selectbox) and the tech stack (a grid of checkboxes) have their
own input widgets and so keep their own functions.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

import streamlit as st

from config import Config
from data_validator import DataValidator


def _strip(value: str) -> str:
    return value.strip()


def _strip_lower(value: str) -> str:
    return value.strip().lower()


@dataclass(frozen=True)
class TextFieldStage:
    """One "ask for a value, validate it, move on" step of the profile form."""

    field: str                      # key this value takes in candidate_data
    heading: str                    # markdown heading above the input
    label: str                      # the text input's own label
    validator: str                  # DataValidator method that accepts the raw value
    empty_message: str              # shown when nothing was typed
    invalid_message: str            # shown when the validator rejects the value
    next_stage: str
    previous_stage: str
    placeholder: Optional[str] = None
    normalise: Callable[[str], str] = _strip

    @property
    def input_key(self) -> str:
        """Widget key. Kept as `<field>_input` - it is in use in saved sessions."""
        return f"{self.field}_input"


#: Declared in the order the candidate walks them, which is also the order the
#: `previous_stage`/`next_stage` links describe.
TEXT_FIELD_STAGES: Dict[str, TextFieldStage] = {
    'name': TextFieldStage(
        field='name',
        heading="### Let's start with your name",
        label="What's your full name?",
        validator='validate_name',
        empty_message="Please enter your name",
        invalid_message="Please enter a valid name (letters only, 2-50 characters)",
        next_stage='email',
        previous_stage='welcome',
    ),
    'email': TextFieldStage(
        field='email',
        heading="### What's your email address?",
        label="Email address",
        validator='validate_email',
        empty_message="Please enter your email address",
        invalid_message="Please enter a valid email address",
        next_stage='phone',
        previous_stage='name',
        normalise=_strip_lower,
    ),
    'phone': TextFieldStage(
        field='phone',
        heading="### What's your phone number?",
        label="Phone number (with country code)",
        validator='validate_phone',
        empty_message="Please enter your phone number",
        invalid_message="Please enter a valid phone number",
        next_stage='experience',
        previous_stage='email',
        placeholder="+91 9876543210",
    ),
    'location': TextFieldStage(
        field='location',
        heading="### Where are you currently located?",
        label="City, Country",
        validator='validate_location',
        empty_message="Please enter your location",
        invalid_message="Please enter a valid location",
        next_stage='tech_stack',
        previous_stage='experience',
        placeholder="Delhi, India",
    ),
}

#: Offered by the experience selectbox: half-years early on, where the
#: difference matters, then whole years.
EXPERIENCE_OPTIONS = [
    0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5,
    6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 25, 30,
]


def resolve_text_field(
    stage: TextFieldStage,
    raw: str,
    validator: DataValidator,
) -> Tuple[Optional[str], Optional[str]]:
    """Turn a raw submission into either a value to store or a message to show.

    Returns `(value, None)` when the input is acceptable and `(None, message)`
    when it is not. The validator sees the raw text, not the normalised value,
    so it can reject whitespace the normaliser would otherwise hide.
    """
    if not raw.strip():
        return None, stage.empty_message

    if not getattr(validator, stage.validator)(raw):
        return None, stage.invalid_message

    return stage.normalise(raw), None


def _navigate_back(previous_stage: str) -> None:
    """The Back button, which every profile stage has in the same place."""
    if st.button("⬅️ Back"):
        st.session_state.current_stage = previous_stage
        st.rerun()


def render_text_field_stage(stage: TextFieldStage) -> None:
    """Draw one declared text-input stage."""
    st.markdown(stage.heading)

    raw = st.text_input(stage.label, key=stage.input_key, placeholder=stage.placeholder)

    col1, col2 = st.columns([1, 4])

    with col1:
        if st.button("Next ➡️", type="primary"):
            value, error = resolve_text_field(
                stage, raw, st.session_state.data_validator
            )
            if error:
                st.error(error)
            else:
                st.session_state.candidate_data[stage.field] = value
                st.session_state.current_stage = stage.next_stage
                st.rerun()

    with col2:
        _navigate_back(stage.previous_stage)


def welcome_stage() -> None:
    """Explain what the assessment involves before anything is collected."""
    st.markdown("### Welcome to TalentScout AI! 👋")
    st.write("I'm here to help you with the initial technical screening process. Let's start by getting to know you better.")

    # Create an attractive info box
    st.markdown("""
    <div class="candidate-info">
        <h4>📋 Assessment Process Overview:</h4>
        <p><strong>1. Profile Setup</strong> - Basic information collection</p>
        <p><strong>2. Technical Assessment</strong> - Maximum 5 personalized questions</p>
        <p><strong>3. Instant Evaluation</strong> - Real-time feedback on responses</p>
        <p><strong>4. Final Report</strong> - Comprehensive assessment results</p>
        <br>
        <p>🕒 <strong>Time:</strong> 15-30 minutes | 🚪 <strong>Exit:</strong> End test anytime | ⭐ <strong>Skip:</strong> Skip difficult questions</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Let's Get Started! 🚀", type="primary"):
        st.session_state.current_stage = 'name'
        st.rerun()


def name_stage() -> None:
    """Collect candidate name"""
    render_text_field_stage(TEXT_FIELD_STAGES['name'])


def email_stage() -> None:
    """Collect candidate email"""
    render_text_field_stage(TEXT_FIELD_STAGES['email'])


def phone_stage() -> None:
    """Collect candidate phone"""
    render_text_field_stage(TEXT_FIELD_STAGES['phone'])


def location_stage() -> None:
    """Collect candidate location"""
    render_text_field_stage(TEXT_FIELD_STAGES['location'])


def experience_stage() -> None:
    """Collect candidate experience. A selectbox, so there is nothing to validate."""
    st.markdown("### How many years of professional experience do you have?")

    experience = st.selectbox(
        "Years of experience",
        options=EXPERIENCE_OPTIONS,
        key="experience_input",
    )

    col1, col2 = st.columns([1, 4])

    with col1:
        if st.button("Next ➡️", type="primary"):
            st.session_state.candidate_data['experience'] = experience
            st.session_state.current_stage = 'location'
            st.rerun()

    with col2:
        _navigate_back('phone')


def tech_stack_stage() -> None:
    """Collect candidate tech stack. Drives the questions, so it cannot be empty."""
    st.markdown("### What technologies make up your primary tech stack?")
    st.write("Select all technologies you're proficient in:")

    # Technology categories come from Config so there is one list to maintain
    tech_categories = Config.get_technology_categories()

    selected_technologies = []

    for category, technologies in tech_categories.items():
        st.write(f"**{category}:**")
        cols = st.columns(3)
        for i, tech in enumerate(technologies):
            with cols[i % 3]:
                if st.checkbox(tech, key=f"tech_{tech}"):
                    selected_technologies.append(tech)

    # Other technologies
    st.write("**Other Technologies:**")
    other_tech = st.text_input("Enter other technologies (comma-separated)", key="other_tech_input")
    if other_tech.strip():
        other_technologies = [tech.strip() for tech in other_tech.split(',') if tech.strip()]
        selected_technologies.extend(other_technologies)

    col1, col2 = st.columns([1, 4])

    with col1:
        if st.button("Next ➡️", type="primary"):
            if selected_technologies:
                st.session_state.candidate_data['tech_stack'] = selected_technologies
                st.session_state.current_stage = 'generate_questions'
                st.rerun()
            else:
                st.error("Please select at least one technology")

    with col2:
        _navigate_back('location')
