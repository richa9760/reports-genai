"""Shared test helpers for llmops tests.

This module is intentionally NOT discovered by Django's test runner (name does
not start with ``test``), so it can be imported from any llmops test module.
"""

import io
import json
import urllib.error


class MockLLMResponse:
    """Fake HTTP response exposing ``read()`` and context manager support."""

    def __init__(self, body):
        self._body = json.dumps(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def make_openai_body(content="Generated monthly summary."):
    return {"choices": [{"message": {"content": content}}]}


def make_http_error(code, reason="Error"):
    """Build a real ``urllib.error.HTTPError`` with a readable response fp.

    The production ``_generate_with_config`` calls ``exc.read()`` on the raised
    ``HTTPError``, so a usable file pointer is required.
    """
    return urllib.error.HTTPError(
        "https://llm.example.com/v1/chat/completions",
        code,
        reason,
        {"content-type": "application/json"},
        io.BytesIO(b"{}"),
    )