"""TalentScout AI - Streamlit entry point.

Routes the candidate through the profile and assessment stages, and hosts the
recruiter dashboard (see recruiter_view.py). Everything a candidate does is
written to the database as it happens, so a refresh loses the UI state but not
the assessment.
"""

import json
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

import database as db
from config import Config
from conversation_manager import ConversationManager
from data_validator import DataValidator
from llm_handler import LLMHandler
from recruiter_view import recruiter_dashboard
from utils import ReportGenerator, get_logger, sanitize_filename

# Load environment variables from .env file
load_dotenv()

logger = get_logger("TalentScout.app")

STYLESHEET = Path(__file__).parent / "static" / "styles.css"

# Page configuration
st.set_page_config(
    page_title="TalentScout AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)


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


def load_stylesheet():
    """Inject the app's CSS, which lives in static/styles.css."""
    try:
        mtime = STYLESHEET.stat().st_mtime
    except OSError:
        mtime = 0.0

    css = _read_stylesheet(mtime)
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


load_stylesheet()

def initialize_session_state():
    """Initialize session state variables with proper state management"""
    if 'conversation_manager' not in st.session_state:
        st.session_state.conversation_manager = ConversationManager()
        st.session_state.llm_handler = LLMHandler()
        st.session_state.data_validator = DataValidator()
    
    if 'current_stage' not in st.session_state:
        st.session_state.current_stage = 'welcome'
    
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

    # FIXED: Better state management for preventing issues
    if 'current_answer' not in st.session_state:
        st.session_state.current_answer = ""
    
    if 'show_evaluation' not in st.session_state:
        st.session_state.show_evaluation = False
    
    if 'last_submitted_question' not in st.session_state:
        st.session_state.last_submitted_question = -1

def display_header():
    """Display the main header with enhanced styling"""
    st.markdown('<h1 class="main-header">🎯 TalentScout AI</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">INTELLIGENT  HIRING  ASSISTANT  FOR TECHNICAL  SCREENING</p>', unsafe_allow_html=True)
    st.markdown("---")

def display_candidate_profile():
    """Display candidate profile in sidebar with enhanced styling"""
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
            completed = len([k for k in ['name', 'email', 'phone', 'experience', 'location', 'tech_stack'] if k in data])
            progress = min(completed / 6 * 100, 100)
            
            st.progress(progress / 100)
            st.markdown(f'<p class="progress-text">Profile: {int(progress)}% Complete</p>', unsafe_allow_html=True)

def welcome_stage():
    """Welcome stage with enhanced design"""
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

def name_stage():
    """Collect candidate name"""
    st.markdown("### Let's start with your name")
    
    name = st.text_input("What's your full name?", key="name_input")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("Next ➡️", type="primary"):
            if name.strip():
                if st.session_state.data_validator.validate_name(name):
                    st.session_state.candidate_data['name'] = name.strip()
                    st.session_state.current_stage = 'email'
                    st.rerun()
                else:
                    st.error("Please enter a valid name (letters only, 2-50 characters)")
            else:
                st.error("Please enter your name")
    
    with col2:
        if st.button("⬅️ Back"):
            st.session_state.current_stage = 'welcome'
            st.rerun()

def email_stage():
    """Collect candidate email"""
    st.markdown("### What's your email address?")
    
    email = st.text_input("Email address", key="email_input")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("Next ➡️", type="primary"):
            if email.strip():
                if st.session_state.data_validator.validate_email(email):
                    st.session_state.candidate_data['email'] = email.strip().lower()
                    st.session_state.current_stage = 'phone'
                    st.rerun()
                else:
                    st.error("Please enter a valid email address")
            else:
                st.error("Please enter your email address")
    
    with col2:
        if st.button("⬅️ Back"):
            st.session_state.current_stage = 'name'
            st.rerun()

def phone_stage():
    """Collect candidate phone"""
    st.markdown("### What's your phone number?")
    
    phone = st.text_input("Phone number (with country code)", key="phone_input", placeholder="+91 9876543210")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("Next ➡️", type="primary"):
            if phone.strip():
                if st.session_state.data_validator.validate_phone(phone):
                    st.session_state.candidate_data['phone'] = phone.strip()
                    st.session_state.current_stage = 'experience'
                    st.rerun()
                else:
                    st.error("Please enter a valid phone number")
            else:
                st.error("Please enter your phone number")
    
    with col2:
        if st.button("⬅️ Back"):
            st.session_state.current_stage = 'email'
            st.rerun()

def experience_stage():
    """Collect candidate experience"""
    st.markdown("### How many years of professional experience do you have?")
    
    experience = st.selectbox(
        "Years of experience",
        options=[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 25, 30],
        key="experience_input"
    )
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("Next ➡️", type="primary"):
            st.session_state.candidate_data['experience'] = experience
            st.session_state.current_stage = 'location'
            st.rerun()
    
    with col2:
        if st.button("⬅️ Back"):
            st.session_state.current_stage = 'phone'
            st.rerun()

def location_stage():
    """Collect candidate location"""
    st.markdown("### Where are you currently located?")
    
    location = st.text_input("City, Country", key="location_input", placeholder="Delhi, India")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("Next ➡️", type="primary"):
            if location.strip():
                if st.session_state.data_validator.validate_location(location):
                    st.session_state.candidate_data['location'] = location.strip()
                    st.session_state.current_stage = 'tech_stack'
                    st.rerun()
                else:
                    st.error("Please enter a valid location")
            else:
                st.error("Please enter your location")
    
    with col2:
        if st.button("⬅️ Back"):
            st.session_state.current_stage = 'experience'
            st.rerun()
            # Part 3: Tech Stack Collection and Question Generation (FIXED)

def tech_stack_stage():
    """Collect candidate tech stack"""
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
        if st.button("⬅️ Back"):
            st.session_state.current_stage = 'location'
            st.rerun()

def generate_questions_stage():
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
    # FIXED: Reset assessment state for new question set
    st.session_state.current_answer = ""
    st.session_state.show_evaluation = False
    st.session_state.last_submitted_question = -1
    st.session_state.final_report = None
    st.rerun()


def degraded_questions_warning():
    """Tell the candidate when the questions are not personalised."""
    questions = st.session_state.get('technical_questions') or []
    degraded = next((q for q in questions if q.get('degraded')), None)
    if degraded:
        st.warning(
            "⚠️ **These questions are not personalised.** The question generator "
            f"could not be reached, so a generic set is being used. Reason: "
            f"{degraded.get('degraded_reason', 'unknown')}"
        )

# FIXED: Complete rewrite of technical assessment with proper state management
# FIXED: Complete rewrite of technical assessment with proper question display
def technical_assessment_stage():
    """FIXED: Conduct technical assessment with proper question progression and display"""
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
    
    # Control buttons row
    col_skip, col_end, col_spacer = st.columns([1, 1, 3])
    with col_skip:
        if st.button("⭐ Skip Question", help="Skip this question and move to next", key=f"skip_btn_{current_q_index}"):
            # FIXED: Proper skip logic - moves to next question immediately
            move_to_next_question()
    
    with col_end:
        if st.button("🚪 End Test Now", help="Get evaluation based on current progress", key=f"end_btn_{current_q_index}"):
            if st.session_state.answers:
                st.session_state.test_ended_early = True
                st.session_state.current_stage = 'final_evaluation'
                st.rerun()
            else:
                st.warning("Please answer at least one question to get an evaluation.")
    
    # FIXED: Display question with proper text extraction
    question_text = current_question.get("question", "Question not found")
    category = current_question.get("category", "General")
    difficulty = current_question.get("difficulty", "Intermediate")
    
    # Display question with enhanced styling
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
    
    # Debug info (remove this in production)
    # st.write(f"DEBUG - Question object: {current_question}")
    # st.write(f"DEBUG - Question text: '{question_text}'")
    
    # Show previous evaluations
    if st.session_state.evaluations:
        with st.expander("📊 Previous Question Reviews", expanded=False):
            for i, eval_data in enumerate(st.session_state.evaluations):
                score_color = "#4CAF50" if eval_data['score'] >= 7 else "#FF9800" if eval_data['score'] >= 5 else "#F44336"
                st.markdown(f'''
                <div class="evaluation-box">
                    <p><strong>Q{i+1} Evaluation:</strong></p>
                    <p><strong>Score:</strong> <span style="color: {score_color}; font-size: 1.2em;">{eval_data['score']}/10</span></p>
                    <p><strong>Feedback:</strong> {eval_data['feedback']}</p>
                </div>
                ''', unsafe_allow_html=True)
    
    # FIXED: Check if we should show evaluation for current question
    show_current_evaluation = (st.session_state.show_evaluation and 
                              st.session_state.last_submitted_question == current_q_index)
    
    if show_current_evaluation:
        # Display current evaluation and next button
        latest_evaluation = st.session_state.evaluations[-1]

        if latest_evaluation.get('degraded'):
            st.warning(
                "⚠️ **This answer could not be scored.** It has been recorded with a "
                "placeholder score of 5/10 and flagged for human review. Reason: "
                f"{latest_evaluation.get('degraded_reason', 'unknown')}"
            )

        score_color = "#4CAF50" if latest_evaluation['score'] >= 7 else "#FF9800" if latest_evaluation['score'] >= 5 else "#F44336"

        st.markdown(f'''
        <div class="evaluation-box">
            <h4>✅ Answer Submitted Successfully!</h4>
            <p><strong>Score:</strong> <span style="color: {score_color}; font-size: 1.3em;">{latest_evaluation['score']}/10</span></p>
            <p><strong>Feedback:</strong> {latest_evaluation['feedback']}</p>
        </div>
        ''', unsafe_allow_html=True)

        # Show next/finish button
        if current_q_index + 1 < total_questions:
            if st.button("Continue to Next Question ➡️", type="primary", key=f"next_question_btn_{current_q_index}"):
                move_to_next_question()
        else:
            st.markdown("### 🎉 Assessment Complete!")
            if st.button("Generate Final Report 📊", type="primary", key=f"final_report_btn_{current_q_index}"):
                st.session_state.current_stage = 'final_evaluation'
                st.rerun()
    else:
        # FIXED: Show answer input only when not showing evaluation
        # FIXED: Dynamic text area key that clears when moving to new question
        answer_key = f"answer_q_{current_q_index}"
        
        # FIXED: Clear text area value when showing a new question
        default_answer = st.session_state.current_answer if st.session_state.last_submitted_question != current_q_index else ""
        
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
                    # Check if user wants to skip
                    if answer.strip().lower() in ['not sure', 'skip', 'pass', 'idk', "i don't know"]:
                        st.info("Skipping this question...")
                        move_to_next_question()
                    else:
                        # FIXED: Store current answer and evaluate
                        st.session_state.current_answer = answer.strip()
                        evaluate_current_answer(current_question, answer.strip(), current_q_index)
                else:
                    st.error("Please provide an answer before submitting.")
        
        with col2:
            if current_q_index > 0:
                if st.button("⬅️ Previous", key=f"prev_btn_{current_q_index}"):
                    # FIXED: Proper previous question navigation
                    st.session_state.current_question_index = max(0, current_q_index - 1)
                    st.session_state.show_evaluation = False
                    st.session_state.current_answer = ""
                    st.rerun()

# FIXED: Helper function for moving to next question
def move_to_next_question():
    """FIXED: Helper function to properly advance to next question"""
    current_q_index = st.session_state.current_question_index
    total_questions = len(st.session_state.technical_questions)
    
    if current_q_index + 1 < total_questions:
        st.session_state.current_question_index += 1
        st.session_state.show_evaluation = False
        st.session_state.current_answer = ""  # FIXED: Clear answer for next question
        st.rerun()
    else:
        # All questions completed
        if st.session_state.answers:
            st.session_state.current_stage = 'final_evaluation'
            st.rerun()
        else:
            st.warning("Please answer at least one question to get an evaluation.")

def evaluate_current_answer(question, answer, question_index):
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

def reset_session():
    """Clear everything and go back to the welcome screen."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def score_colour(score: float) -> str:
    """Traffic-light colour for a 1-10 score."""
    if score >= 7:
        return "#4CAF50"
    return "#FF9800" if score >= 5 else "#F44336"


def final_evaluation_stage():
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

    # Generate the report once and keep it. Regenerating it on every rerun
    # would bill another API call for every button click on this page.
    if st.session_state.final_report is None:
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
            except Exception as exc:
                logger.exception("Could not persist the final report: %s", exc)
                st.warning(
                    "⚠️ This report could not be saved to the database. It is shown "
                    "below and can still be downloaded."
                )

    final_report = st.session_state.final_report

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


def render_report(final_report, candidate_data, answers, evaluations):
    """Render the score cards, analysis and per-question breakdown.

    Shared by the candidate's results page and the recruiter dashboard, so a
    stored assessment looks exactly like a live one.
    """
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


def render_downloads(final_report, candidate_data, answers, evaluations, extra=None):
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


def main():
    """Main application function with proper routing"""
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

    initialize_session_state()
    display_header()

    view = sidebar_navigation()
    if view == 'recruiter':
        recruiter_dashboard(render_report, render_downloads)
        return
    if view == 'locked':
        st.info("🔒 The recruiter dashboard is password protected.")
        return

    display_candidate_profile()

    # Route to appropriate stage
    current_stage = st.session_state.current_stage

    if current_stage == 'welcome':
        welcome_stage()
    elif current_stage == 'name':
        name_stage()
    elif current_stage == 'email':
        email_stage()
    elif current_stage == 'phone':
        phone_stage()
    elif current_stage == 'experience':
        experience_stage()
    elif current_stage == 'location':
        location_stage()
    elif current_stage == 'tech_stack':
        tech_stack_stage()
    elif current_stage == 'generate_questions':
        generate_questions_stage()
    elif current_stage == 'technical_assessment':
        technical_assessment_stage()
    elif current_stage == 'final_evaluation':
        final_evaluation_stage()
    else:
        # Fallback to welcome if unknown stage
        st.session_state.current_stage = 'welcome'
        st.rerun()

if __name__ == "__main__":
    main()