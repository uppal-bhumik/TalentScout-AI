# main_app.py - Part 1: Imports and Enhanced CSS (FIXED)

import streamlit as st
import json
from datetime import datetime
from conversation_manager import ConversationManager
from llm_handler import LLMHandler
from data_validator import DataValidator
from config import Config
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="TalentScout AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# FIXED: Enhanced CSS with proper text visibility and contrast
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .stApp {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    
    /* Main container with glassmorphism effect */
    .main .block-container {
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 20px;
        padding: 2rem;
        margin-top: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    
    /* Header styles with better contrast */
    .main-header {
        text-align: center;
        background: linear-gradient(45deg, #FFD700, #FF6B6B, #4ECDC4, #45B7D1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .sub-header {
    text-align: center;
    color: #000000; /* Set text color to black */
    font-size: 2rem;
    word-spacing: 7px;
    font-weight: 700;
    margin-bottom: 1rem;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}
    
    /* Card styles with better visibility */
    .candidate-info {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(20px);
        padding: 1.5rem;
        border-radius: 15px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        margin-bottom: 1rem;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
        color: white !important;
    }
    
    .question-box {
        background: rgba(70, 130, 255, 0.2);
        backdrop-filter: blur(15px);
        padding: 2rem;
        border-radius: 15px;
        border: 2px solid rgba(70, 130, 255, 0.4);
        margin-bottom: 1.5rem;
        box-shadow: 0 6px 25px rgba(70, 130, 255, 0.3);
        color: white !important;
    }
    
    .evaluation-box {
        background: rgba(76, 175, 80, 0.2);
        backdrop-filter: blur(15px);
        padding: 1.5rem;
        border-radius: 15px;
        border: 2px solid rgba(76, 175, 80, 0.4);
        margin-bottom: 1rem;
        box-shadow: 0 6px 25px rgba(76, 175, 80, 0.3);
        color: white !important;
    }
    
    .final-report-box {
        background: rgba(255, 193, 7, 0.2);
        backdrop-filter: blur(15px);
        padding: 2rem;
        border-radius: 15px;
        border: 2px solid rgba(255, 193, 7, 0.4);
        margin-bottom: 1rem;
        box-shadow: 0 8px 30px rgba(255, 193, 7, 0.3);
        color: white !important;
    }
    
    .end-test-box {
        background: rgba(255, 87, 51, 0.2);
        backdrop-filter: blur(15px);
        padding: 1.5rem;
        border-radius: 15px;
        border: 2px solid rgba(255, 87, 51, 0.4);
        margin-bottom: 1rem;
        box-shadow: 0 6px 25px rgba(255, 87, 51, 0.3);
        color: white !important;
    }
    
    /* Progress styles with better visibility */
    .progress-text {
        text-align: center;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.95) !important;
        margin-top: 0.5rem;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
    }
    
    /* FIXED: Button styling with perfect visibility */
    .stButton > button {
        background: linear-gradient(45deg, #667eea, #764ba2) !important;
        color: #ffffff !important;
        border: 2px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 10px !important;
        padding: 0.5rem 2rem !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3) !important;
        min-height: 2.5rem !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3) !important;
        background: linear-gradient(45deg, #5a6fd8, #6b42a6) !important;
        color: #ffffff !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.4) !important;
    }
    
    .stButton > button:focus {
        color: #ffffff !important;
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.4) !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3) !important;
    }
    
    .stButton > button:active {
        color: #ffffff !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3) !important;
    }
    
    /* FIXED: Text input with perfect black text on white background */
    .stTextInput > div > div > input {
    background: #ffffff !important;
    backdrop-filter: none !important;
    border: 2px solid rgba(102, 126, 234, 0.4) !important;
    border-radius: 10px !important;
    color: #000000 !important;
    font-weight: 500 !important;
    font-size: 16px !important;
    padding: 12px 16px !important;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1) !important;
}
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2) !important;
        color: #000000 !important;
        outline: none !important;
        background: #ffffff !important;
    }
    
    .stTextInput > div > div > input::placeholder {
        color: #666666 !important;
        opacity: 0.7 !important;
    }
    
    /* FIXED: TextArea with perfect black text on white background */
    .stTextArea > div > div > textarea {
        background: #ffffff !important;
        backdrop-filter: none !important;
        border: 2px solid rgba(102, 126, 234, 0.4) !important;
        border-radius: 10px !important;
        color: #000000 !important;
        font-weight: 500 !important;
        font-size: 16px !important;
        padding: 12px 16px !important;
        line-height: 1.5 !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1) !important;
        resize: vertical !important;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2) !important;
        color: #000000 !important;
        outline: none !important;
        background: #ffffff !important;
    }
    
    .stTextArea > div > div > textarea::placeholder {
        color: #666666 !important;
        opacity: 0.7 !important;
        font-style: italic !important;
    }

/* FIXED: Selectbox with perfect black text on white background */
.stSelectbox > div > div > select {
    background: #ffffff !important;
    backdrop-filter: none !important;
    border: 2px solid rgba(102, 126, 234, 0.4) !important;
    border-radius: 10px !important;
    color: #000000 !important;
    font-weight: 500 !important;
    font-size: 16px !important;
    padding: 8px 12px !important;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1) !important;
}

.stSelectbox > div > div > select option {
    background: #ffffff !important;
    color: #000000 !important;
}
    
    .stSelectbox > div > div > select:focus {
        color: #000000 !important;
        border-color: #667eea !important;
        outline: none !important;
        background: #ffffff !important;
    }
    
    .stSelectbox > div > div > select option {
        background: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Checkbox styling with better visibility */
    .stCheckbox {
        color: rgba(255, 255, 255, 0.95) !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
    }
    
    .stCheckbox > label {
        color: rgba(255, 255, 255, 0.95) !important;
        font-weight: 500 !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
    }
    
    /* Input labels with better visibility */
    .stTextInput > label,
    .stTextArea > label,
    .stSelectbox > label,
    .stNumberInput > label {
        color: rgba(255, 255, 255, 0.95) !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        margin-bottom: 0.5rem !important;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(20px);
    }
    
    /* Metric styles with better visibility */
    .metric-card {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(20px);
        padding: 1.5rem;
        border-radius: 15px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
        color: white !important;
    }
    
    /* Text color overrides for better readability */
    .stMarkdown, .stText, p, span, div {
        color: rgba(255, 255, 255, 0.95) !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: rgba(255, 255, 255, 0.95) !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
    }
    
    /* Progress bar styling */
    .stProgress .st-bo {
        background-color: rgba(255, 255, 255, 0.3);
    }
    
    .stProgress .st-bp {
        background-color: #4CAF50;
    }
    
    /* Alert and message styling */
    .stAlert, .stSuccess, .stError, .stWarning, .stInfo {
        background: rgba(255, 255, 255, 0.15) !important;
        backdrop-filter: blur(15px) !important;
        border-radius: 10px !important;
        border: 2px solid rgba(255, 255, 255, 0.3) !important;
        color: white !important;
    }
    
    .stAlert [data-baseweb="notification"], 
    .stSuccess [data-baseweb="notification"], 
    .stError [data-baseweb="notification"], 
    .stWarning [data-baseweb="notification"], 
    .stInfo [data-baseweb="notification"] {
        background: transparent !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)
# Part 2: Session State Initialization and Helper Functions (FIXED)

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
        if questions:
            # Cap at the configured question count
            st.session_state.technical_questions = questions[:Config.DEFAULT_QUESTIONS]
            st.session_state.current_stage = 'technical_assessment'
            st.session_state.current_question_index = 0
            # FIXED: Reset assessment state for new question set
            st.session_state.current_answer = ""
            st.session_state.show_evaluation = False
            st.session_state.last_submitted_question = -1
            st.success(f"Generated {len(st.session_state.technical_questions)} personalized questions!")
            st.rerun()
        else:
            st.error("Failed to generate questions. Please try again.")
            if st.button("Try Again"):
                st.rerun()

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

# FIXED: Separate function for answer evaluation
def evaluate_current_answer(question, answer, question_index):
    """FIXED: Evaluate the current answer and update state properly"""
    with st.spinner("Evaluating your answer..."):
        evaluation = st.session_state.llm_handler.evaluate_answer(
            question,
            answer,
            st.session_state.candidate_data
        )
        
        if evaluation:
            # Store answer and evaluation
            st.session_state.answers.append({
                'question': question['question'],
                'answer': answer,
                'category': question.get('category', 'General')
            })
            st.session_state.evaluations.append(evaluation)
            
            # FIXED: Set flags to show evaluation
            st.session_state.show_evaluation = True
            st.session_state.last_submitted_question = question_index
            st.balloons()
            st.rerun()
        else:
            st.error("Failed to evaluate answer. Please try again.")

# Part 5: Final Evaluation Stage and Main Function (COMPLETE)

def final_evaluation_stage():
    """Show final evaluation and results with enhanced design"""
    st.markdown("### 🎉 Assessment Complete!")
    
    # Check if test was ended early
    if st.session_state.test_ended_early:
        st.markdown(f"""
        <div class="end-test-box">
            <p><strong>⚡ Test ended early by candidate choice</strong></p>
            <p>Evaluation based on {len(st.session_state.answers)} completed question(s)</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("Thank you for completing the technical assessment. Here's your comprehensive evaluation:")
    
    # Generate final report
    if st.session_state.evaluations:  # Only generate if there are evaluations
        with st.spinner("Generating your final report..."):
            final_report = st.session_state.llm_handler.generate_final_report(
                st.session_state.candidate_data,
                st.session_state.answers,
                st.session_state.evaluations
            )
            
            if final_report:
                # Display results with enhanced metrics cards
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    # Show the completion adjustment rather than silently
                    # applying it, so the candidate can see how it was reached.
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
                        <p style="font-size: 2em; font-weight: bold; color: white; margin-bottom: 0;">{len(st.session_state.answers)}/{Config.DEFAULT_QUESTIONS}</p>
                        <p style="font-size: 0.75em; color: #CFE8F3; margin: 0;">{final_report.get('completion_status', '')}</p>
                    </div>
                    ''', unsafe_allow_html=True)
                
                with col3:
                    rec_color = "#90EE90" if "Strong Hire" in final_report['recommendation'] else "#FFB6C1" if "Hire" in final_report['recommendation'] else "#FFA07A"
                    st.markdown(f'''
                    <div class="metric-card">
                        <h3 style="color: #DDA0DD;">🎯 Recommendation</h3>
                        <p style="font-size: 1.2em; font-weight: bold; color: {rec_color};">{final_report['recommendation']}</p>
                    </div>
                    ''', unsafe_allow_html=True)
                
                # Detailed feedback with enhanced styling
                st.markdown("### 📈 Detailed Analysis")
                st.markdown(f'''
                <div class="final-report-box">
                    <p style="color: white; font-size: 1.1em; line-height: 1.6;">{final_report['detailed_feedback']}</p>
                </div>
                ''', unsafe_allow_html=True)
                
                # Individual question breakdown
                if st.session_state.answers and st.session_state.evaluations:
                    st.markdown("### 🔍 Question-wise Breakdown")
                    for i, (answer, evaluation) in enumerate(zip(st.session_state.answers, st.session_state.evaluations)):
                        score_color = "#4CAF50" if evaluation['score'] >= 7 else "#FF9800" if evaluation['score'] >= 5 else "#F44336"
                        with st.expander(f"Question {i+1}: {evaluation['score']}/10", expanded=False):
                            st.markdown(f"**Question:** {answer['question']}")
                            st.markdown(f"**Category:** {answer.get('category', 'General').title()}")
                            st.markdown(f"**Your Answer:** {answer['answer']}")
                            st.markdown(f"**Score:** <span style='color: {score_color}; font-weight: bold;'>{evaluation['score']}/10</span>", unsafe_allow_html=True)
                            st.markdown(f"**Feedback:** {evaluation['feedback']}")
                
                # Save results
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                results = {
                    'candidate_data': st.session_state.candidate_data,
                    'answers': st.session_state.answers,
                    'evaluations': st.session_state.evaluations,
                    'final_report': final_report,
                    'test_ended_early': st.session_state.test_ended_early,
                    'questions_answered': len(st.session_state.answers),
                    'total_questions_generated': len(st.session_state.technical_questions),
                    'timestamp': timestamp
                }
                
                # Download results
                st.download_button(
                    label="📄 Download Full Report",
                    data=json.dumps(results, indent=2),
                    file_name=f"assessment_report_{st.session_state.candidate_data.get('name', 'candidate').replace(' ', '_')}_{timestamp}.json",
                    mime="application/json"
                )
                
                # Restart option
                st.markdown("---")
                col_restart1, col_restart2 = st.columns([1, 4])
                with col_restart1:
                    if st.button("🔄 Start New Assessment"):
                        # Clear all session state
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        st.rerun()
                
            else:
                st.error("Failed to generate final report. Please try again.")
                if st.button("Try Again"):
                    st.rerun()
    
    else:
        # Handle case where no questions were answered
        st.warning("No questions were answered. Assessment cannot be completed.")
        if st.button("🔄 Start Over"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

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

    initialize_session_state()
    display_header()
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