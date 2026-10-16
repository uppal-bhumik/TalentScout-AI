"""The assessment stages: generating the questions and working through them.

The candidate can move forwards, backwards, skip a question or end the test
early, so this module owns the question index and the answer bookkeeping that
makes those moves safe - in particular, re-answering a question has to replace
the earlier attempt rather than record a second one.
"""

import streamlit as st

import database as db
from config import Config
from report_view import score_colour
from utils import get_logger

logger = get_logger("TalentScout.assessment")

#: Typing any of these instead of an answer skips the question.
SKIP_PHRASES = {'not sure', 'skip', 'pass', 'idk', "i don't know"}


def generate_questions_stage() -> None:
    """Generate technical questions based on tech stack"""
    st.markdown("### Generating Your Technical Assessment 🧠")
    st.write("Based on your profile, I'm creating personalized technical questions...")

    with st.spinner("Analyzing your tech stack and generating questions..."):
        questions = st.session_state.llm_handler.generate_technical_questions(
            st.session_state.candidate_data
        )

    if not questions:
        st.error("Failed to generate questions. Please try again.")
        if st.button("Try Again"):
            st.rerun()
        return

    # Cap at the configured question count
    questions = questions[:Config.DEFAULT_QUESTIONS]
    st.session_state.technical_questions = questions

    # Open the database record now, so answers can be stored as they arrive
    # rather than only at the end.
    try:
        st.session_state.assessment_id = db.create_assessment(
            st.session_state.candidate_data, questions
        )
    except Exception as exc:  # a storage failure must not end the interview
        logger.exception("Could not create the assessment record: %s", exc)
        st.warning(
            "⚠️ This assessment could not be saved to the database, so it will not "
            "appear in the recruiter dashboard. The interview itself will work normally."
        )

    st.session_state.current_stage = 'technical_assessment'
    st.session_state.current_question_index = 0
    # Start the question set from a clean slate.
    st.session_state.current_answer = ""
    st.session_state.show_evaluation = False
    st.session_state.last_submitted_question = -1
    st.session_state.final_report = None
    st.rerun()


def degraded_questions_warning() -> None:
    """Tell the candidate when the questions are not personalised."""
    questions = st.session_state.get('technical_questions') or []
    degraded = next((q for q in questions if q.get('degraded')), None)
    if degraded:
        st.warning(
            "⚠️ **These questions are not personalised.** The question generator "
            f"could not be reached, so a generic set is being used. Reason: "
            f"{degraded.get('degraded_reason', 'unknown')}"
        )


def technical_assessment_stage() -> None:
    """One question at a time, with its evaluation and the navigation around it."""
    if not st.session_state.technical_questions:
        st.error("No questions available. Please restart the assessment.")
        return

    current_q_index = st.session_state.current_question_index
    total_questions = len(st.session_state.technical_questions)

    # Check if we've completed all questions
    if current_q_index >= total_questions:
        st.session_state.current_stage = 'final_evaluation'
        st.rerun()
        return

    # Get current question
    current_question = st.session_state.technical_questions[current_q_index]

    # Assessment header
    st.markdown(f"### Technical Assessment - Question {current_q_index + 1} of {total_questions}")

    degraded_questions_warning()

    # Progress bar
    progress = (current_q_index + 1) / total_questions
    st.progress(progress)

    # End test option - prominently displayed
    st.markdown("""
    <div class="end-test-box">
        <p>💡 <strong>Options:</strong> You can skip difficult questions, end the test anytime, or answer "not sure" to move to the next question.</p>
    </div>
    """, unsafe_allow_html=True)

    _render_assessment_controls(current_q_index)
    _render_question_card(current_question, current_q_index)
    _render_previous_evaluations()

    # The evaluation panel belongs to the question that was just submitted; on
    # any other question the answer form is shown instead.
    show_current_evaluation = (st.session_state.show_evaluation and
                              st.session_state.last_submitted_question == current_q_index)

    if show_current_evaluation:
        _render_current_evaluation(current_q_index, total_questions)
    else:
        _render_answer_form(current_question, current_q_index)


def _render_assessment_controls(current_q_index: int) -> None:
    """The skip and end-test buttons that sit above every question."""
    col_skip, col_end, col_spacer = st.columns([1, 1, 3])

    with col_skip:
        if st.button("⭐ Skip Question", help="Skip this question and move to next", key=f"skip_btn_{current_q_index}"):
            move_to_next_question()

    with col_end:
        if st.button("🚪 End Test Now", help="Get evaluation based on current progress", key=f"end_btn_{current_q_index}"):
            if st.session_state.answers:
                st.session_state.test_ended_early = True
                st.session_state.current_stage = 'final_evaluation'
                st.rerun()
            else:
                st.warning("Please answer at least one question to get an evaluation.")


def _render_question_card(current_question: dict, current_q_index: int) -> None:
    """The question itself, with its category and difficulty."""
    question_text = current_question.get("question", "Question not found")
    category = current_question.get("category", "General")
    difficulty = current_question.get("difficulty", "Intermediate")

    st.markdown(f'''
    <div class="question-box">
        <h4>🔍 Question {current_q_index + 1}</h4>
        <p style="font-size: 1.1em; font-weight: 500; color: white !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">{question_text}</p>
        <p style="color: rgba(255,255,255,0.8); font-size: 0.9em;">
            📂 Category: {category.title()} |
            ⭐ Difficulty: {difficulty.title()}
        </p>
    </div>
    ''', unsafe_allow_html=True)


def _render_previous_evaluations() -> None:
    """Scores and feedback for everything answered so far, collapsed."""
    if st.session_state.evaluations:
        with st.expander("📊 Previous Question Reviews", expanded=False):
            for i, eval_data in enumerate(st.session_state.evaluations):
                st.markdown(f'''
                <div class="evaluation-box">
                    <p><strong>Q{i+1} Evaluation:</strong></p>
                    <p><strong>Score:</strong> <span style="color: {score_colour(eval_data['score'])}; font-size: 1.2em;">{eval_data['score']}/10</span></p>
                    <p><strong>Feedback:</strong> {eval_data['feedback']}</p>
                </div>
                ''', unsafe_allow_html=True)


def _render_current_evaluation(current_q_index: int, total_questions: int) -> None:
    """The result of the answer just submitted, plus the way onwards."""
    latest_evaluation = st.session_state.evaluations[-1]

    if latest_evaluation.get('degraded'):
        st.warning(
            "⚠️ **This answer could not be scored.** It has been recorded with a "
            "placeholder score of 5/10 and flagged for human review. Reason: "
            f"{latest_evaluation.get('degraded_reason', 'unknown')}"
        )

    st.markdown(f'''
    <div class="evaluation-box">
        <h4>✅ Answer Submitted Successfully!</h4>
        <p><strong>Score:</strong> <span style="color: {score_colour(latest_evaluation['score'])}; font-size: 1.3em;">{latest_evaluation['score']}/10</span></p>
        <p><strong>Feedback:</strong> {latest_evaluation['feedback']}</p>
    </div>
    ''', unsafe_allow_html=True)

    if current_q_index + 1 < total_questions:
        if st.button("Continue to Next Question ➡️", type="primary", key=f"next_question_btn_{current_q_index}"):
            move_to_next_question()
    else:
        st.markdown("### 🎉 Assessment Complete!")
        if st.button("Generate Final Report 📊", type="primary", key=f"final_report_btn_{current_q_index}"):
            st.session_state.current_stage = 'final_evaluation'
            st.rerun()


def _render_answer_form(current_question: dict, current_q_index: int) -> None:
    """The answer box, with submit and previous-question navigation."""
    # The key is per question, so each question keeps its own text area; the
    # value is cleared once this question has been submitted.
    answer_key = f"answer_q_{current_q_index}"
    default_answer = (
        st.session_state.current_answer
        if st.session_state.last_submitted_question != current_q_index else ""
    )

    answer = st.text_area(
        "Your Answer:",
        key=answer_key,
        height=150,
        placeholder="Please provide a detailed answer with examples where possible... Type 'not sure' to skip this question.",
        value=default_answer
    )

    col1, col2, col3 = st.columns([1, 1, 3])

    with col1:
        if st.button("Submit Answer", type="primary", key=f"submit_btn_{current_q_index}"):
            if answer.strip():
                if answer.strip().lower() in SKIP_PHRASES:
                    st.info("Skipping this question...")
                    move_to_next_question()
                else:
                    st.session_state.current_answer = answer.strip()
                    evaluate_current_answer(current_question, answer.strip(), current_q_index)
            else:
                st.error("Please provide an answer before submitting.")

    with col2:
        if current_q_index > 0:
            if st.button("⬅️ Previous", key=f"prev_btn_{current_q_index}"):
                st.session_state.current_question_index = max(0, current_q_index - 1)
                st.session_state.show_evaluation = False
                st.session_state.current_answer = ""
                st.rerun()


def move_to_next_question() -> None:
    """Advance to the next question, or to the report if this was the last."""
    current_q_index = st.session_state.current_question_index
    total_questions = len(st.session_state.technical_questions)

    if current_q_index + 1 < total_questions:
        st.session_state.current_question_index += 1
        st.session_state.show_evaluation = False
        st.session_state.current_answer = ""  # the next question starts empty
        st.rerun()
    else:
        # All questions completed
        if st.session_state.answers:
            st.session_state.current_stage = 'final_evaluation'
            st.rerun()
        else:
            st.warning("Please answer at least one question to get an evaluation.")


def evaluate_current_answer(question: dict, answer: str, question_index: int) -> None:
    """Score the current answer, store it in session state and persist it."""
    with st.spinner("Evaluating your answer..."):
        evaluation = st.session_state.llm_handler.evaluate_answer(
            question,
            answer,
            st.session_state.candidate_data
        )

    record = {
        'question': question['question'],
        'answer': answer,
        'category': question.get('category', 'General'),
        'question_index': question_index,
    }

    # The candidate can navigate back and answer again, so replace any earlier
    # attempt at this question instead of recording it twice - a duplicate
    # would be counted twice in the final report.
    existing = next(
        (i for i, a in enumerate(st.session_state.answers)
         if a.get('question_index') == question_index),
        None,
    )
    if existing is None:
        st.session_state.answers.append(record)
        st.session_state.evaluations.append(evaluation)
    else:
        st.session_state.answers[existing] = record
        st.session_state.evaluations[existing] = evaluation

    if st.session_state.assessment_id is not None:
        try:
            db.record_answer(
                st.session_state.assessment_id, question_index, answer, evaluation
            )
        except Exception as exc:  # never lose an answer to a storage error
            logger.exception("Could not persist answer %d: %s", question_index, exc)

    # A new answer invalidates any report generated earlier.
    st.session_state.final_report = None
    st.session_state.show_evaluation = True
    st.session_state.last_submitted_question = question_index
    if not evaluation.get('degraded'):
        st.balloons()
    st.rerun()
