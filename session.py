"""Session state for the candidate interview.

Every key the stages rely on is created here, once, so no stage has to guess
whether a key exists yet. The keys themselves are load-bearing: the stage
router reads `current_stage`, and the results page reads the answers and
evaluations collected along the way.
"""

import streamlit as st

from conversation_manager import ConversationManager
from data_validator import DataValidator
from llm_handler import LLMHandler

#: The first stage a new session lands on.
INITIAL_STAGE = 'welcome'


def initialize_session_state() -> None:
    """Create any session state key the interview needs but does not have yet."""
    if 'conversation_manager' not in st.session_state:
        st.session_state.conversation_manager = ConversationManager()
        st.session_state.llm_handler = LLMHandler()
        st.session_state.data_validator = DataValidator()

    if 'current_stage' not in st.session_state:
        st.session_state.current_stage = INITIAL_STAGE

    if 'candidate_data' not in st.session_state:
        st.session_state.candidate_data = {}

    if 'technical_questions' not in st.session_state:
        st.session_state.technical_questions = []

    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0

    if 'answers' not in st.session_state:
        st.session_state.answers = []

    if 'evaluations' not in st.session_state:
        st.session_state.evaluations = []

    if 'test_ended_early' not in st.session_state:
        st.session_state.test_ended_early = False

    # Database id of the row backing this assessment, set once the questions
    # have been generated.
    if 'assessment_id' not in st.session_state:
        st.session_state.assessment_id = None

    # The final report is generated once and kept here. Without this it would
    # be regenerated - and re-billed - on every rerun of the results page.
    if 'final_report' not in st.session_state:
        st.session_state.final_report = None

    # Answer bookkeeping: the text area is re-created on every rerun, so the
    # submitted answer and which question it belongs to have to be remembered
    # to know whether an evaluation is the current question's.
    if 'current_answer' not in st.session_state:
        st.session_state.current_answer = ""

    if 'show_evaluation' not in st.session_state:
        st.session_state.show_evaluation = False

    if 'last_submitted_question' not in st.session_state:
        st.session_state.last_submitted_question = -1


def reset_session() -> None:
    """Clear everything and go back to the welcome screen."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
