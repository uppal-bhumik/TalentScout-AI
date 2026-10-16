"""Rendering for a finished assessment: score cards, breakdown, downloads.

Imported by both the candidate's results page and the recruiter dashboard, so
a stored assessment looks exactly like a live one. Nothing here reads session
state - everything it draws is passed in, which is what lets the recruiter
view render someone else's assessment from the database.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

import streamlit as st

from config import Config
from utils import ReportGenerator, sanitize_filename


def score_colour(score: float) -> str:
    """Traffic-light colour for a 1-10 score."""
    if score >= 7:
        return "#4CAF50"
    return "#FF9800" if score >= 5 else "#F44336"


def render_report(
    final_report: Dict,
    candidate_data: Dict,
    answers: List[Dict],
    evaluations: List[Dict],
) -> None:
    """Render the score cards, analysis and per-question breakdown."""
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        # Show the completion adjustment rather than silently applying it, so
        # the arithmetic behind the score is visible.
        penalty_factor = final_report.get('completion_penalty_factor', 1.0)
        if penalty_factor < 1.0:
            score_note = (
                f'<p style="font-size: 0.75em; color: #FFE4B5; margin: 0;">'
                f'{final_report["performance_score"]}/10 on answers given '
                f'&times; {penalty_factor} completion factor</p>'
            )
        else:
            score_note = ''
        st.markdown(f'''
        <div class="metric-card">
            <h3 style="color: #FFD700;">📊 Overall Score</h3>
            <p style="font-size: 2em; font-weight: bold; color: white; margin-bottom: 0;">{final_report['overall_score']}/10</p>
            {score_note}
        </div>
        ''', unsafe_allow_html=True)

    with col2:
        st.markdown(f'''
        <div class="metric-card">
            <h3 style="color: #87CEEB;">❓ Questions</h3>
            <p style="font-size: 2em; font-weight: bold; color: white; margin-bottom: 0;">{len(answers)}/{Config.DEFAULT_QUESTIONS}</p>
            <p style="font-size: 0.75em; color: #CFE8F3; margin: 0;">{final_report.get('completion_status', '')}</p>
        </div>
        ''', unsafe_allow_html=True)

    with col3:
        recommendation = final_report.get('recommendation', 'N/A')
        rec_color = (
            "#90EE90" if "Strong Hire" in recommendation
            else "#FFB6C1" if "Hire" in recommendation
            else "#FFA07A"
        )
        st.markdown(f'''
        <div class="metric-card">
            <h3 style="color: #DDA0DD;">🎯 Recommendation</h3>
            <p style="font-size: 1.2em; font-weight: bold; color: {rec_color};">{recommendation}</p>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("### 📈 Detailed Analysis")
    st.markdown(f'''
    <div class="final-report-box">
        <p style="color: white; font-size: 1.1em; line-height: 1.6;">{final_report.get('detailed_feedback', '')}</p>
    </div>
    ''', unsafe_allow_html=True)

    if answers and evaluations:
        st.markdown("### 🔍 Question-wise Breakdown")
        for i, (answer, evaluation) in enumerate(zip(answers, evaluations)):
            flag = " ⚠️ not scored" if evaluation.get('degraded') else ""
            with st.expander(f"Question {i + 1}: {evaluation['score']}/10{flag}", expanded=False):
                st.markdown(f"**Question:** {answer['question']}")
                st.markdown(f"**Category:** {answer.get('category', 'General').title()}")
                st.markdown(f"**Answer:** {answer['answer']}")
                st.markdown(
                    f"**Score:** <span style='color: {score_colour(evaluation['score'])}; "
                    f"font-weight: bold;'>{evaluation['score']}/10</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**Feedback:** {evaluation['feedback']}")
                if evaluation.get('degraded'):
                    st.caption(
                        "Placeholder score — automated scoring failed: "
                        f"{evaluation.get('degraded_reason', 'unknown')}"
                    )


def render_downloads(
    final_report: Dict,
    candidate_data: Dict,
    answers: List[Dict],
    evaluations: List[Dict],
    extra: Optional[Dict] = None,
) -> None:
    """Offer the assessment as JSON, HTML or CSV."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"assessment_{sanitize_filename(candidate_data.get('name', 'candidate'))}_{timestamp}"

    payload = {
        'candidate_data': candidate_data,
        'answers': answers,
        'evaluations': evaluations,
        'final_report': final_report,
        'questions_answered': len(answers),
        'timestamp': timestamp,
    }
    payload.update(extra or {})

    col_json, col_html, col_csv = st.columns(3)

    with col_json:
        st.download_button(
            label="📄 Download JSON",
            data=json.dumps(payload, indent=2, default=str),
            file_name=f"{stem}.json",
            mime="application/json",
            key=f"dl_json_{stem}",
        )

    with col_html:
        st.download_button(
            label="🖨️ Download HTML report",
            data=ReportGenerator.generate_html_report(
                candidate_data, answers, evaluations, final_report
            ),
            file_name=f"{stem}.html",
            mime="text/html",
            key=f"dl_html_{stem}",
        )

    with col_csv:
        st.download_button(
            label="📊 Download CSV summary",
            data=ReportGenerator.generate_csv_summary(candidate_data, evaluations),
            file_name=f"{stem}.csv",
            mime="text/csv",
            key=f"dl_csv_{stem}",
        )
