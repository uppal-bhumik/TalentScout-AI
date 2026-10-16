"""Page chrome: the stylesheet, the header, the profile sidebar, the view switch.

Everything here frames the app rather than belonging to any one stage, so the
stage modules never have to care about it.
"""

from pathlib import Path

import streamlit as st

from config import Config
from utils import get_logger

logger = get_logger("TalentScout.chrome")

STYLESHEET = Path(__file__).parent / "static" / "styles.css"

#: The profile fields, in the order they are collected. The sidebar shows them
#: in this order and measures progress against the length of this list.
PROFILE_FIELDS = ['name', 'email', 'phone', 'experience', 'location', 'tech_stack']


@st.cache_data
def _read_stylesheet(mtime: float) -> str:
    """Read the stylesheet, caching on its modification time.

    `mtime` is not used in the body - it is the cache key, so an edit to the
    file is picked up on the next rerun instead of needing a restart.
    """
    try:
        return STYLESHEET.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not read %s: %s", STYLESHEET, exc)
        return ""


def load_stylesheet() -> None:
    """Inject the app's CSS, which lives in static/styles.css."""
    try:
        mtime = STYLESHEET.stat().st_mtime
    except OSError:
        mtime = 0.0

    css = _read_stylesheet(mtime)
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def display_header() -> None:
    """Display the main header with enhanced styling"""
    st.markdown('<h1 class="main-header">🎯 TalentScout AI</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">INTELLIGENT  HIRING  ASSISTANT  FOR TECHNICAL  SCREENING</p>', unsafe_allow_html=True)
    st.markdown("---")


def display_candidate_profile() -> None:
    """Show what has been collected so far, and how much is left, in the sidebar."""
    if st.session_state.candidate_data:
        with st.sidebar:
            st.markdown("### 👤 Candidate Profile")
            st.markdown('<div class="candidate-info">', unsafe_allow_html=True)

            data = st.session_state.candidate_data
            if 'name' in data:
                st.write(f"**Name:** {data['name']}")
            if 'email' in data:
                st.write(f"**Email:** {data['email']}")
            if 'phone' in data:
                st.write(f"**Phone:** {data['phone']}")
            if 'experience' in data:
                exp = data['experience']
                exp_text = f"{exp} year{'s' if exp != 1 else ''}"
                st.write(f"**Experience:** {exp_text}")
            if 'location' in data:
                st.write(f"**Location:** {data['location']}")
            if 'tech_stack' in data:
                tech_list = ', '.join(data['tech_stack'])
                st.write(f"**Tech Stack:** {tech_list}")

            st.markdown('</div>', unsafe_allow_html=True)

            # Progress indicator
            completed = len([k for k in PROFILE_FIELDS if k in data])
            progress = min(completed / len(PROFILE_FIELDS) * 100, 100)

            st.progress(progress / 100)
            st.markdown(f'<p class="progress-text">Profile: {int(progress)}% Complete</p>', unsafe_allow_html=True)


def sidebar_navigation() -> str:
    """Choose between the candidate interview and the recruiter dashboard.

    Returns 'interview' or 'recruiter'. The dashboard holds candidate contact
    details, so when RECRUITER_PASSWORD is set it has to be entered first; on
    a local machine with no password configured it is open.
    """
    with st.sidebar:
        st.markdown("### 🧭 View")
        view = st.radio(
            "View",
            options=['interview', 'recruiter'],
            format_func=lambda v: (
                "📝 Candidate interview" if v == 'interview' else "📋 Recruiter dashboard"
            ),
            label_visibility="collapsed",
            key="active_view",
        )

        if view == 'recruiter' and Config.RECRUITER_PASSWORD:
            if not st.session_state.get('recruiter_authenticated'):
                entered = st.text_input(
                    "Recruiter password", type="password", key="recruiter_password_input"
                )
                if entered:
                    if entered == Config.RECRUITER_PASSWORD:
                        st.session_state.recruiter_authenticated = True
                        st.rerun()
                    else:
                        st.error("Incorrect password.")
                st.info("Enter the recruiter password to view past assessments.")
                return 'locked'

    return view
