from pathlib import Path

import pytest
from dotenv import dotenv_values


@pytest.fixture
def a_test_env(monkeypatch):
    """Set up test environment variables using monkeypatch for proper isolation."""
    example_env_vars = dotenv_values(Path(__file__).parent.parent / ".example.env")

    for key, value in example_env_vars.items():
        if value is not None:  # dotenv_values returns None for empty values
            monkeypatch.setenv(key, value)
