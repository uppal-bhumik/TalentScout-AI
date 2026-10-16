# Deploying TalentScout AI

Two supported targets: Docker (anywhere) and Streamlit Community Cloud (free,
public). Both read configuration from environment variables — the app never
reads a key from source.

## Configuration

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | **yes** | — | OpenAI key. The app refuses to start without it, and rejects an OpenRouter `sk-or-…` key. |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | Model for all three call sites (~$0.002 per full interview). |
| `OPENAI_MODEL_QUESTIONS` / `_EVALUATION` / `_REPORT` | no | `OPENAI_MODEL` | Per-task overrides. |
| `OPENAI_TIMEOUT_SECONDS` | no | `60` | Per-request timeout. |
| `OPENAI_MAX_RETRIES` | no | `3` | Retries after the first attempt, with exponential backoff. |
| `DATABASE_URL` | no | `sqlite:///data/talentscout.db` | Any SQLAlchemy URL. |
| `RECRUITER_PASSWORD` | no | unset | When set, the recruiter dashboard asks for it. **Set this on any public deployment** — the dashboard shows candidate names, emails and phone numbers. |
| `LOG_LEVEL` / `LOG_FILE` | no | `INFO`, `logs/talentscout.log` | Logging. |

## Docker

```bash
docker build -t talentscout-ai .
docker run --rm -p 8501:8501 \
  -e OPENAI_API_KEY=sk-... \
  -e RECRUITER_PASSWORD=choose-something \
  -v talentscout-data:/app/data \
  talentscout-ai
```

Then open <http://localhost:8501>.

Notes:

- The image runs as the non-root user `talentscout`.
- The database lives at `/app/data/talentscout.db`. Without the volume mount it
  is created inside the container and lost when the container is removed.
- `HEALTHCHECK` polls Streamlit's own `/_stcore/health` endpoint.
- `--env-file .env` works too, but check `.env` is still gitignored first.

### docker compose

```yaml
services:
  talentscout:
    build: .
    ports: ["8501:8501"]
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      RECRUITER_PASSWORD: ${RECRUITER_PASSWORD}
    volumes:
      - talentscout-data:/app/data
volumes:
  talentscout-data:
```

## Streamlit Community Cloud

1. Push the repository to GitHub (the `.gitignore` already excludes `.env`,
   `data/` and the virtualenv).
2. At <https://share.streamlit.io> create an app pointing at `main_app.py` on
   the `main` branch.
3. In **App settings → Secrets**, paste:

   ```toml
   OPENAI_API_KEY = "sk-..."
   OPENAI_MODEL = "gpt-4o-mini"
   RECRUITER_PASSWORD = "choose-something"
   ```

   Streamlit also exposes every secret as an environment variable, which is how
   `Config` picks them up — no code change is needed, and `python-dotenv`
   simply finds no `.env` file and moves on.
4. Deploy. First boot installs `requirements.txt` and creates the SQLite schema
   automatically.

**The filesystem there is ephemeral.** The SQLite database is wiped whenever the
app reboots or is redeployed, so past assessments disappear from the recruiter
dashboard. For results that persist, point `DATABASE_URL` at a hosted Postgres
(Supabase and Neon both have free tiers) and add `psycopg[binary]` to
`requirements.txt`:

```toml
DATABASE_URL = "postgresql+psycopg://user:password@host:5432/talentscout"
```

No other change is required — the models and queries are plain SQLAlchemy.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

166 tests, no network access and no API key needed: the OpenAI client is mocked,
the database runs in memory, and the email validator's DNS lookup is stubbed.
