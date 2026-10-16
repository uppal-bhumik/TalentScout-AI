import re
from typing import List, Dict, Any, Optional
import phonenumbers
from email_validator import validate_email, EmailNotValidError

class DataValidator:
    """Validates user input data for the TalentScout AI application"""
    
    def __init__(self):
        # Common patterns for validation
        self.name_pattern = re.compile(r'^[a-zA-Z\s\-\'\.]{2,50}$')
        self.location_pattern = re.compile(r'^[a-zA-Z\s\-\',\.]{2,100}$')
        
        # Blocked/suspicious patterns
        self.blocked_patterns = [
            r'test\s*\d*',
            r'admin',
            r'null',
            r'undefined',
            r'<.*>',  # HTML tags
            r'[{}()\[\]]',  # Special characters that might indicate injection
        ]
    
    def validate_name(self, name: str) -> bool:
        """Validate candidate name"""
        if not name or not name.strip():
            return False
        
        name = name.strip()
        
        # Check length
        if len(name) < 2 or len(name) > 50:
            return False
        
        # Check for blocked patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, name, re.IGNORECASE):
                return False
        
        # Check format (letters, spaces, hyphens, apostrophes, dots only)
        if not self.name_pattern.match(name):
            return False
        
        # Should not be all spaces or special characters
        if not re.search(r'[a-zA-Z]', name):
            return False
        
        # Should not start or end with special characters
        if name.startswith(('-', "'", '.')) or name.endswith(('-', "'", '.')):
            return False
        
        return True
    
    def validate_email(self, email: str) -> bool:
        """Validate email address"""
        if not email or not email.strip():
            return False
        
        email = email.strip().lower()
        
        # Check for blocked patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, email, re.IGNORECASE):
                return False
        
        # Basic format check first
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False
        
        # Use email-validator for comprehensive validation
        try:
            validate_email(email)
            return True
        except EmailNotValidError:
            return False
        except Exception:
            # Fallback to basic validation if email-validator fails
            return self._basic_email_validation(email)
    
    def _basic_email_validation(self, email: str) -> bool:
        """Basic email validation fallback"""
        # More strict pattern for fallback
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9._%-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_phone(self, phone: str) -> bool:
        """Validate phone number"""
        if not phone or not phone.strip():
            return False
        
        phone = phone.strip()
        
        # Check for blocked patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, phone, re.IGNORECASE):
                return False
        
        try:
            # Use phonenumbers library for comprehensive validation
            parsed_number = phonenumbers.parse(phone, None)
            return phonenumbers.is_valid_number(parsed_number)
        except Exception:
            # Fallback to basic validation
            return self._basic_phone_validation(phone)
    
    def _basic_phone_validation(self, phone: str) -> bool:
        """Basic phone validation fallback"""
        # Remove common separators and spaces
        clean_phone = re.sub(r'[\s\-\(\)\+]', '', phone)
        
        # Should contain only digits after cleaning
        if not clean_phone.isdigit():
            return False
        
        # Should be between 7 and 15 digits (international standard)
        if len(clean_phone) < 7 or len(clean_phone) > 15:
            return False
        
        return True
    
    def validate_experience(self, experience: Any) -> bool:
        """Validate experience years"""
        try:
            exp = float(experience)
            return 0 <= exp <= 50  # Reasonable range
        except (ValueError, TypeError):
            return False
    
    def validate_location(self, location: str) -> bool:
        """Validate location string"""
        if not location or not location.strip():
            return False
        
        location = location.strip()
        
        # Check length
        if len(location) < 2 or len(location) > 100:
            return False
        
        # Check for blocked patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, location, re.IGNORECASE):
                return False
        
        # Check format (letters, spaces, hyphens, apostrophes, commas, dots only)
        if not self.location_pattern.match(location):
            return False
        
        # Should contain at least one letter
        if not re.search(r'[a-zA-Z]', location):
            return False
        
        return True
    
    def validate_tech_stack(self, tech_stack: List[str]) -> bool:
        """Validate technology stack list"""
        if not tech_stack or not isinstance(tech_stack, list):
            return False
        
        if len(tech_stack) > 20:  # Reasonable upper limit
            return False
        
        for tech in tech_stack:
            if not self.validate_technology_name(tech):
                return False
        
        return True
    
    def validate_technology_name(self, tech_name: str) -> bool:
        """Validate individual technology name"""
        if not tech_name or not tech_name.strip():
            return False
        
        tech_name = tech_name.strip()
        
        # Check length
        if len(tech_name) < 1 or len(tech_name) > 30:
            return False
        
        # Check for blocked patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, tech_name, re.IGNORECASE):
                return False
        
        # Allow letters, numbers, spaces, dots, hyphens, plus signs
        if not re.match(r'^[a-zA-Z0-9\s\.\-\+#]+$', tech_name):
            return False
        
        return True
    
    def validate_answer(self, answer: str) -> bool:
        """Validate technical answer"""
        if not answer or not answer.strip():
            return False
        
        answer = answer.strip()
        
        # Check minimum length (should be substantial)
        if len(answer) < 10:
            return False
        
        # Check maximum length (reasonable upper bound)
        if len(answer) > 5000:
            return False
        
        # Check for blocked patterns (but be more lenient for technical content)
        suspicious_patterns = [
            r'<script.*?>.*?</script>',  # Script tags
            r'javascript:',  # Javascript protocol
            r'data:.*base64',  # Base64 data URIs
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, answer, re.IGNORECASE):
                return False
        
        return True
    
    def sanitize_input(self, input_str: str) -> str:
        """Sanitize input string"""
        if not input_str:
            return ""
        
        # Strip whitespace
        sanitized = input_str.strip()
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Limit length
        sanitized = sanitized[:1000]  # General limit
        
        return sanitized
    
    def validate_json_data(self, data: Dict) -> Dict:
        """Validate and sanitize JSON data"""
        validated_data = {}
        
        # Validate each field
        if 'name' in data:
            name = self.sanitize_input(str(data['name']))
            if self.validate_name(name):
                validated_data['name'] = name
        
        if 'email' in data:
            email = self.sanitize_input(str(data['email']))
            if self.validate_email(email):
                validated_data['email'] = email.lower()
        
        if 'phone' in data:
            phone = self.sanitize_input(str(data['phone']))
            if self.validate_phone(phone):
                validated_data['phone'] = phone
        
        if 'experience' in data:
            if self.validate_experience(data['experience']):
                validated_data['experience'] = float(data['experience'])
        
        if 'location' in data:
            location = self.sanitize_input(str(data['location']))
            if self.validate_location(location):
                validated_data['location'] = location
        
        if 'tech_stack' in data and isinstance(data['tech_stack'], list):
            validated_tech_stack = []
            for tech in data['tech_stack']:
                tech_name = self.sanitize_input(str(tech))
                if self.validate_technology_name(tech_name):
                    validated_tech_stack.append(tech_name)
            
            if validated_tech_stack:
                validated_data['tech_stack'] = validated_tech_stack
        
        return validated_data
    
    def get_validation_errors(self, data: Dict) -> List[str]:
        """Get list of validation errors for given data"""
        errors = []
        
        if 'name' in data:
            if not self.validate_name(data['name']):
                errors.append("Name must be 2-50 characters long and contain only letters, spaces, hyphens, and apostrophes")
        
        if 'email' in data:
            if not self.validate_email(data['email']):
                errors.append("Please provide a valid email address")
        
        if 'phone' in data:
            if not self.validate_phone(data['phone']):
                errors.append("Please provide a valid phone number with country code")
        
        if 'experience' in data:
            if not self.validate_experience(data['experience']):
                errors.append("Experience must be a number between 0 and 50")
        
        if 'location' in data:
            if not self.validate_location(data['location']):
                errors.append("Location must be 2-100 characters long and contain valid location characters")
        
        if 'tech_stack' in data:
            if not self.validate_tech_stack(data['tech_stack']):
                errors.append("Please provide a valid list of technologies (max 20 items)")
        
        return errors
    
    def is_valid_candidate_profile(self, data: Dict) -> bool:
        """Check if candidate profile is completely valid"""
        required_fields = ['name', 'email', 'phone', 'experience', 'location', 'tech_stack']
        
        # Check if all required fields are present
        for field in required_fields:
            if field not in data:
                return False
        
        # Validate each field
        return (
            self.validate_name(data['name']) and
            self.validate_email(data['email']) and
            self.validate_phone(data['phone']) and
            self.validate_experience(data['experience']) and
            self.validate_location(data['location']) and
            self.validate_tech_stack(data['tech_stack'])
        )