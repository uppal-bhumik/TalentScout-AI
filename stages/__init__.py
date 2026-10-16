"""The candidate interview, one module per phase of it.

`STAGES` maps the value of `st.session_state.current_stage` to the function
that draws it, which is the whole of the router main_app needs. Adding a stage
means writing it in one of these modules and naming it here; the stage names
themselves are stored in session state, so they must not be renamed lightly.
"""

from typing import Callable, Dict

from stages.assessment import (
    degraded_questions_warning,
    evaluate_current_answer,
    generate_questions_stage,
    move_to_next_question,
    technical_assessment_stage,
)
from stages.profile import (
    email_stage,
    experience_stage,
    location_stage,
    name_stage,
    phone_stage,
    tech_stack_stage,
    welcome_stage,
)
from stages.results import final_evaluation_stage

#: In the order a candidate walks them.
STAGES: Dict[str, Callable[[], None]] = {
    'welcome': welcome_stage,
    'name': name_stage,
    'email': email_stage,
    'phone': phone_stage,
    'experience': experience_stage,
    'location': location_stage,
    'tech_stack': tech_stack_stage,
    'generate_questions': generate_questions_stage,
    'technical_assessment': technical_assessment_stage,
    'final_evaluation': final_evaluation_stage,
}

__all__ = [
    'STAGES',
    'degraded_questions_warning',
    'email_stage',
    'evaluate_current_answer',
    'experience_stage',
    'final_evaluation_stage',
    'generate_questions_stage',
    'location_stage',
    'move_to_next_question',
    'name_stage',
    'phone_stage',
    'tech_stack_stage',
    'technical_assessment_stage',
    'welcome_stage',
]
