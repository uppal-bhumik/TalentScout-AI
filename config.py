import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration settings for TalentScout AI"""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    # Optional per-task model routing. Each falls back to OPENAI_MODEL so a
    # single OPENAI_MODEL setting is all that's needed for normal use.
    OPENAI_MODEL_QUESTIONS = os.getenv('OPENAI_MODEL_QUESTIONS') or OPENAI_MODEL
    OPENAI_MODEL_EVALUATION = os.getenv('OPENAI_MODEL_EVALUATION') or OPENAI_MODEL
    OPENAI_MODEL_REPORT = os.getenv('OPENAI_MODEL_REPORT') or OPENAI_MODEL

    # Request reliability. Retries are handled in LLMHandler._complete rather
    # than by the SDK, so the backoff is explicit and testable.
    OPENAI_TIMEOUT_SECONDS = float(os.getenv('OPENAI_TIMEOUT_SECONDS', '60'))
    OPENAI_MAX_RETRIES = int(os.getenv('OPENAI_MAX_RETRIES', '3'))
    OPENAI_RETRY_BASE_DELAY = float(os.getenv('OPENAI_RETRY_BASE_DELAY', '1.0'))
    OPENAI_RETRY_MAX_DELAY = float(os.getenv('OPENAI_RETRY_MAX_DELAY', '20.0'))

    # Persistence. SQLite by default; any SQLAlchemy URL works, so the same
    # code runs against Postgres in a hosted deployment.
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/talentscout.db')
    DATABASE_ECHO = os.getenv('DATABASE_ECHO', 'False').lower() == 'true'

    # Recruiter view - plain shared password, read from the environment. Left
    # unset, the recruiter view is hidden entirely.
    RECRUITER_PASSWORD = os.getenv('RECRUITER_PASSWORD')

    # Application Settings
    APP_NAME = "TalentScout AI"
    APP_VERSION = "2.1.0"
    APP_ENV = os.getenv('APP_ENV', 'development')
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

    # Logging Settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    LOG_FILE = os.getenv('LOG_FILE', 'logs/talentscout.log')
    
    # Validation Settings
    MAX_NAME_LENGTH = 50
    MIN_NAME_LENGTH = 2
    MAX_EMAIL_LENGTH = 254
    MAX_PHONE_LENGTH = 20
    MAX_LOCATION_LENGTH = 100
    MIN_LOCATION_LENGTH = 2
    MAX_TECH_STACK_ITEMS = 20
    MAX_ANSWER_LENGTH = 5000
    MIN_ANSWER_LENGTH = 10
    
    # Assessment Settings - Updated for 5-question limit
    MIN_QUESTIONS = 1  # Allow ending test after just 1 question
    MAX_QUESTIONS = 5  # Maximum 5 questions
    DEFAULT_QUESTIONS = 5  # Generate 5 questions by default
    QUESTION_TIMEOUT_SECONDS = 1800  # 30 minutes per question
    ALLOW_EARLY_COMPLETION = True  # Allow candidates to end test early
    MIN_QUESTIONS_FOR_EVALUATION = 1  # Minimum questions needed for evaluation
    
    # Scoring Settings
    MIN_SCORE = 1
    MAX_SCORE = 10
    PASSING_SCORE = 6
    
    # Early completion scoring adjustments
    EARLY_COMPLETION_PENALTY = {
        1: 0.8,  # 20% penalty for completing only 1 question
        2: 0.9,  # 10% penalty for completing only 2 questions
        3: 0.95, # 5% penalty for completing only 3 questions
        4: 0.98, # 2% penalty for completing only 4 questions
        5: 1.0   # No penalty for completing all 5 questions
    }
    
    # LLM Settings
    LLM_TEMPERATURE_QUESTIONS = 0.7
    LLM_TEMPERATURE_EVALUATION = 0.3
    LLM_TEMPERATURE_REPORT = 0.3
    LLM_MAX_TOKENS_QUESTIONS = 2000
    LLM_MAX_TOKENS_EVALUATION = 500
    LLM_MAX_TOKENS_REPORT = 1000
    
    # UI Settings
    SIDEBAR_WIDTH = 300
    MAIN_CONTENT_WIDTH = 800
    
    # Security Settings
    MAX_FAILED_ATTEMPTS = 3
    SESSION_TIMEOUT_MINUTES = 60
    
    # Predefined Technology Lists
    PROGRAMMING_LANGUAGES = [
        "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", 
        "Rust", "PHP", "Ruby", "Swift", "Kotlin", "Scala", "R", "MATLAB"
    ]
    
    FRONTEND_FRAMEWORKS = [
        "React", "Vue.js", "Angular", "Svelte", "Next.js", "Nuxt.js", 
        "Gatsby", "Ember.js", "Backbone.js", "jQuery"
    ]
    
    BACKEND_FRAMEWORKS = [
        "Node.js", "Express", "Django", "Flask", "FastAPI", "Spring Boot", 
        "ASP.NET", "Rails", "Laravel", "Symfony", "Gin", "Fiber"
    ]
    
    DATABASES = [
        "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch", 
        "Cassandra", "Oracle", "SQL Server", "SQLite", "DynamoDB"
    ]
    
    CLOUD_PLATFORMS = [
        "AWS", "Google Cloud", "Azure", "DigitalOcean", "Heroku", 
        "Vercel", "Netlify", "Firebase", "Supabase"
    ]
    
    DEVOPS_TOOLS = [
        "Docker", "Kubernetes", "Jenkins", "GitLab CI", "GitHub Actions", 
        "Terraform", "Ansible", "Chef", "Puppet", "Vagrant"
    ]
    
    @classmethod
    def get_all_technologies(cls):
        """Get all predefined technologies as a flat list"""
        return (
            cls.PROGRAMMING_LANGUAGES + 
            cls.FRONTEND_FRAMEWORKS + 
            cls.BACKEND_FRAMEWORKS + 
            cls.DATABASES + 
            cls.CLOUD_PLATFORMS + 
            cls.DEVOPS_TOOLS
        )
    
    @classmethod
    def get_technology_categories(cls):
        """Get technologies organized by category"""
        return {
            "Programming Languages": cls.PROGRAMMING_LANGUAGES,
            "Frontend Frameworks": cls.FRONTEND_FRAMEWORKS,
            "Backend Frameworks": cls.BACKEND_FRAMEWORKS,
            "Databases": cls.DATABASES,
            "Cloud Platforms": cls.CLOUD_PLATFORMS,
            "DevOps Tools": cls.DEVOPS_TOOLS
        }
    
    @classmethod
    def calculate_completion_adjusted_score(cls, avg_score: float, questions_completed: int) -> float:
        """Calculate score adjusted for early completion"""
        if questions_completed in cls.EARLY_COMPLETION_PENALTY:
            penalty_factor = cls.EARLY_COMPLETION_PENALTY[questions_completed]
            return round(avg_score * penalty_factor, 1)
        return avg_score
    
    @classmethod
    def get_completion_status(cls, questions_completed: int) -> str:
        """Get completion status based on questions answered"""
        if questions_completed == cls.MAX_QUESTIONS:
            return "Full Assessment Completed"
        elif questions_completed >= cls.MIN_QUESTIONS_FOR_EVALUATION:
            return f"Partial Assessment ({questions_completed}/{cls.MAX_QUESTIONS} questions)"
        else:
            return "Assessment Incomplete"
    
    @classmethod
    def validate_config(cls):
        """Validate configuration settings"""
        errors = []
        
        if not cls.OPENAI_API_KEY:
            errors.append(
                "OPENAI_API_KEY is missing. Copy .env.example to .env and add your key."
            )
        elif cls.OPENAI_API_KEY.startswith('sk-or-'):
            errors.append(
                "OPENAI_API_KEY looks like an OpenRouter key (sk-or-...), but this app "
                "now calls the OpenAI API directly. Use a key from "
                "https://platform.openai.com/api-keys"
            )

        if cls.MIN_QUESTIONS < 1:
            errors.append("MIN_QUESTIONS must be at least 1.")
        
        if cls.MAX_QUESTIONS < cls.MIN_QUESTIONS:
            errors.append("MAX_QUESTIONS must be greater than or equal to MIN_QUESTIONS.")
        
        if cls.DEFAULT_QUESTIONS < cls.MIN_QUESTIONS or cls.DEFAULT_QUESTIONS > cls.MAX_QUESTIONS:
            errors.append("DEFAULT_QUESTIONS must be between MIN_QUESTIONS and MAX_QUESTIONS.")
        
        if cls.MIN_SCORE >= cls.MAX_SCORE:
            errors.append("MIN_SCORE must be less than MAX_SCORE.")
        
        if cls.PASSING_SCORE < cls.MIN_SCORE or cls.PASSING_SCORE > cls.MAX_SCORE:
            errors.append("PASSING_SCORE must be between MIN_SCORE and MAX_SCORE.")
        
        if not all(0 < penalty <= 1 for penalty in cls.EARLY_COMPLETION_PENALTY.values()):
            errors.append("All EARLY_COMPLETION_PENALTY values must be between 0 and 1.")
        
        if cls.QUESTION_TIMEOUT_SECONDS <= 0:
            errors.append("QUESTION_TIMEOUT_SECONDS must be positive.")
        
        if cls.SESSION_TIMEOUT_MINUTES <= 0:
            errors.append("SESSION_TIMEOUT_MINUTES must be positive.")
        
        if cls.MAX_FAILED_ATTEMPTS <= 0:
            errors.append("MAX_FAILED_ATTEMPTS must be positive.")

        if cls.OPENAI_TIMEOUT_SECONDS <= 0:
            errors.append("OPENAI_TIMEOUT_SECONDS must be positive.")

        if cls.OPENAI_MAX_RETRIES < 0:
            errors.append("OPENAI_MAX_RETRIES cannot be negative.")

        if cls.OPENAI_RETRY_BASE_DELAY <= 0:
            errors.append("OPENAI_RETRY_BASE_DELAY must be positive.")

        if cls.OPENAI_RETRY_MAX_DELAY < cls.OPENAI_RETRY_BASE_DELAY:
            errors.append("OPENAI_RETRY_MAX_DELAY must be at least OPENAI_RETRY_BASE_DELAY.")

        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL must not be empty.")

        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
        
        return True

# Example usage
if __name__ == "__main__":
    try:
        Config.validate_config()
        print("✅ Configuration validated successfully.")
        print(f"📊 Early-completion penalties: {Config.EARLY_COMPLETION_PENALTY}")
        print(f"🧪 Default questions: {Config.DEFAULT_QUESTIONS}")
        print(f"🔐 Session timeout: {Config.SESSION_TIMEOUT_MINUTES} min")
    except ValueError as e:
        print(str(e))