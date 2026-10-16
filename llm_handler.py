import openai
import json
from typing import Dict, List, Any, Optional
import random
import re

from config import Config

class LLMHandler:
    """Handles all LLM interactions for question generation and answer evaluation"""
    
    def __init__(self):
        # Talks to the OpenAI API directly; the key comes from OPENAI_API_KEY in .env
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

        # Default model, plus the per-task overrides (each falls back to this one)
        self.model = Config.OPENAI_MODEL
        self.model_questions = Config.OPENAI_MODEL_QUESTIONS
        self.model_evaluation = Config.OPENAI_MODEL_EVALUATION
        self.model_report = Config.OPENAI_MODEL_REPORT

        # Question templates for different tech categories
        self.question_templates = {
            "programming": [
                "Explain the difference between {concept1} and {concept2} in {technology}",
                "How would you implement {functionality} in {technology}?",
                "What are the best practices for {aspect} in {technology}?",
                "Describe a challenging problem you solved using {technology}",
                "How would you optimize performance when working with {technology}?"
            ],
            "system_design": [
                "How would you design a scalable {system_type} using {technology}?",
                "What database design would you choose for {use_case} and why?",
                "How would you handle {challenge} in a distributed system?",
                "Describe your approach to implementing {feature} at scale"
            ],
            "problem_solving": [
                "Walk me through your approach to debugging {issue_type}",
                "How would you troubleshoot performance issues in {technology}?",
                "Describe a time when you had to learn {technology} quickly for a project"
            ]
        }
    
    def generate_technical_questions(self, candidate_data: Dict) -> List[Dict]:
        """Generate exactly 5 personalized technical questions based on candidate's tech stack"""
        try:
            tech_stack = candidate_data.get('tech_stack', [])
            experience = candidate_data.get('experience', 1)
            
            if not tech_stack:
                return self._get_fallback_questions()
            
            # Create prompt for question generation - specifically ask for 5 questions
            prompt = self._create_question_generation_prompt(candidate_data)
            
            response = self.client.chat.completions.create(
                model=self.model_questions,
                messages=[
                    {"role": "system", "content": f"You are an expert technical interviewer. Generate exactly {Config.DEFAULT_QUESTIONS} relevant, practical technical questions based on the candidate's profile."},
                    {"role": "user", "content": prompt}
                ],
                temperature=Config.LLM_TEMPERATURE_QUESTIONS,
                max_tokens=Config.LLM_MAX_TOKENS_QUESTIONS
            )
            
            questions_text = response.choices[0].message.content
            questions = self._parse_questions_from_response(questions_text)
            
            # Top up with template questions if the model returned too few
            target = Config.DEFAULT_QUESTIONS
            if len(questions) < target:
                questions.extend(self._get_additional_questions(tech_stack, experience, target - len(questions)))

            return questions[:target]
            
        except Exception as e:
            print(f"Error generating questions: {e}")
            return self._get_fallback_questions()
    
    def _create_question_generation_prompt(self, candidate_data: Dict) -> str:
        """Create a detailed prompt for question generation"""
        tech_stack = candidate_data.get('tech_stack', [])
        experience = candidate_data.get('experience', 1)
        name = candidate_data.get('name', 'the candidate')
        count = Config.DEFAULT_QUESTIONS

        prompt = f"""
Generate EXACTLY {count} technical interview questions for {name} based on their profile:

Tech Stack: {', '.join(tech_stack)}
Experience: {experience} years
Location: {candidate_data.get('location', 'Not specified')}

Requirements:
1. Generate EXACTLY {count} questions, no more, no less
2. Questions should be appropriate for {experience} years of experience
3. Focus on their tech stack: {', '.join(tech_stack)}
4. Include a mix of:
   - Conceptual understanding questions
   - Practical implementation questions  
   - Problem-solving scenarios
   - Best practices questions

5. Each question should:
   - Be specific and actionable
   - Allow for detailed answers
   - Test real-world application of knowledge
   - Be appropriate for their experience level

Format each question as:
Q1: [Question text]
Category: [programming/system_design/problem_solving]
Difficulty: [beginner/intermediate/advanced]

Q2: [Question text]
Category: [programming/system_design/problem_solving]
Difficulty: [beginner/intermediate/advanced]

... continue for exactly {count} questions.

Make the questions challenging but fair for someone with {experience} years of experience.
Ensure you provide exactly {count} questions.
"""
        return prompt
    
    def _parse_questions_from_response(self, response_text: str) -> List[Dict]:
        """Parse questions from LLM response"""
        questions = []
        
        # Split by question markers
        question_blocks = re.split(r'Q\d+:', response_text)
        
        for block in question_blocks[1:]:  # Skip first empty block
            lines = block.strip().split('\n')
            if not lines:
                continue
                
            question_text = lines[0].strip()
            category = "programming"  # default
            difficulty = "intermediate"  # default
            
            # Extract category and difficulty
            for line in lines[1:]:
                if line.strip().lower().startswith('category:'):
                    category = line.split(':', 1)[1].strip().lower()
                elif line.strip().lower().startswith('difficulty:'):
                    difficulty = line.split(':', 1)[1].strip().lower()
            
            if question_text:
                questions.append({
                    'question': question_text,
                    'category': category,
                    'difficulty': difficulty
                })
        
        return questions
    
    def _get_additional_questions(self, tech_stack: List[str], experience: int, needed_count: int) -> List[Dict]:
        """Generate additional questions if needed to reach exactly 5"""
        additional_questions = []
        
        # Basic programming questions
        programming_questions = [
            {
                'question': 'Explain the difference between synchronous and asynchronous programming. Provide examples from your experience.',
                'category': 'programming',
                'difficulty': 'intermediate'
            },
            {
                'question': 'How do you handle errors and exceptions in your code? Describe your approach with examples.',
                'category': 'programming',
                'difficulty': 'intermediate'
            },
            {
                'question': 'What are the key principles of clean code? How do you ensure your code is maintainable?',
                'category': 'programming',
                'difficulty': 'intermediate'
            }
        ]
        
        # Database questions
        if any(db in tech_stack for db in ['MySQL', 'PostgreSQL', 'MongoDB', 'Redis']):
            additional_questions.append({
                'question': 'How would you optimize the performance of a slow database query? Walk through your debugging process.',
                'category': 'system_design',
                'difficulty': 'intermediate'
            })
        
        # System design questions
        system_design_questions = [
            {
                'question': 'Describe how you would approach scaling a web application to handle increased traffic.',
                'category': 'system_design',
                'difficulty': 'intermediate'
            },
            {
                'question': 'How do you ensure the security of web applications? What measures do you implement?',
                'category': 'system_design',
                'difficulty': 'intermediate'
            }
        ]
        
        # Problem solving questions
        problem_solving_questions = [
            {
                'question': 'Describe a challenging technical problem you solved recently. What was your approach?',
                'category': 'problem_solving',
                'difficulty': 'intermediate'
            },
            {
                'question': 'How do you stay updated with new technologies and industry trends?',
                'category': 'problem_solving',
                'difficulty': 'beginner'
            }
        ]
        
        # Combine all additional questions
        all_additional = programming_questions + additional_questions + system_design_questions + problem_solving_questions
        
        # Return the needed number of questions
        return all_additional[:needed_count]
    
    def _get_fallback_questions(self) -> List[Dict]:
        """Return exactly 5 fallback questions if LLM generation fails"""
        return [
            {
                'question': 'Describe a challenging technical project you worked on. What problems did you face and how did you solve them?',
                'category': 'problem_solving',
                'difficulty': 'intermediate'
            },
            {
                'question': 'How do you ensure code quality and maintainability in your projects?',
                'category': 'programming',
                'difficulty': 'intermediate'
            },
            {
                'question': 'Explain your approach to learning new technologies. Give an example of a recent technology you learned.',
                'category': 'problem_solving',
                'difficulty': 'beginner'
            },
            {
                'question': 'How would you approach debugging a performance issue in a web application?',
                'category': 'problem_solving',
                'difficulty': 'intermediate'
            },
            {
                'question': 'What are the key considerations when designing a REST API? How do you ensure it is scalable and maintainable?',
                'category': 'system_design',
                'difficulty': 'intermediate'
            }
        ]
    
    def evaluate_answer(self, question: Dict, answer: str, candidate_data: Dict) -> Optional[Dict]:
        """Evaluate a candidate's answer to a technical question"""
        try:
            evaluation_prompt = self._create_evaluation_prompt(question, answer, candidate_data)
            
            response = self.client.chat.completions.create(
                model=self.model_evaluation,
                messages=[
                    {"role": "system", "content": "You are an expert technical interviewer. Evaluate answers objectively and provide constructive feedback."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=Config.LLM_TEMPERATURE_EVALUATION,  # Lower temperature for more consistent evaluation
                max_tokens=Config.LLM_MAX_TOKENS_EVALUATION
            )
            
            evaluation_text = response.choices[0].message.content
            return self._parse_evaluation_response(evaluation_text)
            
        except Exception as e:
            print(f"Error evaluating answer: {e}")
            return self._get_fallback_evaluation()
    
    def _create_evaluation_prompt(self, question: Dict, answer: str, candidate_data: Dict) -> str:
        """Create prompt for answer evaluation"""
        experience = candidate_data.get('experience', 1)
        tech_stack = candidate_data.get('tech_stack', [])
        
        prompt = f"""
Evaluate this technical interview answer:

Question: {question['question']}
Question Category: {question.get('category', 'general')}
Question Difficulty: {question.get('difficulty', 'intermediate')}

Candidate's Answer: {answer}

Candidate Profile:
- Experience: {experience} years
- Tech Stack: {', '.join(tech_stack)}

Please provide:
1. Score (1-10 scale)
2. Detailed feedback explaining the score
3. What the candidate did well
4. Areas for improvement
5. Whether the answer demonstrates appropriate level knowledge for their experience

Format your response as:
Score: [1-10]
Feedback: [Detailed explanation of the score, what was good, what could be improved]

Consider:
- Technical accuracy
- Depth of explanation
- Practical examples
- Communication clarity
- Appropriate complexity for experience level
"""
        return prompt
    
    def _parse_evaluation_response(self, response_text: str) -> Dict:
        """Parse evaluation response from LLM"""
        lines = response_text.strip().split('\n')

        score = self._extract_score(response_text, 'Score')
        if score is None:
            score = 5  # neutral default when the model gave no readable score

        # Take everything from the "Feedback:" label onwards, so multi-line
        # feedback survives instead of being truncated to its first line.
        feedback = None
        label_pattern = r'^[\s>*_#\-•]*Feedback\s*[:\-]\s*\**\s*(.*)$'
        for i, line in enumerate(lines):
            match = re.match(label_pattern, line.strip(), re.IGNORECASE)
            if match:
                feedback = '\n'.join([match.group(1).strip()] + lines[i + 1:]).strip()
                break

        # No "Feedback:" label at all - use the whole response minus any score line
        if not feedback:
            score_pattern = r'^[\s>*_#\-•]*Score\s*[:\-]'
            feedback = '\n'.join(
                l for l in lines
                if not re.match(score_pattern, l.strip(), re.IGNORECASE)
            ).strip()

        return {
            'score': int(score) if float(score).is_integer() else round(score, 1),
            'feedback': feedback or "Answer provided."
        }
    
    def _get_fallback_evaluation(self) -> Dict:
        """Return fallback evaluation if LLM evaluation fails"""
        return {
            'score': 5,
            'feedback': 'Thank you for your answer. I was unable to provide detailed feedback at this time, but your response has been recorded.'
        }
    
    def generate_final_report(self, candidate_data: Dict, answers: List[Dict], evaluations: List[Dict]) -> Optional[Dict]:
        """Generate final comprehensive evaluation report"""
        try:
            report_prompt = self._create_final_report_prompt(candidate_data, answers, evaluations)
            
            response = self.client.chat.completions.create(
                model=self.model_report,
                messages=[
                    {"role": "system", "content": "You are an expert technical recruiter. Generate comprehensive, professional evaluation reports."},
                    {"role": "user", "content": report_prompt}
                ],
                temperature=Config.LLM_TEMPERATURE_REPORT,
                max_tokens=Config.LLM_MAX_TOKENS_REPORT
            )
            
            report_text = response.choices[0].message.content
            return self._parse_final_report(report_text, evaluations)
            
        except Exception as e:
            print(f"Error generating final report: {e}")
            return self._get_fallback_report(evaluations)
    
    def _create_final_report_prompt(self, candidate_data: Dict, answers: List[Dict], evaluations: List[Dict]) -> str:
        """Create prompt for final report generation"""
        avg_score = sum(eval_data['score'] for eval_data in evaluations) / len(evaluations)
        total_possible_questions = Config.DEFAULT_QUESTIONS
        questions_answered = len(answers)
        
        prompt = f"""
Generate a comprehensive technical assessment report:

CANDIDATE PROFILE:
Name: {candidate_data.get('name', 'Candidate')}
Experience: {candidate_data.get('experience', 0)} years
Tech Stack: {', '.join(candidate_data.get('tech_stack', []))}
Location: {candidate_data.get('location', 'Not specified')}

ASSESSMENT RESULTS:
Questions Answered: {questions_answered} out of {total_possible_questions} total questions
Average Score: {avg_score:.1f}/10
Test Status: {"Completed Early" if questions_answered < total_possible_questions else "Full Assessment Completed"}

INDIVIDUAL QUESTION PERFORMANCE:
"""
        
        for i, (answer, evaluation) in enumerate(zip(answers, evaluations)):
            prompt += f"""
Q{i+1} - Score: {evaluation['score']}/10
Category: {answer.get('category', 'General')}
Question: {answer['question']}
Answer Length: {len(answer['answer'])} characters
"""
        
        prompt += f"""

Please provide:
1. Overall Score (1-10) considering both performance and completion rate
2. Recommendation (Strong Hire / Hire / Maybe / No Hire)
3. Detailed Analysis covering:
   - Technical competency assessment
   - Communication skills
   - Problem-solving approach
   - Areas of strength
   - Areas for improvement
   - Impact of early completion (if applicable)
   - Fit for experience level

Note: The candidate answered {questions_answered} out of {total_possible_questions} possible questions.
{"Consider this early completion in your evaluation." if questions_answered < total_possible_questions else ""}

Format as:
Overall Score: [1-10]
Recommendation: [Strong Hire/Hire/Maybe/No Hire]
Analysis: [Detailed professional assessment including completion status]
"""
        return prompt
    
    @staticmethod
    def _extract_labeled_value(text: str, label: str) -> Optional[str]:
        """Pull the value for a 'Label: value' line out of an LLM response.

        Tolerates the markdown the model actually emits - '**Overall Score:** 7.5/10',
        '- Score: 8', '## Recommendation: Hire' - rather than requiring the line to
        begin with the bare label.
        """
        pattern = rf'^[\s>*_#\-•]*{re.escape(label)}\s*[:\-]\s*\**\s*(.+)$'
        for line in text.split('\n'):
            match = re.match(pattern, line.strip(), re.IGNORECASE)
            if match:
                return match.group(1).strip().strip('*').strip()
        return None

    @classmethod
    def _extract_score(cls, text: str, label: str) -> Optional[float]:
        """Extract a numeric score for a label, accepting '8', '7.5' and '7.5/10'."""
        value = cls._extract_labeled_value(text, label)
        if value:
            match = re.search(r'(\d+(?:\.\d+)?)', value)
            if match:
                score = float(match.group(1))
                return min(Config.MAX_SCORE, max(Config.MIN_SCORE, score))
        return None

    def _parse_final_report(self, response_text: str, evaluations: List[Dict]) -> Dict:
        """Parse final report from LLM response"""
        # Fall back to the mean of the per-answer scores if the model didn't
        # state an overall score we can read.
        overall_score = self._extract_score(response_text, 'Overall Score')
        if overall_score is None:
            overall_score = sum(e['score'] for e in evaluations) / len(evaluations)

        recommendation = self._extract_labeled_value(response_text, 'Recommendation') or "Maybe"

        return {
            'overall_score': round(overall_score, 1),
            'recommendation': recommendation,
            'detailed_feedback': response_text
        }
    
    def _get_fallback_report(self, evaluations: List[Dict]) -> Dict:
        """Generate fallback report if LLM generation fails"""
        if not evaluations:
            return {
                'overall_score': 0,
                'recommendation': "Incomplete",
                'detailed_feedback': "Assessment was not completed. No questions were answered."
            }
        
        avg_score = sum(eval_data['score'] for eval_data in evaluations) / len(evaluations)
        questions_answered = len(evaluations)
        
        # Adjust recommendation based on completion and performance
        if questions_answered < 3:
            if avg_score >= 8:
                recommendation = "Maybe"
                feedback = f"Strong performance on {questions_answered} question(s), but assessment incomplete."
            elif avg_score >= 6:
                recommendation = "Maybe"
                feedback = f"Good performance on {questions_answered} question(s), but needs full assessment."
            else:
                recommendation = "No Hire"
                feedback = f"Below average performance on {questions_answered} question(s) and incomplete assessment."
        else:
            if avg_score >= 8:
                recommendation = "Hire" if questions_answered >= 4 else "Maybe"
                feedback = f"Excellent performance across {questions_answered} questions."
            elif avg_score >= 7:
                recommendation = "Hire" if questions_answered >= 4 else "Maybe"
                feedback = f"Good technical skills demonstrated in {questions_answered} questions."
            elif avg_score >= 5:
                recommendation = "Maybe"
                feedback = f"Average performance across {questions_answered} questions, some areas need improvement."
            else:
                recommendation = "No Hire"
                feedback = f"Below expectations in {questions_answered} questions, significant improvement needed."
        
        return {
            'overall_score': round(avg_score, 1),
            'recommendation': recommendation,
            'detailed_feedback': feedback
        }