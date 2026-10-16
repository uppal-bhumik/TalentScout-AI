"""The results stage: generate the final report once, show it, offer the exports.

The rendering itself lives in report_view, which the recruiter dashboard uses
too; what is here is the part specific to the candidate who has just finished -
generating the report, caching it and writing it to the database.
"""

import streamlit as st

import database as db
from report_view import render_downloads, render_report
from session import reset_session
from utils import get_logger

logger = get_logger("TalentScout.results")


def final_evaluation_stage() -> None:
    """Show the final evaluation, persist it and offer the exports."""
    st.markdown("### 🎉 Assessment Complete!")

    if st.session_state.test_ended_early:
        st.markdown(f"""
        <div class="end-test-box">
            <p><strong>⚡ Test ended early by candidate choice</strong></p>
            <p>Evaluation based on {len(st.session_state.answers)} completed question(s)</p>
        </div>
        """, unsafe_allow_html=True)

    st.write(
        "Thank you for completing the technical assessment. "
        "Here's your comprehensive evaluation:"
    )

    if not st.session_state.evaluations:
        st.warning("No questions were answered. Assessment cannot be completed.")
        if st.button("🔄 Start Over"):
            reset_session()
        return

    final_report = _generate_report_once()

    if final_report.get('degraded'):
        st.warning(
            "⚠️ **This report was produced in degraded mode.** "
            f"{final_report.get('degraded_reason', 'Some scores are placeholders.')} "
            "Treat the numbers below as provisional — they need a human review."
        )

    render_report(
        final_report,
        st.session_state.candidate_data,
        st.session_state.answers,
        st.session_state.evaluations,
    )

    st.markdown("---")
    render_downloads(
        final_report,
        st.session_state.candidate_data,
        st.session_state.answers,
        st.session_state.evaluations,
        extra={
            'test_ended_early': st.session_state.test_ended_early,
            'total_questions_generated': len(st.session_state.technical_questions),
            'assessment_id': st.session_state.assessment_id,
        },
    )

    st.markdown("---")
    col_restart1, col_restart2 = st.columns([1, 4])
    with col_restart1:
        if st.button("🔄 Start New Assessment"):
            reset_session()


def _generate_report_once() -> dict:
    """Return the final report, generating and storing it on the first call.

    The report is cached in session state because regenerating it on every
    rerun would bill another API call for every button click on this page.
    """
    if st.session_state.final_report is not None:
        return st.session_state.final_report

    with st.spinner("Generating your final report..."):
        st.session_state.final_report = st.session_state.llm_handler.generate_final_report(
            st.session_state.candidate_data,
            st.session_state.answers,
            st.session_state.evaluations,
        )

    if st.session_state.assessment_id is not None:
        try:
            db.save_final_report(
                st.session_state.assessment_id,
                st.session_state.final_report,
                ended_early=st.session_state.test_ended_early,
            )
        except Exception as exc:  # a storage failure must not hide the report
            logger.exception("Could not persist the final report: %s", exc)
            st.warning(
                "⚠️ This report could not be saved to the database. It is shown "
                "below and can still be downloaded."
            )

    return st.session_state.final_report
