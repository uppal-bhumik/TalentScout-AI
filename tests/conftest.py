"""Shared fixtures.

Nothing here touches the network: `validate_email` normally performs a live
DNS/MX lookup, and the OpenAI client is always a stand-in.
"""

import httpx
import pytest

import database as db
from data_validator import DataValidator


@pytest.fixture
def validator():
    return DataValidator()


@pytest.fixture
def accept_email_deliverability(monkeypatch):
    """Stub out email-validator's DNS/MX lookup so tests stay offline.

    data_validator imports `validate_email` into its own namespace, so that is
    the name that has to be patched.
    """
    monkeypatch.setattr("data_validator.validate_email", lambda email: True)


@pytest.fixture
def memory_db():
    """A fresh in-memory database for the duration of one test."""
    db.reset_engine()
    db.init_db("sqlite:///:memory:", echo=False)
    yield db
    db.reset_engine()


@pytest.fixture
def http_request():
    """A throwaway httpx request, needed to construct OpenAI exceptions."""
    return httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


@pytest.fixture
def no_sleep(monkeypatch):
    """Make the retry backoff instant and record the delays it asked for."""
    delays = []
    monkeypatch.setattr("llm_handler.time.sleep", delays.append)
    return delays


@pytest.fixture
def candidate():
    return {
        "name": "Ada Lovelace",
        "email": "ada@analytical.example",
        "phone": "+442071838750",
        "experience": 5,
        "location": "London, United Kingdom",
        "tech_stack": ["Python", "PostgreSQL"],
    }
