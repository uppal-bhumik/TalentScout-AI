"""Shared helpers: logging, error messages, report export and small utilities.

Deliberately free of any Streamlit import so that non-UI modules (llm_handler,
database) and the test suite can use it without pulling in the UI framework.
"""

import csv
import logging
import os
import re
from datetime import datetime
from io import StringIO
from typing import Dict, List, Optional

from config import Config

_CONFIGURED_LOGGERS = set()


def get_logger(name: str = "TalentScout") -> logging.Logger:
    """Return a logger that writes to the console and to Config.LOG_FILE.

    Handlers are attached once per name; the log directory is created first
    because a FileHandler will not create it itself.
    """
    logger = logging.getLogger(name)

    if name not in _CONFIGURED_LOGGERS:
        logger.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        log_dir = os.path.dirname(Config.LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(Config.LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        _CONFIGURED_LOGGERS.add(name)

    return logger


class ErrorHandler:
    """Turns exceptions into messages that are safe to show a user."""

    @staticmethod
    def handle_api_error(error: Optional[Exception], context: str = "API call") -> str:
        """Map an API exception to a short, actionable explanation."""
        if error is None:
            return f"{context} failed for an unknown reason."

        text = str(error).lower()
        kind = type(error).__name__

        if "ratelimit" in kind.lower() or "rate_limit" in text or "rate limit" in text:
            return "The OpenAI rate limit was hit and retries did not clear it. Try again shortly."
        if "authentication" in kind.lower() or "api key" in text or "unauthorized" in text:
            return "OpenAI rejected the API key. Check OPENAI_API_KEY in your environment."
        if "permissiondenied" in kind.lower():
            return "This OpenAI key is not allowed to use the configured model."
        if "notfound" in kind.lower():
            return f"The configured model was not found: {error}"
        if "timeout" in kind.lower() or "timeout" in text:
            return "The request to OpenAI timed out after several attempts."
        if "connection" in kind.lower():
            return "Could not reach the OpenAI API. Check the network connection."
        if "badrequest" in kind.lower():
            return f"OpenAI rejected the request: {error}"

        return f"{context} failed: {error}"


class ReportGenerator:
    """Exports a completed assessment as a standalone HTML or CSV document."""

    @staticmethod
    def generate_html_report(candidate_data: Dict, answers: List[Dict],
                             evaluations: List[Dict], final_report: Dict) -> str:
        """Generate a self-contained HTML report."""

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>TalentScout AI Assessment Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; color: #222; }}
        .header {{ background-color: #2E86AB; color: white; padding: 20px; text-align: center; }}
        .candidate-info {{ background-color: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; }}
        .question-block {{ margin: 20px 0; padding: 15px; border-left: 4px solid #2196f3; background-color: #e3f2fd; }}
        .evaluation-block {{ margin: 10px 0; padding: 15px; border-left: 4px solid #9c27b0; background-color: #f3e5f5; }}
        .final-report {{ background-color: #e8f5e8; padding: 20px; margin: 20px 0; border-radius: 8px; }}
        .score {{ font-size: 24px; font-weight: bold; color: #4caf50; }}
        .recommendation {{ font-size: 20px; font-weight: bold; color: #ff5722; }}
        .degraded {{ background-color: #fff3cd; border-left: 4px solid #ff9800; padding: 15px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>TalentScout AI Assessment Report</h1>
        <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="candidate-info">
        <h2>Candidate Information</h2>
        <p><strong>Name:</strong> {candidate_data.get('name', 'N/A')}</p>
        <p><strong>Email:</strong> {candidate_data.get('email', 'N/A')}</p>
        <p><strong>Phone:</strong> {candidate_data.get('phone', 'N/A')}</p>
        <p><strong>Experience:</strong> {candidate_data.get('experience', 'N/A')} years</p>
        <p><strong>Location:</strong> {candidate_data.get('location', 'N/A')}</p>
        <p><strong>Tech Stack:</strong> {', '.join(candidate_data.get('tech_stack', []))}</p>
    </div>
"""

        if final_report.get('degraded'):
            html += f"""
    <div class="degraded">
        <strong>Scored in degraded mode.</strong>
        {final_report.get('degraded_reason', 'Some scores are automated placeholders.')}
        These results need a human review before any hiring decision.
    </div>
"""

        performance = final_report.get('performance_score')
        factor = final_report.get('completion_penalty_factor', 1.0)
        arithmetic = (
            f"<p>{performance}/10 on the answers given &times; {factor} completion factor</p>"
            if performance is not None and factor < 1.0 else ""
        )

        html += f"""
    <div class="final-report">
        <h2>Final Assessment</h2>
        <div class="score">Overall Score: {final_report.get('overall_score', 'N/A')}/10</div>
        {arithmetic}
        <div class="recommendation">Recommendation: {final_report.get('recommendation', 'N/A')}</div>
        <p><strong>Completion:</strong> {final_report.get('completion_status', 'N/A')}</p>
        <p><strong>Analysis:</strong> {final_report.get('detailed_feedback', 'No analysis available.')}</p>
    </div>

    <h2>Question-wise Performance</h2>
"""

        for i, (answer, evaluation) in enumerate(zip(answers, evaluations)):
            html += f"""
    <div class="question-block">
        <h3>Question {i + 1}</h3>
        <p><strong>Question:</strong> {answer['question']}</p>
        <p><strong>Category:</strong> {answer.get('category', 'General')}</p>
        <p><strong>Answer:</strong> {answer['answer']}</p>
    </div>
    <div class="evaluation-block">
        <p><strong>Score:</strong> {evaluation['score']}/10{' (placeholder - not scored)' if evaluation.get('degraded') else ''}</p>
        <p><strong>Feedback:</strong> {evaluation['feedback']}</p>
    </div>
"""

        html += """
</body>
</html>
"""
        return html

    @staticmethod
    def generate_csv_summary(candidate_data: Dict, evaluations: List[Dict]) -> str:
        """Generate a CSV summary of the assessment"""
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Name', candidate_data.get('name', 'N/A')])
        writer.writerow(['Email', candidate_data.get('email', 'N/A')])
        writer.writerow(['Experience', f"{candidate_data.get('experience', 'N/A')} years"])
        writer.writerow(['Location', candidate_data.get('location', 'N/A')])
        writer.writerow(['Tech Stack', ', '.join(candidate_data.get('tech_stack', []))])
        writer.writerow(['Total Questions', len(evaluations)])

        if evaluations:
            avg_score = sum(e['score'] for e in evaluations) / len(evaluations)
            writer.writerow(['Average Score', f"{avg_score:.1f}/10"])

        writer.writerow(['Assessment Date', datetime.now().strftime("%Y-%m-%d")])

        return output.getvalue()


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length"""
    if not text or len(text) <= max_length:
        return text or ""
    return text[:max_length].rstrip() + "..."


def sanitize_filename(filename: str) -> str:
    """Sanitize a string for use in a filename"""
    filename = re.sub(r'[<>:"/\\|?*\s]', '_', filename or "")
    filename = re.sub(r'_+', '_', filename)
    return filename.strip('_') or "unnamed"


def calculate_assessment_metrics(evaluations: List[Dict]) -> Dict:
    """Summary statistics over a set of per-answer evaluations."""
    if not evaluations:
        return {}

    scores = [e['score'] for e in evaluations]
    passing = [s for s in scores if s >= Config.PASSING_SCORE]

    return {
        'total_questions': len(evaluations),
        'average_score': sum(scores) / len(scores),
        'highest_score': max(scores),
        'lowest_score': min(scores),
        'passing_questions': len(passing),
        'pass_rate': len(passing) / len(scores) * 100,
    }
