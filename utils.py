import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import streamlit as st

from config import Config

class Logger:
    """Custom logger for TalentScout AI"""
    
    def __init__(self, name: str = "TalentScout"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))

        if not self.logger.handlers:
            # Create console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # Create file handler - the log directory may not exist yet
            log_path = Config.LOG_FILE
            log_dir = os.path.dirname(log_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def debug(self, message: str):
        self.logger.debug(message)

class FileManager:
    """Handles file operations for saving and loading data"""
    
    def __init__(self, base_directory: str = None):
        base_directory = base_directory or Config.RESULTS_FOLDER
        self.base_directory = base_directory
        self.ensure_directory_exists()
    
    def ensure_directory_exists(self):
        """Ensure the base directory exists"""
        if not os.path.exists(self.base_directory):
            os.makedirs(self.base_directory)
    
    def save_assessment_results(self, candidate_data: Dict, results: Dict) -> str:
        """Save assessment results to a JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        candidate_name = candidate_data.get('name', 'unknown').replace(' ', '_')
        filename = f"assessment_{candidate_name}_{timestamp}.json"
        filepath = os.path.join(self.base_directory, filename)
        
        data_to_save = {
            'candidate_data': candidate_data,
            'results': results,
            'timestamp': timestamp,
            'saved_at': datetime.now().isoformat()
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            return filepath
        except Exception as e:
            logging.error(f"Error saving assessment results: {e}")
            return None
    
    def load_assessment_results(self, filepath: str) -> Optional[Dict]:
        """Load assessment results from a JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading assessment results: {e}")
            return None
    
    def list_assessment_files(self) -> List[str]:
        """List all assessment result files"""
        try:
            files = [f for f in os.listdir(self.base_directory) if f.endswith('.json')]
            return sorted(files, reverse=True)  # Most recent first
        except Exception as e:
            logging.error(f"Error listing assessment files: {e}")
            return []

class SessionManager:
    """Manages Streamlit session state"""
    
    @staticmethod
    def initialize_session():
        """Initialize session state with default values"""
        default_values = {
            'conversation_manager': None,
            'llm_handler': None,
            'data_validator': None,
            'current_stage': 'welcome',
            'candidate_data': {},
            'technical_questions': [],
            'current_question_index': 0,
            'answers': [],
            'evaluations': [],
            'session_start_time': datetime.now(),
            'last_activity': datetime.now()
        }
        
        for key, value in default_values.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    @staticmethod
    def update_last_activity():
        """Update last activity timestamp"""
        st.session_state.last_activity = datetime.now()
    
    @staticmethod
    def get_session_duration() -> int:
        """Get session duration in minutes"""
        if 'session_start_time' not in st.session_state:
            return 0
        
        duration = datetime.now() - st.session_state.session_start_time
        return int(duration.total_seconds() / 60)
    
    @staticmethod
    def clear_session():
        """Clear all session state"""
        for key in list(st.session_state.keys()):
            del st.session_state[key]
    
    @staticmethod
    def export_session_data() -> Dict:
        """Export session data for backup"""
        return {
            'candidate_data': st.session_state.get('candidate_data', {}),
            'current_stage': st.session_state.get('current_stage', 'welcome'),
            'answers': st.session_state.get('answers', []),
            'evaluations': st.session_state.get('evaluations', []),
            'current_question_index': st.session_state.get('current_question_index', 0),
            'exported_at': datetime.now().isoformat()
        }

class ReportGenerator:
    """Generates various types of reports"""
    
    @staticmethod
    def generate_html_report(candidate_data: Dict, answers: List[Dict], 
                           evaluations: List[Dict], final_report: Dict) -> str:
        """Generate an HTML report"""
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>TalentScout AI Assessment Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #2E86AB; color: white; padding: 20px; text-align: center; }}
                .candidate-info {{ background-color: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; }}
                .question-block {{ margin: 20px 0; padding: 15px; border-left: 4px solid #2196f3; background-color: #e3f2fd; }}
                .evaluation-block {{ margin: 10px 0; padding: 15px; border-left: 4px solid #9c27b0; background-color: #f3e5f5; }}
                .final-report {{ background-color: #e8f5e8; padding: 20px; margin: 20px 0; border-radius: 8px; }}
                .score {{ font-size: 24px; font-weight: bold; color: #4caf50; }}
                .recommendation {{ font-size: 20px; font-weight: bold; color: #ff5722; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎯 TalentScout AI Assessment Report</h1>
                <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
            
            <div class="candidate-info">
                <h2>👤 Candidate Information</h2>
                <p><strong>Name:</strong> {candidate_data.get('name', 'N/A')}</p>
                <p><strong>Email:</strong> {candidate_data.get('email', 'N/A')}</p>
                <p><strong>Phone:</strong> {candidate_data.get('phone', 'N/A')}</p>
                <p><strong>Experience:</strong> {candidate_data.get('experience', 'N/A')} years</p>
                <p><strong>Location:</strong> {candidate_data.get('location', 'N/A')}</p>
                <p><strong>Tech Stack:</strong> {', '.join(candidate_data.get('tech_stack', []))}</p>
            </div>
            
            <div class="final-report">
                <h2>📊 Final Assessment</h2>
                <div class="score">Overall Score: {final_report.get('overall_score', 'N/A')}/10</div>
                <div class="recommendation">Recommendation: {final_report.get('recommendation', 'N/A')}</div>
                <p><strong>Analysis:</strong> {final_report.get('detailed_feedback', 'No analysis available.')}</p>
            </div>
            
            <h2>📝 Question-wise Performance</h2>
        """
        
        # Add questions and evaluations
        for i, (answer, evaluation) in enumerate(zip(answers, evaluations)):
            html_template += f"""
            <div class="question-block">
                <h3>Question {i+1}</h3>
                <p><strong>Question:</strong> {answer['question']}</p>
                <p><strong>Category:</strong> {answer.get('category', 'General')}</p>
                <p><strong>Answer:</strong> {answer['answer']}</p>
            </div>
            <div class="evaluation-block">
                <p><strong>Score:</strong> {evaluation['score']}/10</p>
                <p><strong>Feedback:</strong> {evaluation['feedback']}</p>
            </div>
            """
        
        html_template += """
        </body>
        </html>
        """
        
        return html_template
    
    @staticmethod
    def generate_csv_summary(candidate_data: Dict, evaluations: List[Dict]) -> str:
        """Generate a CSV summary of the assessment"""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Metric', 'Value'])
        
        # Candidate info
        writer.writerow(['Name', candidate_data.get('name', 'N/A')])
        writer.writerow(['Email', candidate_data.get('email', 'N/A')])
        writer.writerow(['Experience', f"{candidate_data.get('experience', 'N/A')} years"])
        writer.writerow(['Location', candidate_data.get('location', 'N/A')])
        writer.writerow(['Tech Stack', ', '.join(candidate_data.get('tech_stack', []))])
        
        # Assessment results
        writer.writerow(['Total Questions', len(evaluations)])
        if evaluations:
            avg_score = sum(eval_data['score'] for eval_data in evaluations) / len(evaluations)
            writer.writerow(['Average Score', f"{avg_score:.1f}/10"])
        
        writer.writerow(['Assessment Date', datetime.now().strftime("%Y-%m-%d")])
        
        return output.getvalue()

class ProgressTracker:
    """Tracks user progress through the assessment"""
    
    def __init__(self):
        self.stages = [
            'welcome', 'name', 'email', 'phone', 'experience', 
            'location', 'tech_stack', 'generate_questions', 
            'technical_assessment', 'final_evaluation'
        ]
    
    def get_progress_percentage(self, current_stage: str) -> float:
        """Get progress percentage based on current stage"""
        try:
            current_index = self.stages.index(current_stage)
            return (current_index / (len(self.stages) - 1)) * 100
        except ValueError:
            return 0
    
    def get_next_stage(self, current_stage: str) -> Optional[str]:
        """Get the next stage"""
        try:
            current_index = self.stages.index(current_stage)
            if current_index < len(self.stages) - 1:
                return self.stages[current_index + 1]
        except ValueError:
            pass
        return None
    
    def get_previous_stage(self, current_stage: str) -> Optional[str]:
        """Get the previous stage"""
        try:
            current_index = self.stages.index(current_stage)
            if current_index > 0:
                return self.stages[current_index - 1]
        except ValueError:
            pass
        return None

class ErrorHandler:
    """Handles errors gracefully"""
    
    @staticmethod
    def handle_api_error(error: Exception, context: str = "API call") -> str:
        """Handle API-related errors"""
        error_message = f"Error in {context}: {str(error)}"
        logging.error(error_message)
        
        if "rate_limit" in str(error).lower():
            return "Rate limit exceeded. Please wait a moment and try again."
        elif "authentication" in str(error).lower():
            return "Authentication error. Please check your API key."
        elif "timeout" in str(error).lower():
            return "Request timed out. Please try again."
        else:
            return "An unexpected error occurred. Please try again later."
    
    @staticmethod
    def handle_validation_error(field: str, value: Any) -> str:
        """Handle validation errors"""
        return f"Invalid {field}: {value}. Please provide a valid {field}."
    
    @staticmethod
    def handle_session_error() -> str:
        """Handle session-related errors"""
        return "Session error occurred. Please refresh the page and start again."

# Initialize logger
logger = Logger()

# Utility functions
def format_time_duration(seconds: int) -> str:
    """Format time duration in human-readable format"""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    # Trim underscores from edges
    filename = filename.strip('_')
    return filename

def calculate_assessment_metrics(evaluations: List[Dict]) -> Dict:
    """Calculate various assessment metrics"""
    if not evaluations:
        return {}
    
    scores = [eval_data['score'] for eval_data in evaluations]
    
    return {
        'total_questions': len(evaluations),
        'average_score': sum(scores) / len(scores),
        'highest_score': max(scores),
        'lowest_score': min(scores),
        'passing_questions': len([score for score in scores if score >= 6]),
        'pass_rate': len([score for score in scores if score >= 6]) / len(scores) * 100
    }