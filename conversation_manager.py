from datetime import datetime
from typing import Dict, List, Any, Optional

class ConversationManager:
    """Manages the conversation flow and state for TalentScout AI"""
    
    def __init__(self):
        self.conversation_stages = [
            'welcome',
            'name',
            'email', 
            'phone',
            'experience',
            'location',
            'tech_stack',
            'generate_questions',
            'technical_assessment',
            'final_evaluation'
        ]
        self.current_stage_index = 0
        self.candidate_data = {}
        self.conversation_history = []
    
    def get_current_stage(self) -> str:
        """Get the current conversation stage"""
        if self.current_stage_index < len(self.conversation_stages):
            return self.conversation_stages[self.current_stage_index]
        return 'completed'
    
    def move_to_next_stage(self) -> bool:
        """Move to the next conversation stage"""
        if self.current_stage_index < len(self.conversation_stages) - 1:
            self.current_stage_index += 1
            return True
        return False
    
    def move_to_previous_stage(self) -> bool:
        """Move to the previous conversation stage"""
        if self.current_stage_index > 0:
            self.current_stage_index -= 1
            return True
        return False
    
    def set_stage(self, stage: str) -> bool:
        """Set a specific conversation stage"""
        if stage in self.conversation_stages:
            self.current_stage_index = self.conversation_stages.index(stage)
            return True
        return False
    
    def update_candidate_data(self, key: str, value: Any) -> None:
        """Update candidate data"""
        self.candidate_data[key] = value
        self.log_interaction(f"Updated {key}", str(value))
    
    def get_candidate_data(self, key: str = None) -> Any:
        """Get candidate data"""
        if key:
            return self.candidate_data.get(key)
        return self.candidate_data
    
    def log_interaction(self, action: str, data: str = "") -> None:
        """Log conversation interactions"""
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'stage': self.get_current_stage(),
            'action': action,
            'data': data
        }
        self.conversation_history.append(interaction)
    
    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history"""
        return self.conversation_history
    
    def get_progress_percentage(self) -> float:
        """Get conversation progress as percentage"""
        # Exclude welcome and final stages from progress calculation
        data_collection_stages = ['name', 'email', 'phone', 'experience', 'location', 'tech_stack']
        completed_data_stages = sum(1 for stage in data_collection_stages if stage in self.candidate_data)
        return (completed_data_stages / len(data_collection_stages)) * 100
    
    def is_profile_complete(self) -> bool:
        """Check if candidate profile is complete"""
        required_fields = ['name', 'email', 'phone', 'experience', 'location', 'tech_stack']
        return all(field in self.candidate_data for field in required_fields)
    
    def reset_conversation(self) -> None:
        """Reset the conversation to initial state"""
        self.current_stage_index = 0
        self.candidate_data = {}
        self.conversation_history = []
        self.log_interaction("Conversation reset")
    
    def export_conversation_data(self) -> Dict:
        """Export all conversation data"""
        return {
            'candidate_data': self.candidate_data,
            'conversation_history': self.conversation_history,
            'current_stage': self.get_current_stage(),
            'progress_percentage': self.get_progress_percentage(),
            'exported_at': datetime.now().isoformat()
        }
    
    def import_conversation_data(self, data: Dict) -> bool:
        """Import conversation data"""
        try:
            self.candidate_data = data.get('candidate_data', {})
            self.conversation_history = data.get('conversation_history', [])
            current_stage = data.get('current_stage', 'welcome')
            self.set_stage(current_stage)
            return True
        except Exception as e:
            print(f"Error importing conversation data: {e}")
            return False
    
    def get_next_required_field(self) -> Optional[str]:
        """Get the next required field that needs to be collected"""
        required_fields = ['name', 'email', 'phone', 'experience', 'location', 'tech_stack']
        for field in required_fields:
            if field not in self.candidate_data:
                return field
        return None
    
    def validate_stage_completion(self, stage: str) -> bool:
        """Validate if a stage has been completed properly"""
        stage_requirements = {
            'name': lambda: 'name' in self.candidate_data and self.candidate_data['name'].strip(),
            'email': lambda: 'email' in self.candidate_data and self.candidate_data['email'].strip(),
            'phone': lambda: 'phone' in self.candidate_data and self.candidate_data['phone'].strip(),
            'experience': lambda: 'experience' in self.candidate_data,
            'location': lambda: 'location' in self.candidate_data and self.candidate_data['location'].strip(),
            'tech_stack': lambda: 'tech_stack' in self.candidate_data and len(self.candidate_data['tech_stack']) > 0
        }
        
        if stage in stage_requirements:
            return stage_requirements[stage]()
        return True
    
    def get_stage_prompt(self, stage: str) -> str:
        """Get appropriate prompt for each stage"""
        prompts = {
            'welcome': "Welcome! I'm TalentScout AI, your intelligent hiring assistant. Let's start with some basic information.",
            'name': "Could you please tell me your full name?",
            'email': "What's your email address?",
            'phone': "What's your phone number? (Please include country code)",
            'experience': "How many years of professional experience do you have?",
            'location': "Where are you currently located? (City, Country)",
            'tech_stack': "What technologies make up your primary tech stack? Please list the programming languages, frameworks, databases, and tools you're proficient in.",
            'generate_questions': "Based on your profile, I'm generating personalized technical questions...",
            'technical_assessment': "Let's begin the technical assessment. I'll ask you questions one by one.",
            'final_evaluation': "Assessment complete! Let me generate your final evaluation report."
        }
        return prompts.get(stage, "Let's continue...")
    
    def format_candidate_summary(self) -> str:
        """Format candidate data as a readable summary"""
        if not self.candidate_data:
            return "No candidate data available."
        
        summary = []
        
        if 'name' in self.candidate_data:
            summary.append(f"Name: {self.candidate_data['name']}")
        
        if 'email' in self.candidate_data:
            summary.append(f"Email: {self.candidate_data['email']}")
        
        if 'phone' in self.candidate_data:
            summary.append(f"Phone: {self.candidate_data['phone']}")
        
        if 'experience' in self.candidate_data:
            exp = self.candidate_data['experience']
            exp_text = f"{exp} year{'s' if exp != 1 else ''}"
            summary.append(f"Experience: {exp_text}")
        
        if 'location' in self.candidate_data:
            summary.append(f"Location: {self.candidate_data['location']}")
        
        if 'tech_stack' in self.candidate_data:
            tech_list = ', '.join(self.candidate_data['tech_stack'])
            summary.append(f"Tech Stack: {tech_list}")
        
        return '\n'.join(summary)