"""The recruiter dashboard: list past assessments, open one, read its report.

Reads straight from the database, so it shows every assessment any candidate
has completed - not just the one in the current browser session. Report
rendering is passed in from main_app rather than duplicated here, which keeps
a stored assessment looking identical to a live one.
"""

from typing import Callable, Dict, List, Optional

import streamlit as st

import database as db
from config import Config
from utils import calculate_assessment_metrics, get_logger, truncate_text

logger = get_logger("TalentScout.recruiter")


def recruiter_dashboard(
    render_report: Callable,
    render_downloads: Callable,
) -> None:
    """Entry point for the dashboard view."""
    st.markdown("### 📋 Recruiter Dashboard")

    try:
        rows = db.list_assessments()
    except Exception as exc:
        logger.exception("Could not list assessments: %s", exc)
        st.error("The assessment database could not be read.")
        st.code(str(exc))
        return

    if not rows:
        st.info(
            "No assessments recorded yet. Complete an interview in the candidate "
            "view and it will appear here."
        )
        return

    selected_id = st.session_state.get('recruiter_selected_assessment')

    if selected_id is None:
        _render_list(rows)
    else:
        _render_detail(selected_id, render_report, render_downloads)


def _render_list(rows: List[Dict]) -> None:
    """The overview table plus a row of summary metrics."""
    completed = [r for r in rows if r['is_complete']]
    scored = [r['overall_score'] for r in completed if r['overall_score'] is not None]
    degraded_count = sum(1 for r in rows if r['degraded'])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Assessments", len(rows))
    with col2:
        st.metric("Completed", len(completed))
    with col3:
        st.metric("Average score", f"{sum(scored) / len(scored):.1f}" if scored else "—")
    with col4:
        st.metric("Needs review", degraded_count)

    if degraded_count:
        st.warning(
            f"⚠️ {degraded_count} assessment(s) contain placeholder scores from a "
            "failed LLM call and need a human review."
        )

    st.markdown("---")

    search = st.text_input(
        "Filter by name, email or technology", key="recruiter_search"
    ).strip().lower()

    if search:
        rows = [
            r for r in rows
            if search in (r['name'] or "").lower()
            or search in (r['email'] or "").lower()
            or any(search in t.lower() for t in r['tech_stack'])
        ]
        if not rows:
            st.info("No assessments match that filter.")
            return

    st.caption(f"{len(rows)} assessment(s), most recent first. Times are UTC.")

    for row in rows:
        with st.container():
            cols = st.columns([3, 2, 2, 2, 1.4])

            with cols[0]:
                st.markdown(f"**{row['name']}**")
                st.caption(row['email'] or "no email")

            with cols[1]:
                experience = row['experience']
                exp_text = f"{experience:g} yrs" if experience is not None else "—"
                st.markdown(exp_text)
                st.caption(truncate_text(", ".join(row['tech_stack']), 40) or "—")

            with cols[2]:
                if row['overall_score'] is not None:
                    st.markdown(f"**{row['overall_score']}/10**")
                else:
                    st.markdown("_in progress_")
                st.caption(
                    f"{row['questions_answered']}/{row['questions_total']} answered"
                )

            with cols[3]:
                st.markdown(row['recommendation'] or "—")
                started = row['started_at']
                st.caption(started.strftime("%Y-%m-%d %H:%M") if started else "—")

            with cols[4]:
                if row['degraded']:
                    st.caption("⚠️ review")
                if st.button("Open", key=f"open_{row['assessment_id']}"):
                    st.session_state.recruiter_selected_assessment = row['assessment_id']
                    st.rerun()

            st.markdown(
                "<hr style='margin: 0.4rem 0; border-color: rgba(255,255,255,0.15);'>",
                unsafe_allow_html=True,
            )


def _render_detail(
    assessment_id: int,
    render_report: Callable,
    render_downloads: Callable,
) -> None:
    """One assessment in full, rendered the same way the candidate saw it."""
    if st.button("⬅️ Back to all assessments"):
        st.session_state.recruiter_selected_assessment = None
        st.rerun()

    try:
        detail: Optional[Dict] = db.get_assessment(assessment_id)
    except Exception as exc:
        logger.exception("Could not load assessment %s: %s", assessment_id, exc)
        st.error("That assessment could not be loaded.")
        return

    if detail is None:
        st.error(f"Assessment {assessment_id} no longer exists.")
        st.session_state.recruiter_selected_assessment = None
        return

    candidate = detail['candidate_data']
    st.markdown(f"### 👤 {candidate.get('name', 'Candidate')}")

    with st.sidebar:
        st.markdown("### 👤 Candidate Profile")
        st.write(f"**Name:** {candidate.get('name', '—')}")
        st.write(f"**Email:** {candidate.get('email', '—')}")
        st.write(f"**Phone:** {candidate.get('phone') or '—'}")
        experience = candidate.get('experience')
        st.write(f"**Experience:** {f'{experience:g} years' if experience is not None else '—'}")
        st.write(f"**Location:** {candidate.get('location') or '—'}")
        st.write(f"**Tech Stack:** {', '.join(candidate.get('tech_stack', [])) or '—'}")

    started = detail['started_at']
    completed = detail['completed_at']
    st.caption(
        f"Assessment #{assessment_id} · started "
        f"{started.strftime('%Y-%m-%d %H:%M') if started else '—'} UTC · "
        + (
            f"completed {completed.strftime('%Y-%m-%d %H:%M')} UTC"
            if completed else "not completed"
        )
        + (" · ended early" if detail['ended_early'] else "")
    )

    report = detail['final_report']
    answers = detail['answers']
    evaluations = detail['evaluations']

    if report is None:
        st.warning(
            "This assessment was never completed, so there is no final report. "
            f"{len(answers)} of {detail['questions_total']} questions were answered."
        )
    else:
        if report.get('degraded'):
            st.warning(
                "⚠️ **Scored in degraded mode.** "
                f"{report.get('degraded_reason', 'Some scores are placeholders.')} "
                "These results need a human review."
            )
        render_report(report, candidate, answers, evaluations)

    if answers:
        metrics = calculate_assessment_metrics(evaluations)
        st.markdown("### 📐 Score distribution")
        cols = st.columns(4)
        cols[0].metric("Average", f"{metrics['average_score']:.1f}/10")
        cols[1].metric("Highest", f"{metrics['highest_score']}/10")
        cols[2].metric("Lowest", f"{metrics['lowest_score']}/10")
        cols[3].metric(
            f"At or above {Config.PASSING_SCORE}",
            f"{metrics['passing_questions']}/{metrics['total_questions']}",
        )

    if detail['skipped_questions']:
        with st.expander(f"⏭️ {len(detail['skipped_questions'])} question(s) not answered"):
            for question in detail['skipped_questions']:
                st.markdown(f"- {question['question']}")

    if report is not None:
        st.markdown("---")
        render_downloads(
            report,
            candidate,
            answers,
            evaluations,
            extra={'assessment_id': assessment_id, 'ended_early': detail['ended_early']},
        )

    st.markdown("---")
    with st.expander("🗑️ Delete this assessment"):
        st.caption(
            "This permanently removes the assessment, its answers and its report."
        )
        if st.checkbox("I understand this cannot be undone", key=f"confirm_del_{assessment_id}"):
            if st.button("Delete permanently", type="primary", key=f"del_{assessment_id}"):
                try:
                    db.delete_assessment(assessment_id)
                except Exception as exc:
                    logger.exception("Could not delete assessment %s: %s", assessment_id, exc)
                    st.error("Deletion failed.")
                else:
                    st.session_state.recruiter_selected_assessment = None
                    st.rerun()
