"""TalentScout AI - Streamlit entry point.

Bootstraps the app (configuration, database, session state, page chrome), then
hands over to either the candidate interview - whose stages live in `stages/` -
or the recruiter dashboard in recruiter_view.py. Everything a candidate does is
written to the database as it happens, so a refresh loses the UI state but not
the assessment.
"""

import streamlit as st
from dotenv import load_dotenv

import database as db
from app_chrome import (
    display_candidate_profile,
    display_header,
    load_stylesheet,
    sidebar_navigation,
)
from config import Config
from recruiter_view import recruiter_dashboard
from session import INITIAL_STAGE, initialize_session_state
from stages import STAGES
from utils import get_logger

# Load environment variables from .env file
load_dotenv()

logger = get_logger("TalentScout.app")

# Page configuration
st.set_page_config(
    page_title="TalentScout AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

load_stylesheet()


def _bootstrap() -> None:
    """Check the configuration and open the database before anything uses them."""
    # Fail loudly on a missing or wrong API key. Without this the LLM calls
    # fall back silently and every candidate gets canned questions and a
    # flat score of 5, which looks like a working app but isn't one.
    try:
        Config.validate_config()
    except ValueError as e:
        st.error("⚠️ Configuration problem — answers cannot be scored until this is fixed.")
        st.code(str(e))
        st.info("Copy `.env.example` to `.env`, add your OpenAI API key, then restart the app.")
        st.stop()

    # Open the database (and create the schema on first run) before anything
    # tries to read or write it.
    try:
        db.init_db()
    except Exception as exc:
        logger.exception("Database unavailable: %s", exc)
        st.warning(
            "⚠️ The database could not be opened, so assessments will not be saved "
            "and the recruiter dashboard is unavailable. Interviews still work."
        )


def main():
    """Bootstrap, pick the view, then route to the current interview stage."""
    _bootstrap()

    initialize_session_state()
    display_header()

    view = sidebar_navigation()
    if view == 'recruiter':
        recruiter_dashboard()
        return
    if view == 'locked':
        st.info("🔒 The recruiter dashboard is password protected.")
        return

    display_candidate_profile()

    stage = STAGES.get(st.session_state.current_stage)
    if stage is None:
        # Unknown stage - most likely a stale session. Start over.
        logger.warning("Unknown stage %r, returning to the start", st.session_state.current_stage)
        st.session_state.current_stage = INITIAL_STAGE
        st.rerun()
    else:
        stage()


if __name__ == "__main__":
    main()
