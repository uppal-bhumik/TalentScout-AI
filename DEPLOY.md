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
3. Open **Advanced settings** before deploying and set the Python version to
   **3.11**. `streamlit==1.28.1` predates 3.12, and the version cannot be
   changed afterwards without deleting the app and redeploying it.
4. In the same dialog (or later under **App settings → Secrets**), paste:

   ```toml
   OPENAI_API_KEY = "sk-..."
   OPENAI_MODEL = "gpt-4o-mini"
   DATABASE_URL = "postgresql://user:password@host/dbname?sslmode=require"
   RECRUITER_PASSWORD = "choose-something"
   ```

   Secrets written at the top level of the TOML are also exposed as environment
   variables, which is how `Config` picks them up — no code change is needed,
   and `python-dotenv` simply finds no `.env` file and moves on. Keys inside a
   `[section]` are *not*, so keep them flat.
5. Deploy. First boot installs `requirements.txt` and creates the schema
   automatically.

**Set `DATABASE_URL`, and set `RECRUITER_PASSWORD`.** The filesystem there is
ephemeral, so without a `DATABASE_URL` the SQLite database is wiped on every
reboot and redeploy, and past assessments vanish from the dashboard. And the
dashboard lists candidate names, emails and phone numbers, so on a public URL it
needs the password in front of it.

### Pointing at hosted Postgres

Any SQLAlchemy URL works; the models and queries are plain SQLAlchemy and need
no change. `psycopg2-binary` is already in `requirements.txt`, which is the
driver SQLAlchemy loads for a bare `postgresql://` URL.

Neon and Supabase both have a free tier. Copy the connection string from the
provider and paste it in as-is, with two caveats:

- If it starts `postgres://` (Heroku and some Supabase copies), change that to
  `postgresql://` — SQLAlchemy rejects the short form.
- Hosted Postgres generally needs `?sslmode=require` on the end. Neon's string
  arrives with that and `channel_binding=require` already on it.

Neon gives two hostnames: use the **pooler** endpoint for the app, and the
direct one if you ever run schema migrations. Both free tiers suspend their
compute when idle, which adds roughly a second to the first query after a quiet
spell.

### Before you share the URL

- **Every visitor spends your OpenAI credit** — about $0.002 an interview, with
  nothing capping how many. Set a monthly budget limit on the OpenAI account.
- **Community Cloud sleeps an app** after about a week without traffic, so a
  cold link shows a wake screen for roughly half a minute before the app
  appears. Opening it occasionally keeps it warm.
- `logs/` is ephemeral too; read the app's output through **Manage app** in the
  Cloud workspace rather than from the filesystem.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

202 tests, no network access and no API key needed: the OpenAI client is mocked,
the database runs in memory, and the email validator's DNS lookup is stubbed.
