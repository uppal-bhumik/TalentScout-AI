
# TalentScout AI 🎯

An intelligent hiring assistant that automates the initial technical screening process for candidates using a sophisticated, stage-based conversational UI and advanced LLM-powered evaluation.

## 🌟 Project Overview

TalentScout AI is a web application designed to automate the initial technical screening process for job candidates. It uses advanced Large Language Model (LLM) technology to generate personalized technical questions based on each candidate's unique tech stack and provides real-time evaluation with constructive feedback. The application is built with a modular architecture that separates the frontend, backend, and configuration logic, making it easy to maintain and extend.

### Key Capabilities:

  * **Stage-Based Conversation Flow**: A structured, step-by-step process guides the candidate through profile setup and a technical assessment.
  * **Dynamic Question Generation**: The application uses an LLM to generate personalized technical questions based on the candidate's unique tech stack and experience.
  * **Real-time Evaluation**: Each answer is evaluated instantly, providing a score and constructive feedback.
  * **Comprehensive Final Report**: At the end of the assessment, a detailed report is generated with an overall score, a hiring recommendation, and a breakdown of the candidate's performance.

## 🛠️ Technical Details

  * **Frontend**: Streamlit
  * **Backend**: Python
  * **LLM Integration**: OpenRouter API (compatible with various models, including Mistral)
  * **Key Libraries**:
      * `streamlit` for the web interface
      * `openai` for the LLM client
      * `python-dotenv` for managing environment variables
      * `phonenumbers` and `email-validator` for robust data validation

## 🛠️ Technical Architecture

```
TalentScout AI/
├── main_app.py              # Main Streamlit application
├── conversation_manager.py  # Handles conversation flow and state
├── llm_handler.py          # LLM integration for questions/evaluation
├── data_validator.py       # Input validation and sanitization
├── config.py              # Configuration settings
├── utils.py               # Utility functions and helpers
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## 🚀 Installation Instructions

1.  **Clone the repository or download the files.**
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv talentscout_env
    # On Windows:
    talentscout_env\Scripts\activate
    # On macOS/Linux:
    source talentscout_env/bin/activate
    ```
3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Create a `.env` file** in the root of your project and add your OpenRouter API key:
    ```
    OPENAI_API_KEY="your_openrouter_api_key_here"
    OPENAI_MODEL="mistralai/mistral-7b-instruct:free"
    ```
5.  **Run the application:**
    ```bash
    streamlit run main_app.py
    ```

## 💡 Usage Guide

### For Candidates:

1.  **Welcome Screen**: Introduction and process overview
2.  **Profile Setup**: Step-by-step collection of your name, email, phone, experience, location, and tech stack
3.  **Technical Assessment**: Answer personalized questions based on your tech stack, with the option to skip questions or end the test early
4.  **Final Report**: Receive an overall score, a hiring recommendation, and a detailed analysis of your performance

### For Recruiters/Administrators:

1.  **Monitor Progress**: View candidate profiles in the sidebar
2.  **Review Results**: Access detailed evaluation reports
3.  **Export Data**: Download assessment results as a JSON file

## ✍️ Prompt Design

The application's intelligence is powered by a set of carefully engineered prompts that guide the LLM's behavior.

  * **Question Generation**: The prompt for question generation provides the LLM with the candidate's tech stack, experience level, and desired position. It then instructs the LLM to generate a specific number of questions that are relevant, practical, and appropriate for the candidate's skill level.
  * **Answer Evaluation**: The prompt for answer evaluation provides the LLM with the question, the candidate's answer, and the candidate's profile. It then instructs the LLM to evaluate the answer based on a set of predefined criteria, including technical accuracy, depth of explanation, and communication clarity.
  * **Final Report Generation**: The prompt for the final report provides the LLM with the candidate's profile, all of their answers, and the individual evaluations. It then instructs the LLM to generate a comprehensive report with an overall score, a hiring recommendation, and a detailed analysis of the candidate's performance.

## 🧗 Challenges & Solutions

  * **State Management in Streamlit**:
      * **Challenge**: Ensuring that the application correctly remembers the user's progress and that UI elements like text boxes clear correctly between stages.
      * **Solution**: We implemented a robust state management system using Streamlit's session state, with a dedicated `ConversationManager` class to handle the application's flow and a unique `key` for each input widget to ensure it resets correctly.
  * **CSS Conflicts**:
      * **Challenge**: The application's CSS was not always being applied correctly, leading to issues with text visibility and layout.
      * **Solution**: We created a more specific and robust CSS stylesheet that uses the `!important` keyword to ensure that the correct styles are always applied.
  * **LLM Reliability**:
      * **Challenge**: The LLM would sometimes fail to generate a response or would generate a response in an unexpected format.
      * **Solution**: We implemented a set of fallback mechanisms that provide a default response when the LLM fails, ensuring that the user experience is not interrupted.

## 🎉 Conclusion
TalentScout AI represents a significant improvement over traditional technical screening methods. With its structured approach, real-time evaluation, and comprehensive reporting, it provides both candidates and recruiters with a superior experience.