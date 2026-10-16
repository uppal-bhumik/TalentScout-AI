# TalentScout AI
#
#   docker build -t talentscout-ai .
#   docker run --rm -p 8501:8501 --env-file .env -v talentscout-data:/app/data talentscout-ai
#
# The API key is passed in at run time and never baked into the image. The
# SQLite database lives in /app/data, so mount a volume there if assessments
# should survive the container.

FROM python:3.11-slim

# Keep Python quiet and unbuffered so container logs appear immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so a code change does not invalidate the install layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py conversation_manager.py data_validator.py database.py \
     llm_handler.py llm_schemas.py utils.py ./
COPY app_chrome.py main_app.py recruiter_view.py report_view.py session.py ./
COPY stages/ ./stages/
COPY static/ ./static/

# Run as a non-root user that owns the writable directories.
RUN useradd --create-home --uid 1000 talentscout \
    && mkdir -p /app/data /app/logs \
    && chown -R talentscout:talentscout /app
USER talentscout

ENV DATABASE_URL=sqlite:////app/data/talentscout.db \
    LOG_FILE=/app/logs/talentscout.log

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

ENTRYPOINT ["streamlit", "run", "main_app.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true", \
            "--browser.gatherUsageStats=false"]
