# TalentScout AI 🎯

An LLM-powered technical screening assistant. It collects a candidate profile,
generates five interview questions from their declared tech stack, scores each
answer with written feedback, and produces a hiring report — then stores the
whole assessment so a recruiter can reopen it later.

Built with Streamlit, OpenAI structured outputs and SQLAlchemy.

## What it does

**For candidates**

1. **Profile setup** — name, email, phone, experience, location and tech stack,
   each validated as it is entered.
2. **Technical assessment** — five questions generated from *their* stack, not a
   fixed question bank. Any question can be skipped, and the test can be ended
   early.
3. **Instant feedback** — every answer is scored 1–10 with an explanation.
4. **Final report** — an overall score, a hiring recommendation and a written
   analysis, downloadable as JSON, HTML or CSV.

**For recruiters**

A dashboard listing every assessment ever taken, with search, per-candidate
detail, the score distribution, the questions that went unanswered, and the same
exports. Password-protect it with `RECRUITER_PASSWORD` on any public deployment —
it shows candidate contact details.

## How the scoring works

The model scores **answer quality only**. The penalty for an unfinished
assessment is applied afterwards, in code, from a fixed table in `config.py`:

| Questions answered | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- |
| Factor | 0.80 | 0.90 | 0.95 | 0.98 | 1.00 |

So a candidate who answers one question well sees `8.0/10 on answers given
× 0.8 completion factor = 6.4/10`, and the report shows that arithmetic rather
than hiding it. Keeping the adjustment out of the prompt makes it deterministic
and identical for every candidate, and stops the model double-counting
incompleteness in its own score.

## Reliability

LLM calls fail. Three design decisions follow from that:

- **Structured outputs.** Every call asks for a Pydantic schema via the OpenAI
  SDK's `parse` helper (`llm_schemas.py`), so the reply is guaranteed to match
  the shape the app expects. There is no response parsing to go wrong.
- **Retries with backoff.** Rate limits, timeouts, connection drops and 5xx are
  retried with exponential backoff and jitter, honouring `Retry-After`. A bad
  key or a truncated reply is *not* retried — it would fail identically.
- **Degraded results are labelled.** When a call still fails, the app falls back
  to canned content rather than breaking, but marks the result `degraded` and
  says so in the UI, in the report and in the database. A silent fallback would
  look like a working app that scores every candidate exactly 5.

## Architecture

```
TalentScout AI/
├── main_app.py              # Streamlit entry point: bootstrap, view switch, routing
├── stages/                  # The candidate interview, one module per phase
│   ├── profile.py           # Declared profile form steps (name, email, ...)
│   ├── assessment.py        # Question generation, answering, scoring
│   └── results.py           # Final report generation and persistence
├── session.py               # Session state keys, created and reset in one place
├── app_chrome.py            # Stylesheet, header, profile sidebar, view switch
├── report_view.py           # Report rendering and exports, shared with the dashboard
├── recruiter_view.py        # Recruiter dashboard: list, detail, exports
├── llm_handler.py           # LLM calls, retries, fallbacks
├── llm_schemas.py           # Pydantic schemas for structured outputs
├── database.py              # SQLAlchemy models and queries
├── data_validator.py        # Input validation and sanitisation
├── conversation_manager.py  # Conversation flow and stage bookkeeping
├── config.py                # Single source of truth for settings
├── utils.py                 # Logging, error messages, HTML/CSV export
├── static/styles.css        # Application styling
├── tests/                   # pytest suite (202 tests, no network needed)
├── Dockerfile               # Container image
└── DEPLOY.md                # Docker and Streamlit Cloud deployment
```

Data model: a `Candidate` (keyed on email) has many `Assessment`s; each has
ordered `Question`s, each of which may have one `Answer`, which has one
`Evaluation`; a finished assessment has one `Report`.

## Running it locally

```bash
python -m venv talentscout_env
talentscout_env\Scripts\activate        # Windows
# source talentscout_env/bin/activate   # macOS / Linux

pip install -r requirements.txt
cp .env.example .env                    # then add your OpenAI key
streamlit run main_app.py
```

The app refuses to start without a valid `OPENAI_API_KEY`, rather than falling
back to canned content and looking like it works. Get one at
<https://platform.openai.com/api-keys>. A full five-question interview costs
about $0.002 on the default `gpt-4o-mini`.

SQLite is created automatically at `data/talentscout.db` on first run.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

202 tests covering validation, the scoring arithmetic, config validation,
persistence and the LLM layer's retry and fallback paths. No API key and no
network access are needed: the OpenAI client is mocked, the database runs in
memory, and the email validator's DNS lookup is stubbed.

## Deployment

See [DEPLOY.md](DEPLOY.md) for Docker and Streamlit Community Cloud, including
the secrets setup and why a hosted deployment should point `DATABASE_URL` at
Postgres rather than SQLite.

## Configuration

All settings live in `config.py` and are overridable through the environment;
see `.env.example` and the table in [DEPLOY.md](DEPLOY.md). `Config.validate_config()`
runs at startup and reports every problem at once.

## Known behaviours

- `validate_email` performs a live DNS/MX lookup, so an address at a
  non-receiving domain (including `@example.com`) is rejected.
- Names, emails and locations containing `test` or `admin` are rejected as junk
  input. That filter is deliberately strict; it also rejects legitimate
  addresses that happen to contain those words.
